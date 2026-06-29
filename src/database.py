"""
Database Module for Yahoo Fantasy Baseball Tracker

Handles all database operations using SQLite.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class FantasyDatabase:
    """Handle all database operations for fantasy baseball tracking."""
    
    def __init__(self, db_path='data/fantasy_baseball.db'):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.initialize_database()
    
    def connect(self):
        """Create database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def initialize_database(self):
        """Create database tables if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Table for daily matchup snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matchup_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL,
                week_number INTEGER NOT NULL,
                team1_id TEXT NOT NULL,
                team1_name TEXT NOT NULL,
                team2_id TEXT NOT NULL,
                team2_name TEXT NOT NULL,
                team1_stats TEXT NOT NULL,  -- JSON
                team2_stats TEXT NOT NULL,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, week_number, team1_id, team2_id)
            )
        ''')
        
        # Table for player stats snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL,
                week_number INTEGER NOT NULL,
                team_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_position TEXT,
                stats TEXT NOT NULL,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, week_number, player_id, team_id)
            )
        ''')
        
        # Table for weekly summaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_number INTEGER NOT NULL,
                season INTEGER NOT NULL,
                summary_data TEXT NOT NULL,  -- JSON
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_number, season)
            )
        ''')
        
        # Table for player of the week
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_of_week (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_number INTEGER NOT NULL,
                season INTEGER NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_name TEXT NOT NULL,
                stat_category TEXT NOT NULL,
                stat_value REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    
    def save_matchup_snapshot(self, date, week, team1_id, team1_name, 
                            team2_id, team2_name, team1_stats, team2_stats):
        """
        Save a matchup snapshot.
        
        Args:
            date: Snapshot date
            week: Week number
            team1_id, team2_id: Team IDs
            team1_name, team2_name: Team names
            team1_stats, team2_stats: Dictionary of stats
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO matchup_snapshots 
                (snapshot_date, week_number, team1_id, team1_name, 
                 team2_id, team2_name, team1_stats, team2_stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date, week, team1_id, team1_name,
                team2_id, team2_name,
                json.dumps(team1_stats),
                json.dumps(team2_stats)
            ))
            conn.commit()
            logger.debug(f"Saved matchup snapshot: {team1_name} vs {team2_name}")
        except Exception as e:
            logger.error(f"Error saving matchup snapshot: {e}")
            raise
    
    def save_player_snapshot(self, date, week, team_id, team_name,
                           player_id, player_name, position, stats):
        """
        Save a player stats snapshot.
        
        Args:
            date: Snapshot date
            week: Week number
            team_id: Team ID
            team_name: Team name
            player_id: Player ID
            player_name: Player name
            position: Player position
            stats: Dictionary of player stats
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO player_snapshots
                (snapshot_date, week_number, team_id, team_name,
                 player_id, player_name, player_position, stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date, week, team_id, team_name,
                player_id, player_name, position,
                json.dumps(stats)
            ))
            conn.commit()
            logger.debug(f"Saved player snapshot: {player_name}")
        except Exception as e:
            logger.error(f"Error saving player snapshot: {e}")
            raise
    
    def get_matchup_snapshots(self, week=None, date=None):
        """
        Retrieve matchup snapshots.
        
        Args:
            week: Filter by week number (optional)
            date: Filter by specific date (optional)
            
        Returns:
            List of matchup snapshot records
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM matchup_snapshots WHERE 1=1"
        params = []
        
        if week:
            query += " AND week_number = ?"
            params.append(week)
        if date:
            query += " AND snapshot_date = ?"
            params.append(date)
        
        query += " ORDER BY snapshot_date DESC, week_number DESC"
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_player_snapshots(self, week=None, date=None, player_id=None):
        """
        Retrieve player snapshots.
        
        Args:
            week: Filter by week number (optional)
            date: Filter by specific date (optional)
            player_id: Filter by player ID (optional)
            
        Returns:
            List of player snapshot records
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM player_snapshots WHERE 1=1"
        params = []
        
        if week:
            query += " AND week_number = ?"
            params.append(week)
        if date:
            query += " AND snapshot_date = ?"
            params.append(date)
        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        
        query += " ORDER BY snapshot_date DESC, team_name, player_name"
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def calculate_daily_deltas(self, current_date, previous_date, week):
        """
        Calculate what changed between two snapshots.
        
        Args:
            current_date: Current snapshot date
            previous_date: Previous snapshot date
            week: Week number
            
        Returns:
            Dictionary of deltas by matchup
        """
        current = self.get_matchup_snapshots(week=week, date=current_date)
        previous = self.get_matchup_snapshots(week=week, date=previous_date)
        
        if not current or not previous:
            return None
        
        deltas = []
        for curr_matchup in current:
            # Find matching previous matchup
            for prev_matchup in previous:
                if (curr_matchup['team1_id'] == prev_matchup['team1_id'] and
                    curr_matchup['team2_id'] == prev_matchup['team2_id']):
                    
                    curr_stats1 = json.loads(curr_matchup['team1_stats'])
                    prev_stats1 = json.loads(prev_matchup['team1_stats'])
                    curr_stats2 = json.loads(curr_matchup['team2_stats'])
                    prev_stats2 = json.loads(prev_matchup['team2_stats'])
                    
                    delta = {
                        'team1_name': curr_matchup['team1_name'],
                        'team2_name': curr_matchup['team2_name'],
                        'team1_delta': self._calc_stat_delta(curr_stats1, prev_stats1),
                        'team2_delta': self._calc_stat_delta(curr_stats2, prev_stats2)
                    }
                    deltas.append(delta)
                    break
        
        return deltas
    
    def calculate_player_daily_deltas(self, current_date, previous_date, week):
        """
        Calculate per-player stat changes between two days, grouped by team.
        
        For each player present in both snapshots, computes how their stats
        changed. Players with no change in any stat are excluded from the
        results. This is the player-level equivalent of calculate_daily_deltas().
        
        Args:
            current_date: Current snapshot date
            previous_date: Previous snapshot date
            week: Week number
            
        Returns:
            List of dictionaries, one per team matchup. Each contains:
                - team1_name, team2_name: The two teams in the matchup
                - team1_players, team2_players: Lists of player delta dicts,
                  each containing player_id, player_name, position, and a
                  'delta' dict of stat changes (only stats that changed > 0)
            Returns None if either date has no data.
        """
        current_players = self.get_player_snapshots(week=week, date=current_date)
        previous_players = self.get_player_snapshots(week=week, date=previous_date)
        
        if not current_players or not previous_players:
            return None
        
        # Index previous snapshots by player_id for O(1) lookup
        previous_by_id = {}
        for p in previous_players:
            previous_by_id[p['player_id']] = p
        
        # Calculate deltas for each player, grouped by team
        players_by_team = {}
        for curr in current_players:
            player_id = curr['player_id']
            team_id = curr['team_id']
            
            # Initialize team entry if needed
            if team_id not in players_by_team:
                players_by_team[team_id] = {
                    'team_name': curr['team_name'],
                    'players': []
                }
            
            # Skip if we have no previous snapshot for this player
            if player_id not in previous_by_id:
                continue
            
            prev = previous_by_id[player_id]
            curr_stats = json.loads(curr['stats'])
            prev_stats = json.loads(prev['stats'])
            
            delta = self._calc_stat_delta(curr_stats, prev_stats)
            
            # Only include players who actually contributed something today
            has_contribution = any(
                v > 0 for v in delta.values()
                if isinstance(v, (int, float))
            )
            
            if has_contribution:
                players_by_team[team_id]['players'].append({
                    'player_id': player_id,
                    'player_name': curr['player_name'],
                    'position': curr['player_position'],
                    'delta': delta
                })
        
        # Now pair teams up into matchups using matchup_snapshots
        # so we know which teams faced each other
        current_matchups = self.get_matchup_snapshots(week=week, date=current_date)
        
        if not current_matchups:
            return None
        
        results = []
        for matchup in current_matchups:
            t1_id = matchup['team1_id']
            t2_id = matchup['team2_id']
            
            results.append({
                'team1_name': matchup['team1_name'],
                'team2_name': matchup['team2_name'],
                'team1_players': players_by_team.get(t1_id, {}).get('players', []),
                'team2_players': players_by_team.get(t2_id, {}).get('players', [])
            })
        
        return results
    
    def _calc_stat_delta(self, current_stats, previous_stats):
        """Calculate the difference between two stat dictionaries."""
        delta = {}
        for stat, value in current_stats.items():
            try:
                curr = float(value)
            except (ValueError, TypeError):
                curr = 0.0
            if stat in previous_stats:
                try:
                    delta[stat] = curr - float(previous_stats[stat])
                except (ValueError, TypeError):
                    delta[stat] = curr
            else:
                delta[stat] = curr
        return delta


def main():
    """Test database operations when run directly."""
    logging.basicConfig(level=logging.INFO)
    
    db = FantasyDatabase()
    print("✓ Database initialized successfully")
    print(f"✓ Database location: {db.db_path.absolute()}")
    
    # Test snapshot
    from datetime import date
    db.save_matchup_snapshot(
        date=date.today(),
        week=1,
        team1_id="test1",
        team1_name="Test Team 1",
        team2_id="test2",
        team2_name="Test Team 2",
        team1_stats={"R": 10, "HR": 5, "RBI": 15},
        team2_stats={"R": 8, "HR": 3, "RBI": 12}
    )
    print("✓ Test matchup snapshot saved")
    
    db.close()


if __name__ == "__main__":
    main()
