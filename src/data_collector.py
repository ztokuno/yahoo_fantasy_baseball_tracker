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

STAT_MAP = {
    # Batting
    '7': 'R', '8': 'H', '9': '1B', '10': '2B', '11': '3B',
    '12': 'HR', '13': 'RBI', '16': 'SB', '18': 'BB', '20': 'HBP',
    '3': 'AVG', '6': 'AB', '17': 'CS', '21': 'K_BAT',
    # Pitching
    '28': 'W', '32': 'SV', '42': 'K', '26': 'ERA', '27': 'WHIP',
    '33': 'O', '34': 'H_PIT', '37': 'ER', '39': 'BB_PIT',
    '41': 'HBP_PIT', '50': 'IP', '29': 'L', '48': 'HLD',
}


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

            league_data = matchups.get('fantasy_content', {}).get('league', [])
            scoreboard_obj = next(
                (item for item in league_data if isinstance(item, dict) and 'scoreboard' in item),
                None
            )
            if not scoreboard_obj:
                logger.warning("No scoreboard found in matchup response")
                return []

            scoreboard_data = scoreboard_obj['scoreboard']
            week_data = scoreboard_data.get('0') or next(
                (v for v in scoreboard_data.values() if isinstance(v, dict) and 'matchups' in v),
                None
            )
            if not week_data:
                logger.warning("No week data found in scoreboard")
                return []

            raw_matchups = week_data['matchups']
            if isinstance(raw_matchups, dict):
                matchup_items = (v for v in raw_matchups.values() if isinstance(v, dict))
            elif isinstance(raw_matchups, list):
                matchup_items = iter(raw_matchups)
            else:
                logger.warning("Unexpected matchups structure: %s", type(raw_matchups))
                return []

            for matchup in matchup_items:
                if not isinstance(matchup, dict) or 'matchup' not in matchup:
                    continue

                matchup_info = matchup['matchup']
                if isinstance(matchup_info, dict):
                    matchup_body = matchup_info.get('0') or next(
                        (v for v in matchup_info.values() if isinstance(v, dict) and 'teams' in v),
                        None
                    )
                else:
                    continue

                if not matchup_body or 'teams' not in matchup_body:
                    continue

                teams = matchup_body['teams']
                team_list = [
                    v['team'] for k, v in teams.items()
                    if k != 'count' and isinstance(v, dict) and 'team' in v
                ]
                if len(team_list) < 2:
                    logger.warning("Expected 2 teams in matchup, got %d", len(team_list))
                    continue

                team1_raw = team_list[0]
                team2_raw = team_list[1]

                team1_info = team1_raw[0] if isinstance(team1_raw, list) else team1_raw
                team2_info = team2_raw[0] if isinstance(team2_raw, list) else team2_raw
                team1_stats_raw = team1_raw[1] if isinstance(team1_raw, list) and len(team1_raw) > 1 else {}
                team2_stats_raw = team2_raw[1] if isinstance(team2_raw, list) and len(team2_raw) > 1 else {}

                team1_stats = self._extract_team_stats(team1_stats_raw)
                team2_stats = self._extract_team_stats(team2_stats_raw)

                team1_id = self._find_in_team_info(team1_info, 'team_id')
                team1_name = self._find_in_team_info(team1_info, 'name')
                team2_id = self._find_in_team_info(team2_info, 'team_id')
                team2_name = self._find_in_team_info(team2_info, 'name')

                if team1_id is None or team2_id is None:
                    logger.warning("Missing team ID in matchup (team1=%r team2=%r), skipping", team1_id, team2_id)
                    continue

                matchup_data.append({
                    'week': week,
                    'team1_id': team1_id,
                    'team1_name': team1_name,
                    'team1_stats': team1_stats,
                    'team2_id': team2_id,
                    'team2_name': team2_name,
                    'team2_stats': team2_stats,
                })

                logger.debug(f"Collected matchup: {team1_name} vs {team2_name}")
            
            logger.info(f"Collected {len(matchup_data)} matchups")
            return matchup_data
            
        except Exception as e:
            logger.error(f"Error collecting matchup data: {e}")
            raise
    
    def _extract_player_name(self, player):
        """Extract player name handling both string and dict formats from Yahoo API."""
        name = player.get('name', 'Unknown')
        if isinstance(name, dict):
            return name.get('full', 'Unknown')
        return name if isinstance(name, str) else 'Unknown'

    def _find_in_team_info(self, team_info, key):
        """Search a Yahoo team info list for a value by key, regardless of position."""
        if isinstance(team_info, list):
            for item in team_info:
                if isinstance(item, dict) and key in item:
                    return item[key]
        elif isinstance(team_info, dict):
            return team_info.get(key)
        return None

    def _extract_team_stats(self, team_data):
        """Extract stats from team data structure."""
        stats = {}

        try:
            if 'team_stats' in team_data:
                stats_raw = team_data['team_stats']['stats']
                if isinstance(stats_raw, dict):
                    stat_items = [v for k, v in stats_raw.items() if k != 'count' and isinstance(v, dict)]
                elif isinstance(stats_raw, list):
                    stat_items = stats_raw
                else:
                    stat_items = []

                for stat in stat_items:
                    if 'stat' in stat:
                        stat_info = stat['stat']
                        stat_id = stat_info.get('stat_id')
                        value = stat_info.get('value', 0)
                        if stat_id in STAT_MAP:
                            stats[STAT_MAP[stat_id]] = value
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
                            'player_name': self._extract_player_name(player),
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
                stats_raw = player_data['player_stats'].get('stats', [])
                if isinstance(stats_raw, dict):
                    stat_items = [v for k, v in stats_raw.items() if k != 'count' and isinstance(v, dict)]
                elif isinstance(stats_raw, list):
                    stat_items = stats_raw
                else:
                    stat_items = []

                for stat in stat_items:
                    if 'stat' in stat:
                        stat_info = stat['stat']
                        stat_id = stat_info.get('stat_id')
                        value = stat_info.get('value', 0)
                        if stat_id in STAT_MAP:
                            stats[STAT_MAP[stat_id]] = value
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
        if not self.league:
            raise RuntimeError("Must call connect() before collecting data")

        if snapshot_date is None:
            snapshot_date = date.today()

        if week is None:
            week = self.league.current_week()
        
        logger.info(f"Taking daily snapshot for {snapshot_date}, week {week}")
        
        # Collect matchup data
        matchup_data = self.collect_matchup_data(week)

        if not matchup_data:
            logger.warning("No matchup data collected — skipping player data collection to avoid DB inconsistency")
            return

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
