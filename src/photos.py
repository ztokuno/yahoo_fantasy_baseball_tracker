"""
Player Photos Module

Handles downloading and caching MLB player headshots for use in visualizations.
Uses the MLB Stats API to fetch photos and fuzzy name matching to handle
differences between Yahoo player names and MLB roster names.
"""

import requests
import json
import logging
from pathlib import Path
from PIL import Image
from io import BytesIO
from difflib import SequenceMatcher
import time

logger = logging.getLogger(__name__)


class PlayerPhotoManager:
    """
    Manage MLB player headshots for fantasy baseball visualizations.
    
    This class handles:
    - Searching for MLB players by name
    - Downloading official headshots from MLB Stats API
    - Caching photos locally to avoid repeated API calls
    - Fuzzy matching to handle name variations between Yahoo and MLB
    """
    
    # NOTE: MLB deprecated lookup-service-prod.mlb.com in late 2024. This
    # uses the modern statsapi.mlb.com replacement instead. Verified live
    # on 2026-06-28 (returns real player data, not a 404).
    MLB_SEARCH_URL = "https://statsapi.mlb.com/api/v1/people/search"
    MLB_PHOTO_BASE = "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people"
    
    # Fallback generic silhouette if player not found
    GENERIC_HEADSHOT = "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/0/headshot/67/current"
    
    def __init__(self, cache_dir='data/player_photos'):
        """
        Initialize the photo manager.
        
        Args:
            cache_dir: Directory to store cached player photos
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of player name -> MLB ID mappings
        self.name_to_id_cache = {}
        self.load_cache_mappings()
    
    def load_cache_mappings(self):
        """Load any previously cached name->ID mappings from disk."""
        mapping_file = self.cache_dir / 'player_mappings.json'
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    self.name_to_id_cache = json.load(f)
                logger.info(f"Loaded {len(self.name_to_id_cache)} cached player mappings")
            except Exception as e:
                logger.warning(f"Error loading player mappings: {e}")
    
    def save_cache_mappings(self):
        """Save name->ID mappings to disk for future use."""
        mapping_file = self.cache_dir / 'player_mappings.json'
        try:
            with open(mapping_file, 'w') as f:
                json.dump(self.name_to_id_cache, f, indent=2)
            logger.debug(f"Saved {len(self.name_to_id_cache)} player mappings")
        except Exception as e:
            logger.warning(f"Error saving player mappings: {e}")
    
    def _normalize_name(self, name):
        """
        Normalize a player name for comparison.
        
        Handles common variations:
        - Removes Jr., Sr., III, etc.
        - Standardizes spacing
        - Lowercases
        """
        if not name:
            return ""
        
        # Remove suffixes
        suffixes = [' Jr.', ' Sr.', ' II', ' III', ' IV']
        for suffix in suffixes:
            name = name.replace(suffix, '')
        
        # Normalize spacing and case
        return ' '.join(name.lower().split())
    
    def _similarity_score(self, name1, name2):
        """
        Calculate similarity between two names.
        
        Returns a score from 0.0 to 1.0, where 1.0 is an exact match.
        Uses SequenceMatcher for fuzzy matching.
        """
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def search_mlb_player(self, player_name):
        """
        Search MLB Stats API for a player by name.
        
        Args:
            player_name: Name to search for (e.g., "Aaron Judge")
            
        Returns:
            MLB player ID (integer) or None if not found
        """
        # Check cache first
        normalized = self._normalize_name(player_name)
        if normalized in self.name_to_id_cache:
            logger.debug(f"Using cached MLB ID for {player_name}")
            return self.name_to_id_cache[normalized]
        
        try:
            # Query MLB's modern people-search endpoint
            params = {'names': player_name}
            
            response = requests.get(self.MLB_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            players = data.get('people', [])
            if not players:
                logger.warning(f"No MLB results found for '{player_name}'")
                self.name_to_id_cache[normalized] = None
                self.save_cache_mappings()
                return None
            
            # Find best match using fuzzy name matching, preferring active players
            best_match = None
            best_score = 0.0
            
            for player in players:
                full_name = player.get('fullName', '')
                score = self._similarity_score(player_name, full_name)
                
                # Slight bonus for currently-active players, since fantasy
                # rosters are made up of active MLB players. This breaks
                # ties in favor of the active player when names collide
                # (e.g. a retired player sharing a name).
                if player.get('active'):
                    score = min(1.0, score + 0.05)
                
                logger.debug(f"MLB match candidate: {full_name} (score: {score:.2f})")
                
                if score > best_score:
                    best_score = score
                    best_match = player
            
            # Require at least 70% similarity
            if best_match and best_score >= 0.7:
                mlb_id = int(best_match['id'])
                logger.info(
                    f"Matched '{player_name}' to MLB ID {mlb_id} "
                    f"({best_match.get('fullName')}) with score {best_score:.2f}"
                )
                
                # Cache the mapping
                self.name_to_id_cache[normalized] = mlb_id
                self.save_cache_mappings()
                
                return mlb_id
            else:
                logger.warning(f"No good match for '{player_name}' (best score: {best_score:.2f})")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for player '{player_name}': {e}")
            return None
    
    def download_photo(self, mlb_id, save_as=None):
        """
        Download a player headshot from MLB Stats API.
        
        Args:
            mlb_id: MLB player ID
            save_as: Optional path to save the image. If None, returns PIL Image.
            
        Returns:
            PIL Image object if save_as is None, otherwise the save path
        """
        try:
            photo_url = f"{self.MLB_PHOTO_BASE}/{mlb_id}/headshot/67/current"
            
            logger.debug(f"Downloading photo from {photo_url}")
            response = requests.get(photo_url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            
            if save_as:
                img.save(save_as)
                logger.info(f"Saved player photo to {save_as}")
                return save_as
            else:
                return img
                
        except Exception as e:
            logger.error(f"Error downloading photo for MLB ID {mlb_id}: {e}")
            return None
    
    def get_player_photo(self, player_name, force_refresh=False):
        """
        Get a player's headshot, using cache if available.
        
        This is the main entry point for getting photos. It handles:
        1. Checking if photo is already cached locally
        2. Searching MLB API for the player
        3. Downloading and caching the photo
        4. Returning a generic silhouette if player not found
        
        Args:
            player_name: Name of the player (e.g., "Shohei Ohtani")
            force_refresh: If True, re-download even if cached
            
        Returns:
            Path to the photo file (Path object)
        """
        # Create a safe filename from the player name
        safe_name = "".join(c if c.isalnum() else "_" for c in player_name)
        photo_path = self.cache_dir / f"{safe_name}.png"
        
        # Return cached photo if it exists
        if photo_path.exists() and not force_refresh:
            logger.debug(f"Using cached photo for {player_name}")
            return photo_path
        
        # Search for the player
        mlb_id = self.search_mlb_player(player_name)
        
        if mlb_id:
            # Download and cache the photo
            self.download_photo(mlb_id, save_as=photo_path)
            time.sleep(0.2)  # Be respectful to MLB API
        else:
            # Use generic silhouette
            logger.info(f"Using generic photo for {player_name}")
            try:
                response = requests.get(self.GENERIC_HEADSHOT, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                img.save(photo_path)
            except Exception as e:
                logger.error(f"Error downloading generic photo: {e}")
                return None
        
        return photo_path if photo_path.exists() else None
    
    def bulk_download(self, player_names, progress_callback=None):
        """
        Download photos for multiple players at once.
        
        Useful for pre-loading all league players at the start of the season.
        
        Args:
            player_names: List of player names
            progress_callback: Optional function(current, total, name) to track progress
            
        Returns:
            Dictionary of {player_name: photo_path}
        """
        results = {}
        total = len(player_names)
        
        logger.info(f"Bulk downloading photos for {total} players")
        
        for i, name in enumerate(player_names):
            if progress_callback:
                progress_callback(i + 1, total, name)
            
            photo_path = self.get_player_photo(name)
            results[name] = photo_path
            
            # Be respectful to the API
            if i < total - 1:
                time.sleep(0.5)
        
        logger.info(f"Bulk download complete: {len(results)} photos")
        return results
    
    def clear_cache(self):
        """Remove all cached photos and mappings."""
        import shutil
        shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.name_to_id_cache = {}
        logger.info("Photo cache cleared")


def main():
    """Test the photo manager when run directly."""
    logging.basicConfig(level=logging.INFO)
    
    manager = PlayerPhotoManager()
    
    # Test with some well-known players
    test_players = [
        "Shohei Ohtani",
        "Aaron Judge",
        "Mookie Betts",
        "Ronald Acuna Jr.",
        "Freddie Freeman"
    ]
    
    print("\nTesting player photo downloads:")
    print("=" * 60)
    
    for player in test_players:
        photo_path = manager.get_player_photo(player)
        if photo_path:
            print(f"✓ {player}: {photo_path}")
        else:
            print(f"✗ {player}: Failed to download")
    
    print("=" * 60)
    print(f"\nPhotos cached in: {manager.cache_dir.absolute()}")


if __name__ == "__main__":
    main()
