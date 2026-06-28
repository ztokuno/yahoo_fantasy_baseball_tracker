"""
Data Collector Module

Handles fetching data from Yahoo Fantasy Sports API and storing it.
"""

import time
from datetime import datetime, date
import logging
import yaml
from pathlib import Path
from yahoo_fantasy_api import League, Game
from src.auth import YahooAuthenticator
from src.database import FantasyDatabase

logger = logging.getLogger(__name__)


class FantasyDataCollector:
    """Collect fantasy baseball data from Yahoo API."""
    
    def __init__(self, config_file='config/config.yaml'):
        """
        Initialize data collector.
        
        Args:
            config_file: Path to configuration YAML file
        """
        self.config = self._load_config(config_file)
        self.auth = YahooAuthenticator()
        self.db = FantasyDatabase(self.config['database_path'])
        self.oauth = None
        self.league = None
        self.api_delay = self.config.get('api_delay_seconds', 0.5)
        
    def _load_config(self, config_file):
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def connect(self):
        """Authenticate and connect to Yahoo Fantasy API."""
        logger.info("Authenticating with Yahoo Fantasy API...")
        self.oauth = self.auth.authenticate()
        
        # Initialize game and league
        game_key = f"{self.config['game_code']}.l.{self.config['league_id']}"
        logger.info(f"Connecting to league: {game_key}")
        
        try:
            gm = Game(self.oauth, self.config['game_code'])
            self.league = gm.to_league(self.config['league_id'])
            logger.info(f"Connected to league: {self.league.settings()['name']}")
        except Exception as e:
            logger.error(f"Failed to connect to league: {e}")
            raise
    
    def collect_matchup_data(self, week=None):
        """
        Collect current matchup data for the week.
        
        Args:
            week: Week number (defaults to current week)
            
        Returns:
            List of matchup data dictionaries
        """
        if not self.league:
            raise RuntimeError("Must call connect() before collecting data")
        
        if week is None:
            week = self.league.current_week()
        
        logger.info(f"Collecting matchup data for week {week}")
        
        try:
            # Get all matchups for the week
            matchups = self.league.matchups(week)
            time.sleep(self.api_delay)  # Be respectful to API
            
            matchup_data = []
            
            for matchup in matchups['fantasy_content']['league'][1]['scoreboard']['0']['matchups'].values():
                if isinstance(matchup, dict) and 'matchup' in matchup:
                    matchup_info = matchup['matchup']
                    
                    # Extract team data
                    teams = matchup_info['0']['teams']
                    
                    team1 = teams['0']['team'][0]
                    team2 = teams['1']['team'][0]
                    
                    team1_stats = self._extract_team_stats(teams['0']['team'][1])
                    team2_stats = self._extract_team_stats(teams['1']['team'][1])
                    
                    matchup_data.append({
                        'week': week,
                        'team1_id': team1[0]['team_id'],
                        'team1_name': team1[2]['name'],
                        'team1_stats': team1_stats,
                        'team2_id': team2[0]['team_id'],
                        'team2_name': team2[2]['name'],
                        'team2_stats': team2_stats
                    })
                    
                    logger.debug(f"Collected matchup: {team1[2]['name']} vs {team2[2]['name']}")
            
            logger.info(f"Collected {len(matchup_data)} matchups")
            return matchup_data
            
        except Exception as e:
            logger.error(f"Error collecting matchup data: {e}")
            raise
    
    def _extract_team_stats(self, team_data):
        """Extract stats from team data structure."""
        stats = {}
        
        try:
            if 'team_stats' in team_data:
                for stat in team_data['team_stats']['stats']:
                    if 'stat' in stat:
                        stat_info = stat['stat']
                        stat_id = stat_info.get('stat_id')
                        value = stat_info.get('value', 0)
                        
                        # Map stat_id to readable names (these are Yahoo's stat IDs)
                        # Reference: https://yahoo-fantasy-node-docs.vercel.app/resource/game/stat_categories
                        stat_map = {
                            # Batting stats (currently collected + Yahoo points additions)
                            '7': 'R',      # Runs
                            '8': 'H',      # Hits
                            '9': '1B',     # Singles
                            '10': '2B',    # Doubles
                            '11': '3B',    # Triples
                            '12': 'HR',    # Home Runs
                            '13': 'RBI',   # RBI
                            '16': 'SB',    # Stolen Bases
                            '18': 'BB',    # Walks
                            '20': 'HBP',   # Hit by Pitch
                            '3': 'AVG',    # Batting Average
                            '6': 'AB',     # At Bats
                            '17': 'CS',    # Caught Stealing
                            '21': 'K_BAT', # Strikeouts (batting) - renamed to avoid clash with pitching K
                            
                            # Pitching stats (currently collected + Yahoo points additions)
                            '28': 'W',     # Wins
                            '32': 'SV',    # Saves
                            '42': 'K',     # Strikeouts
                            '26': 'ERA',   # ERA
                            '27': 'WHIP',  # WHIP
                            '33': 'O',     # Outs (needed for Yahoo points: O × 1)
                            '34': 'H_PIT', # Hits allowed
                            '37': 'ER',    # Earned Runs
                            '39': 'BB_PIT',# Walks allowed
                            '41': 'HBP_PIT',# Hit by Pitch (pitching)
                            '50': 'IP',    # Innings Pitched (composite from outs)
                            '29': 'L',     # Losses
                            '48': 'HLD'    # Holds
                        }
                        
                        if stat_id in stat_map:
                            stats[stat_map[stat_id]] = value
        except Exception as e:
            logger.warning(f"Error extracting team stats: {e}")
        
        return stats
    
    def collect_player_data(self, week=None):
        """
        Collect player-level stats for all teams.
        
        Args:
            week: Week number (defaults to current week)
            
        Returns:
            List of player data dictionaries
        """
        if not self.league:
            raise RuntimeError("Must call connect() before collecting data")
        
        if week is None:
            week = self.league.current_week()
        
        logger.info(f"Collecting player data for week {week}")
        
        try:
            teams = self.league.teams()
            time.sleep(self.api_delay)
            
            all_player_data = []
            
            for team in teams:
                team_key = team['team_key']
                team_id = team['team_id']
                team_name = team['name']
                
                logger.debug(f"Collecting players for team: {team_name}")
                
                # Get roster for the week
                roster = self.league.to_team(team_key).roster(week=week)
                time.sleep(self.api_delay)
                
                for player in roster:
                    try:
                        player_data = {
                            'week': week,
                            'team_id': team_id,
                            'team_name': team_name,
                            'player_id': player.get('player_id'),
                            'player_name': player.get('name', {}).get('full', 'Unknown'),
                            'position': ','.join(player.get('eligible_positions', [])),
                            'stats': self._extract_player_stats(player)
                        }
                        all_player_data.append(player_data)
                    except Exception as e:
                        logger.warning(f"Error processing player: {e}")
                        continue
            
            logger.info(f"Collected data for {len(all_player_data)} players")
            return all_player_data
            
        except Exception as e:
            logger.error(f"Error collecting player data: {e}")
            raise
    
    def _extract_player_stats(self, player_data):
        """Extract stats from player data structure."""
        stats = {}
        
        try:
            if 'player_stats' in player_data:
                for stat in player_data['player_stats'].get('stats', []):
                    if 'stat' in stat:
                        stat_info = stat['stat']
                        stat_id = stat_info.get('stat_id')
                        value = stat_info.get('value', 0)
                        
                        # Same mapping as team stats
                        stat_map = {
                            # Batting
                            '7': 'R', '8': 'H', '9': '1B', '10': '2B', '11': '3B',
                            '12': 'HR', '13': 'RBI', '16': 'SB', '18': 'BB', '20': 'HBP',
                            '3': 'AVG', '6': 'AB', '17': 'CS', '21': 'K_BAT',
                            # Pitching
                            '28': 'W', '32': 'SV', '42': 'K', '26': 'ERA', '27': 'WHIP',
                            '33': 'O', '34': 'H_PIT', '37': 'ER', '39': 'BB_PIT',
                            '41': 'HBP_PIT', '50': 'IP', '29': 'L', '48': 'HLD'
                        }
                        
                        if stat_id in stat_map:
                            stats[stat_map[stat_id]] = value
        except Exception as e:
            logger.warning(f"Error extracting player stats: {e}")
        
        return stats
    
    def save_daily_snapshot(self, snapshot_date=None, week=None):
        """
        Collect and save a complete daily snapshot.
        
        Args:
            snapshot_date: Date of snapshot (defaults to today)
            week: Week number (defaults to current week)
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        if week is None:
            week = self.league.current_week()
        
        logger.info(f"Taking daily snapshot for {snapshot_date}, week {week}")
        
        # Collect matchup data
        matchup_data = self.collect_matchup_data(week)
        
        # Save matchup snapshots
        for matchup in matchup_data:
            self.db.save_matchup_snapshot(
                date=snapshot_date,
                week=matchup['week'],
                team1_id=matchup['team1_id'],
                team1_name=matchup['team1_name'],
                team2_id=matchup['team2_id'],
                team2_name=matchup['team2_name'],
                team1_stats=matchup['team1_stats'],
                team2_stats=matchup['team2_stats']
            )
        
        logger.info(f"Saved {len(matchup_data)} matchup snapshots")
        
        # Collect player data
        player_data = self.collect_player_data(week)
        
        # Save player snapshots
        for player in player_data:
            self.db.save_player_snapshot(
                date=snapshot_date,
                week=player['week'],
                team_id=player['team_id'],
                team_name=player['team_name'],
                player_id=player['player_id'],
                player_name=player['player_name'],
                position=player['position'],
                stats=player['stats']
            )
        
        logger.info(f"Saved {len(player_data)} player snapshots")
        logger.info("Daily snapshot complete!")
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()


def main():
    """Test data collection when run directly."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        collector = FantasyDataCollector()
        collector.connect()
        collector.save_daily_snapshot()
        collector.close()
        
        print("\n✓ Data collection successful!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
