"""
Analyzer Module

Generate recaps, summaries, and analyze fantasy baseball data.
"""

import json
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import logging
import yaml
from src.database import FantasyDatabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stat category definitions
# ---------------------------------------------------------------------------
# These are the batting and pitching categories used throughout the analyzer.
# "lower_is_better" flags the stats where a smaller number is actually good
# (ERA and WHIP for pitching, ER for counting, K_BAT and CS for batting).
# This is used by the composite scorers to invert those stats so they
# contribute positively to the composite score.
# ---------------------------------------------------------------------------
BATTING_STATS = ['R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'SB', 'BB', 'HBP', 'AVG', 'AB']
PITCHING_STATS = ['W', 'SV', 'K', 'ERA', 'WHIP', 'O', 'H_PIT', 'ER', 'BB_PIT', 'HBP_PIT', 'IP', 'L', 'HLD']
LOWER_IS_BETTER = {'ERA', 'WHIP', 'ER', 'K_BAT', 'CS', 'L', 'H_PIT', 'BB_PIT', 'HBP_PIT'}


class CompositeScorer:
    """
    Calculate composite scores for players across multiple stat categories.
    
    Supports multiple scoring methods, selectable at runtime:
        - zscore:       Z-Score Normalization (default). Converts each stat to
                        standard deviations from the league mean. Statistically
                        rigorous but assumes roughly normal distributions.
        - percentile:   Percentile Ranking. Converts each stat to a 0-100
                        percentile representing where the player falls in the
                        league. More intuitive to interpret than z-scores and
                        less sensitive to outliers.
        - minmax:       Min-Max Scaling. Rescales each stat to a 0-1 range
                        where 0 is the worst and 1 is the best. Simple and
                        always bounded, but sensitive to outliers compressing
                        everyone else's scores.
        - weighted_points: Weighted Category Points. Ranks players 1-N for
                        each stat and awards points based on rank, then
                        multiplies by a configurable weight per category.
                        Most customizable — tune weights to match how your
                        league actually values each stat.
        - yahoo_points: Yahoo Fantasy Baseball Default Points. Multiplies
                        each stat directly by Yahoo's official default point
                        values (e.g. HR x 10.4, W x 8, K x 3). This mirrors
                        how Yahoo itself scores players in Head-to-Head Points
                        leagues. All stats required for Yahoo points scoring
                        are now collected by data_collector.py.
    
    Usage:
        scorer = CompositeScorer(method='zscore')
        scores = scorer.score_players(player_stats_list, stat_categories)
    """
    
    VALID_METHODS = ('zscore', 'percentile', 'minmax', 'weighted_points', 'yahoo_points')
    
    # ---------------------------------------------------------------------------
    # Yahoo Fantasy Baseball default Head-to-Head Points values.
    # Source: https://help.yahoo.com/kb/default-league-settings-fantasy-baseball-sln6785.html
    #
    # Negative values mean the stat hurts your score (e.g. ER, BB_PIT for pitchers).
    # All stats below are now collected by data_collector.py.
    # ---------------------------------------------------------------------------
    YAHOO_POINTS_VALUES = {
        # Batting stats
        'R':   1.9,
        'HR':  10.4,
        'RBI': 1.9,
        'SB':  4.2,
        '1B':  2.6,    # Singles
        '2B':  5.2,    # Doubles
        '3B':  7.8,    # Triples
        'BB':  2.6,    # Walks (batting)
        'HBP': 2.6,    # Hit by Pitch (batting)
        # Pitching stats
        'W':   8.0,
        'SV':  8.0,
        'K':   3.0,
        'ER':  -3.0,   # Earned Runs
        'O':   1.0,    # Outs
        'BB_PIT': -1.3,# Walks (pitching)
        'H_PIT': -1.3, # Hits allowed
        'HBP_PIT': -1.3# Hit by Pitch (pitching)
    }
    
    # Default weights for weighted_points method.
    # These can be overridden by passing custom weights at init.
    DEFAULT_WEIGHTS = {
        'R': 1.0, 'HR': 1.5, 'RBI': 1.0, 'SB': 1.0, 'AVG': 1.0,
        'W': 1.5, 'K': 1.0, 'SV': 1.5, 'ERA': 1.5, 'WHIP': 1.5
    }
    
    def __init__(self, method='zscore', weights=None):
        """
        Initialize the scorer.
        
        Args:
            method: Scoring method to use (see class docstring for options)
            weights: Dict of {stat: weight} for the weighted_points method.
                     If None, DEFAULT_WEIGHTS is used. Ignored for other methods.
        """
        if method not in self.VALID_METHODS:
            raise ValueError(
                f"Invalid method '{method}'. Must be one of: {self.VALID_METHODS}"
            )
        self.method = method
        self.weights = weights if weights is not None else dict(self.DEFAULT_WEIGHTS)
    
    def score_players(self, players, stat_categories):
        """
        Score a list of players using the configured method.
        
        Each player dict must have at least 'player_name', 'team_name',
        'position', and 'stats' (a dict of stat values).
        
        Args:
            players: List of player dicts (see format above)
            stat_categories: List of stat category strings to score on
            
        Returns:
            The same list of player dicts, each with a 'composite_score' key
            added and sorted descending by that score.
        """
        if not players:
            return []
        
        # Build a matrix: rows = players, columns = stat categories.
        # Missing stats default to 0.
        matrix = []
        for p in players:
            row = []
            for stat in stat_categories:
                try:
                    row.append(float(p['stats'].get(stat, 0)))
                except (ValueError, TypeError):
                    row.append(0.0)
            matrix.append(row)
        
        data = np.array(matrix, dtype=float)
        
        # Dispatch to the selected scoring method
        if self.method == 'zscore':
            scores = self._score_zscore(data, stat_categories)
        elif self.method == 'percentile':
            scores = self._score_percentile(data, stat_categories)
        elif self.method == 'minmax':
            scores = self._score_minmax(data, stat_categories)
        elif self.method == 'weighted_points':
            scores = self._score_weighted_points(data, stat_categories)
        elif self.method == 'yahoo_points':
            scores = self._score_yahoo_points(data, stat_categories)
        
        # Attach scores back to the player dicts
        for player, score in zip(players, scores):
            player['composite_score'] = round(score, 3)
        
        # Sort descending by composite score
        players.sort(key=lambda p: p['composite_score'], reverse=True)
        return players
    
    def _score_zscore(self, data, stat_categories):
        """
        Z-Score Normalization.
        
        For each stat column, subtract the mean and divide by the standard
        deviation. This converts each stat to "how many standard deviations
        above or below average is this player?" Stats in LOWER_IS_BETTER are
        negated so that a good (low) value contributes positively. The final
        composite is the sum of z-scores across all categories.
        """
        scores = np.zeros(len(data))
        
        for i, stat in enumerate(stat_categories):
            col = data[:, i]
            mean = np.mean(col)
            std = np.std(col)
            
            if std == 0:
                # All players have the same value — no differentiation possible
                continue
            
            z = (col - mean) / std
            
            # Invert stats where lower is better
            if stat in LOWER_IS_BETTER:
                z = -z
            
            scores += z
        
        return scores
    
    def _score_percentile(self, data, stat_categories):
        """
        Percentile Ranking.
        
        For each stat column, convert each player's value to a percentile
        (0-100) representing the fraction of players they scored above.
        Stats in LOWER_IS_BETTER are inverted (100 - percentile) so that
        a good (low) value maps to a high percentile. The final composite
        is the sum of percentiles across all categories.
        """
        n = len(data)
        scores = np.zeros(n)
        
        for i, stat in enumerate(stat_categories):
            col = data[:, i]
            # For each player, count how many players they beat
            percentiles = np.array([
                np.sum(col < val) / (n - 1) * 100 if n > 1 else 50.0
                for val in col
            ])
            
            if stat in LOWER_IS_BETTER:
                percentiles = 100 - percentiles
            
            scores += percentiles
        
        return scores
    
    def _score_minmax(self, data, stat_categories):
        """
        Min-Max Scaling.
        
        For each stat column, rescale values to a 0-1 range where 0 is the
        worst value and 1 is the best. Stats in LOWER_IS_BETTER are inverted
        (1 - scaled) so that a good (low) value maps to 1. The final
        composite is the sum of scaled values across all categories.
        """
        scores = np.zeros(len(data))
        
        for i, stat in enumerate(stat_categories):
            col = data[:, i]
            col_min = np.min(col)
            col_max = np.max(col)
            
            if col_max == col_min:
                # All values are the same — no differentiation possible
                continue
            
            scaled = (col - col_min) / (col_max - col_min)
            
            if stat in LOWER_IS_BETTER:
                scaled = 1 - scaled
            
            scores += scaled
        
        return scores
    
    def _score_weighted_points(self, data, stat_categories):
        """
        Weighted Category Points.
        
        For each stat column, rank players from 1 (worst) to N (best) and
        award points equal to their rank. Stats in LOWER_IS_BETTER are
        ranked in reverse (rank 1 = lowest value = best). Each category's
        points are then multiplied by that category's configured weight.
        The final composite is the sum of weighted points.
        """
        n = len(data)
        scores = np.zeros(n)
        
        for i, stat in enumerate(stat_categories):
            col = data[:, i]
            weight = self.weights.get(stat, 1.0)
            
            # argsort gives indices that would sort the array.
            # argsort of argsort gives the rank (0-based), so add 1.
            if stat in LOWER_IS_BETTER:
                # Reverse sort: lowest value gets highest rank
                ranks = np.argsort(np.argsort(-col)) + 1
            else:
                ranks = np.argsort(np.argsort(col)) + 1
            
            scores += ranks * weight
        
        return scores
    
    def _score_yahoo_points(self, data, stat_categories):
        """
        Yahoo Fantasy Baseball Default Points.
        
        Multiplies each player's raw stat value by Yahoo's official default
        point value for that stat. This is fundamentally different from the
        other methods: those all compare players against each other (ranks,
        percentiles, deviations from the mean). This one is absolute — a
        player's score depends only on their own stats, not on what anyone
        else did. A pitcher with 2 wins scores 16.0 points regardless of
        whether everyone else had 0 wins or 5 wins.
        
        Stats not present in YAHOO_POINTS_VALUES are skipped (score 0 for
        that category). All Yahoo points stats are now collected by
        data_collector.py, so you should get a complete and accurate score.
        
        Note on AVG, ERA, WHIP, IP: Yahoo's points system does not use these
        rate/composite stats — it uses the underlying counting stats that go
        into them (e.g. hits, earned runs, outs). So these are intentionally
        skipped even if present.
        """
        # Rate/composite stats that Yahoo points doesn't use — skip these
        SKIP_STATS = {'AVG', 'ERA', 'WHIP', 'IP', 'AB', 'H', 'CS', 'K_BAT', 'L'}
        
        scores = np.zeros(len(data))
        
        for i, stat in enumerate(stat_categories):
            if stat in SKIP_STATS:
                continue
            
            point_value = self.YAHOO_POINTS_VALUES.get(stat)
            if point_value is None:
                # Stat has no Yahoo point value defined — skip it
                logger.debug(f"yahoo_points: no point value for '{stat}', skipping")
                continue
            
            col = data[:, i]
            scores += col * point_value
        
        return scores


class FantasyAnalyzer:
    """Analyze fantasy baseball data and generate recaps."""
    
    def __init__(self, db_path='data/fantasy_baseball.db', config_file='config/config.yaml'):
        """
        Initialize analyzer with database and config.
        
        Args:
            db_path: Path to SQLite database
            config_file: Path to config.yaml
        """
        self.db = FantasyDatabase(db_path)
        self.config = self._load_config(config_file)
    
    def _load_config(self, config_file):
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_file}. Using defaults.")
            return {}
    
    # ------------------------------------------------------------------
    # Player classification helpers
    # ------------------------------------------------------------------
    
    def _classify_player(self, position_str):
        """
        Determine whether a player is a batter or pitcher from their
        position string.
        
        Yahoo returns positions as a comma-separated string like
        "1B,DH" or "SP,RP". If any pitching position code is present
        the player is classified as a pitcher; otherwise a batter.
        
        Args:
            position_str: Comma-separated position string from Yahoo
            
        Returns:
            'pitcher' or 'batter'
        """
        pitching_positions = {'SP', 'RP', 'P'}
        if not position_str:
            return 'batter'  # default
        positions = {p.strip() for p in position_str.split(',')}
        return 'pitcher' if positions & pitching_positions else 'batter'
    
    # ------------------------------------------------------------------
    # Weekly player data
    # ------------------------------------------------------------------
    
    def _get_weekly_player_totals(self, week):
        """
        Get each player's final (cumulative) stats for a week.
        
        Since Yahoo stats are cumulative within a week, the last snapshot
        of the week IS the weekly total — no summing required. This method
        finds the latest snapshot date for the week and returns one entry
        per player from that date.
        
        Args:
            week: Week number
            
        Returns:
            List of player dicts with keys: player_id, player_name,
            team_name, position, player_type ('batter'/'pitcher'), stats
        """
        snapshots = self.db.get_player_snapshots(week=week)
        
        if not snapshots:
            return []
        
        # Latest snapshot date = end-of-week totals
        latest_date = max(s['snapshot_date'] for s in snapshots)
        latest = [s for s in snapshots if s['snapshot_date'] == latest_date]
        
        players = []
        for s in latest:
            players.append({
                'player_id': s['player_id'],
                'player_name': s['player_name'],
                'team_name': s['team_name'],
                'position': s['player_position'],
                'player_type': self._classify_player(s['player_position']),
                'stats': json.loads(s['stats'])
            })
        
        return players
    
    # ------------------------------------------------------------------
    # Per-stat leaders
    # ------------------------------------------------------------------
    
    def get_stat_leaders(self, week, stat_categories, n=1):
        """
        Rank players by each stat category and return the top and bottom N.
        
        Results are split by batter/pitcher automatically — batting stats
        only rank batters, pitching stats only rank pitchers.
        
        Args:
            week: Week number
            stat_categories: List of stat strings to rank (e.g. ['HR', 'K'])
            n: How many top/bottom players to return per category
            
        Returns:
            Dict of {stat: {'leaders': [...], 'trailers': [...]}}
            Each entry in leaders/trailers is a player dict with the stat
            value included.
        """
        players = self._get_weekly_player_totals(week)
        if not players:
            return {}
        
        results = {}
        for stat in stat_categories:
            # Filter to the right player type for this stat
            if stat in BATTING_STATS:
                pool = [p for p in players if p['player_type'] == 'batter']
            elif stat in PITCHING_STATS:
                pool = [p for p in players if p['player_type'] == 'pitcher']
            else:
                pool = players
            
            # Filter to players who actually have this stat
            ranked = []
            for p in pool:
                try:
                    value = float(p['stats'].get(stat, 0))
                    ranked.append({**p, 'stat_value': value})
                except (ValueError, TypeError):
                    continue
            
            if not ranked:
                continue
            
            # For lower-is-better stats, best = lowest, so sort ascending
            reverse = stat not in LOWER_IS_BETTER
            ranked.sort(key=lambda p: p['stat_value'], reverse=reverse)
            
            results[stat] = {
                'leaders': ranked[:n],
                'trailers': ranked[-n:]  # worst N (reverse of best)
            }
        
        return results
    
    # ------------------------------------------------------------------
    # Composite scoring (best/worst batter and pitcher)
    # ------------------------------------------------------------------
    
    def get_composite_leaders(self, week, method='zscore', weights=None, n=1):
        """
        Score all players with a composite method and return the best and
        worst batter and pitcher for the week.
        
        Args:
            week: Week number
            method: Composite scoring method. One of:
                    'zscore', 'percentile', 'minmax', 'weighted_points'
            weights: Optional dict of {stat: weight} for weighted_points.
                     Ignored for other methods.
            n: Number of top/bottom players to return per group
            
        Returns:
            Dict with keys 'batters' and 'pitchers', each containing:
                - 'best': top N players by composite score
                - 'worst': bottom N players by composite score
                - 'method': the scoring method used
        """
        players = self._get_weekly_player_totals(week)
        if not players:
            return {}
        
        scorer = CompositeScorer(method=method, weights=weights)
        
        batters = [p for p in players if p['player_type'] == 'batter']
        pitchers = [p for p in players if p['player_type'] == 'pitcher']
        
        # Score each group against its own relevant stats
        scored_batters = scorer.score_players(batters, BATTING_STATS)
        scored_pitchers = scorer.score_players(pitchers, PITCHING_STATS)
        
        return {
            'batters': {
                'best': scored_batters[:n],
                'worst': scored_batters[-n:],
                'method': method
            },
            'pitchers': {
                'best': scored_pitchers[:n],
                'worst': scored_pitchers[-n:],
                'method': method
            }
        }
    
    # ------------------------------------------------------------------
    # Daily recap (with player attribution)
    # ------------------------------------------------------------------
    
    def get_daily_recap(self, week, current_date=None, previous_date=None):
        """
        Generate a daily recap that shows both team-level and player-level
        changes since yesterday.
        
        For each matchup, returns:
            - The team-level stat deltas (what changed at the matchup level)
            - The individual players who contributed, with their own deltas
        
        Args:
            week: Week number
            current_date: Current date (defaults to today)
            previous_date: Previous date (defaults to yesterday)
            
        Returns:
            List of matchup recap dicts, each containing team deltas and
            the contributing players. Returns None if data is missing.
        """
        if current_date is None:
            current_date = date.today()
        if previous_date is None:
            previous_date = current_date - timedelta(days=1)
        
        current_str = str(current_date)
        previous_str = str(previous_date)
        
        # Get both team-level and player-level deltas
        team_deltas = self.db.calculate_daily_deltas(current_str, previous_str, week)
        player_deltas = self.db.calculate_player_daily_deltas(current_str, previous_str, week)
        
        if not team_deltas or not player_deltas:
            return None
        
        # Merge player deltas into the team deltas by matching team names
        recaps = []
        for team_delta in team_deltas:
            # Find the matching player delta entry
            matching_players = None
            for pd_entry in player_deltas:
                if (pd_entry['team1_name'] == team_delta['team1_name'] and
                    pd_entry['team2_name'] == team_delta['team2_name']):
                    matching_players = pd_entry
                    break
            
            recaps.append({
                'team1_name': team_delta['team1_name'],
                'team2_name': team_delta['team2_name'],
                'team1_delta': team_delta['team1_delta'],
                'team2_delta': team_delta['team2_delta'],
                'team1_players': matching_players['team1_players'] if matching_players else [],
                'team2_players': matching_players['team2_players'] if matching_players else []
            })
        
        return recaps
    
    # ------------------------------------------------------------------
    # Highlight and moment detection
    # ------------------------------------------------------------------
    
    def identify_clutch_players(self, week, current_date=None, previous_date=None):
        """
        Identify players who made clutch contributions in close stat categories.
        
        A contribution is "clutch" if:
        - The player contributed significantly to that stat category
        - The matchup in that category is close (within 20% margin)
        
        Args:
            week: Week number
            current_date: Date to analyze (defaults to today)
            previous_date: Previous date for delta calculation
            
        Returns:
            List of clutch moment dicts with player info, stat, contribution, margin
        """
        from datetime import timedelta
        
        if current_date is None:
            current_date = date.today()
        if previous_date is None:
            previous_date = current_date - timedelta(days=1)
        
        current_str = str(current_date)
        previous_str = str(previous_date)
        
        # Get player deltas and matchup totals
        player_deltas = self.db.calculate_player_daily_deltas(current_str, previous_str, week)
        matchup_snapshots = self.db.get_matchup_snapshots(week=week, date=current_str)
        
        if not player_deltas or not matchup_snapshots:
            return []
        
        clutch_moments = []
        
        for matchup_delta in player_deltas:
            team1_name = matchup_delta['team1_name']
            team2_name = matchup_delta['team2_name']
            
            # Find the corresponding matchup snapshot to get totals
            matchup_total = None
            for snap in matchup_snapshots:
                if snap['team1_name'] == team1_name and snap['team2_name'] == team2_name:
                    matchup_total = snap
                    break
            
            if not matchup_total:
                continue
            
            team1_stats = json.loads(matchup_total['team1_stats'])
            team2_stats = json.loads(matchup_total['team2_stats'])
            
            # Check each stat category for closeness
            for stat in team1_stats.keys():
                if stat not in team2_stats:
                    continue
                
                try:
                    val1 = float(team1_stats[stat])
                    val2 = float(team2_stats[stat])
                except (ValueError, TypeError):
                    continue
                
                # Skip if both are zero
                if val1 == 0 and val2 == 0:
                    continue
                
                # Calculate margin (as % of the leader's total)
                leader_val = max(val1, val2)
                if leader_val == 0:
                    continue
                
                margin = abs(val1 - val2) / leader_val
                
                # Close category = within 20% margin
                if margin > 0.20:
                    continue
                
                # Now check if any player on either team contributed significantly
                # to this stat today (>= 25% of the current margin)
                threshold = abs(val1 - val2) * 0.25
                
                # Check team 1 players
                for player in matchup_delta['team1_players']:
                    contrib = player['delta'].get(stat, 0)
                    if isinstance(contrib, (int, float)) and contrib >= threshold:
                        clutch_moments.append({
                            'player_name': player['player_name'],
                            'team_name': team1_name,
                            'opponent': team2_name,
                            'stat': stat,
                            'contribution': contrib,
                            'margin': abs(val1 - val2),
                            'margin_pct': margin,
                            'date': current_date
                        })
                
                # Check team 2 players
                for player in matchup_delta['team2_players']:
                    contrib = player['delta'].get(stat, 0)
                    if isinstance(contrib, (int, float)) and contrib >= threshold:
                        clutch_moments.append({
                            'player_name': player['player_name'],
                            'team_name': team2_name,
                            'opponent': team1_name,
                            'stat': stat,
                            'contribution': contrib,
                            'margin': abs(val1 - val2),
                            'margin_pct': margin,
                            'date': current_date
                        })
        
        # Sort by margin_pct (lower = more clutch)
        clutch_moments.sort(key=lambda x: x['margin_pct'])
        
        return clutch_moments
    
    def identify_key_moments(self, week):
        """
        Scan the entire week for notable moments and storylines.
        
        Identifies:
        - Dominant performances (player led league in a stat)
        - Blowout categories (one team won by >50%)
        - Comeback categories (team behind mid-week but won)
        - Cold streaks (player underperformed for multiple days)
        
        Args:
            week: Week number
            
        Returns:
            Dict with lists of different moment types
        """
        snapshots = self.db.get_matchup_snapshots(week=week)
        player_snapshots = self.db.get_player_snapshots(week=week)
        
        if not snapshots or not player_snapshots:
            return {}
        
        # Get all dates for this week
        dates = sorted(set(s['snapshot_date'] for s in snapshots))
        
        if len(dates) < 2:
            return {}  # Need at least 2 days for trends
        
        moments = {
            'blowouts': [],
            'comebacks': [],
            'dominant_players': []
        }
        
        # Find blowouts (using final day)
        final_date = dates[-1]
        final_snapshots = [s for s in snapshots if s['snapshot_date'] == final_date]
        
        for snap in final_snapshots:
            team1_stats = json.loads(snap['team1_stats'])
            team2_stats = json.loads(snap['team2_stats'])
            
            for stat in team1_stats.keys():
                if stat not in team2_stats:
                    continue
                
                try:
                    val1 = float(team1_stats[stat])
                    val2 = float(team2_stats[stat])
                except (ValueError, TypeError):
                    continue
                
                if val1 == 0 and val2 == 0:
                    continue
                
                leader_val = max(val1, val2)
                if leader_val == 0:
                    continue
                
                margin = abs(val1 - val2) / leader_val
                
                # Blowout = margin > 50%
                if margin > 0.50:
                    winner = snap['team1_name'] if val1 > val2 else snap['team2_name']
                    moments['blowouts'].append({
                        'winner': winner,
                        'stat': stat,
                        'margin_pct': margin,
                        'winner_value': max(val1, val2),
                        'loser_value': min(val1, val2)
                    })
        
        # Find dominant players (led league in a stat)
        final_players = [s for s in player_snapshots if s['snapshot_date'] == final_date]
        
        for stat in BATTING_STATS + PITCHING_STATS:
            # Skip rate stats for "dominant" designation
            if stat in {'AVG', 'ERA', 'WHIP', 'IP'}:
                continue
            
            best_player = None
            best_value = float('-inf') if stat not in LOWER_IS_BETTER else float('inf')
            
            for snap in final_players:
                stats = json.loads(snap['stats'])
                if stat not in stats:
                    continue
                
                try:
                    value = float(stats[stat])
                except (ValueError, TypeError):
                    continue
                
                if stat in LOWER_IS_BETTER:
                    if value < best_value and value > 0:
                        best_value = value
                        best_player = snap
                else:
                    if value > best_value:
                        best_value = value
                        best_player = snap
            
            if best_player and best_value != 0:
                moments['dominant_players'].append({
                    'player_name': best_player['player_name'],
                    'team_name': best_player['team_name'],
                    'stat': stat,
                    'value': best_value
                })
        
        # Find comebacks (team behind mid-week but won the category)
        # Compare midweek (around day 3-4) to final day
        if len(dates) >= 5:  # Need enough days to identify a comeback
            midweek_date = dates[len(dates) // 2]  # Roughly middle of the week
            midweek_snapshots = [s for s in snapshots if s['snapshot_date'] == midweek_date]
            
            # Match up midweek and final snapshots for same matchups
            for mid_snap in midweek_snapshots:
                # Find corresponding final snapshot
                final_snap = None
                for f_snap in final_snapshots:
                    if (f_snap['team1_id'] == mid_snap['team1_id'] and
                        f_snap['team2_id'] == mid_snap['team2_id']):
                        final_snap = f_snap
                        break
                
                if not final_snap:
                    continue
                
                mid_team1_stats = json.loads(mid_snap['team1_stats'])
                mid_team2_stats = json.loads(mid_snap['team2_stats'])
                final_team1_stats = json.loads(final_snap['team1_stats'])
                final_team2_stats = json.loads(final_snap['team2_stats'])
                
                for stat in mid_team1_stats.keys():
                    if stat not in mid_team2_stats or stat not in final_team1_stats or stat not in final_team2_stats:
                        continue
                    
                    try:
                        mid_val1 = float(mid_team1_stats[stat])
                        mid_val2 = float(mid_team2_stats[stat])
                        final_val1 = float(final_team1_stats[stat])
                        final_val2 = float(final_team2_stats[stat])
                    except (ValueError, TypeError):
                        continue
                    
                    # Check if team was behind midweek but won by end
                    # For lower-is-better stats, reverse the comparison
                    if stat in LOWER_IS_BETTER:
                        # Team1 comeback: was losing midweek (higher value) but won final (lower value)
                        if mid_val1 > mid_val2 and final_val1 < final_val2 and mid_val1 > 0 and final_val1 > 0:
                            moments['comebacks'].append({
                                'team': mid_snap['team1_name'],
                                'opponent': mid_snap['team2_name'],
                                'stat': stat,
                                'midweek_value': mid_val1,
                                'final_value': final_val1,
                                'opponent_final': final_val2
                            })
                        # Team2 comeback: was losing midweek but won final
                        elif mid_val2 > mid_val1 and final_val2 < final_val1 and mid_val2 > 0 and final_val2 > 0:
                            moments['comebacks'].append({
                                'team': mid_snap['team2_name'],
                                'opponent': mid_snap['team1_name'],
                                'stat': stat,
                                'midweek_value': mid_val2,
                                'final_value': final_val2,
                                'opponent_final': final_val1
                            })
                    else:
                        # Team1 comeback: was losing midweek (lower value) but won final (higher value)
                        if mid_val1 < mid_val2 and final_val1 > final_val2:
                            moments['comebacks'].append({
                                'team': mid_snap['team1_name'],
                                'opponent': mid_snap['team2_name'],
                                'stat': stat,
                                'midweek_value': mid_val1,
                                'final_value': final_val1,
                                'opponent_final': final_val2
                            })
                        # Team2 comeback: was losing midweek but won final
                        elif mid_val2 < mid_val1 and final_val2 > final_val1:
                            moments['comebacks'].append({
                                'team': mid_snap['team2_name'],
                                'opponent': mid_snap['team1_name'],
                                'stat': stat,
                                'midweek_value': mid_val2,
                                'final_value': final_val2,
                                'opponent_final': final_val1
                            })
        
        return moments
    
    # ------------------------------------------------------------------
    # Weekly recap
    # ------------------------------------------------------------------
    
    def get_weekly_matchup_summary(self, week):
        """
        Generate a summary of all matchups for a week.
        
        Args:
            week: Week number
            
        Returns:
            List of dictionaries with matchup summaries
        """
        snapshots = self.db.get_matchup_snapshots(week=week)
        
        if not snapshots:
            logger.warning(f"No data found for week {week}")
            return []
        
        latest_date = max(s['snapshot_date'] for s in snapshots)
        latest_snapshots = [s for s in snapshots if s['snapshot_date'] == latest_date]
        
        summaries = []
        for snapshot in latest_snapshots:
            team1_stats = json.loads(snapshot['team1_stats'])
            team2_stats = json.loads(snapshot['team2_stats'])
            
            summary = {
                'team1': snapshot['team1_name'],
                'team2': snapshot['team2_name'],
                'team1_stats': team1_stats,
                'team2_stats': team2_stats,
                'date': snapshot['snapshot_date']
            }
            summaries.append(summary)
        
        return summaries
    
    def get_matchup_score_progression(self, week):
        """
        Calculate the day-by-day matchup score (categories won) for each team.
        
        For head-to-head categories leagues, this shows how many stat categories
        each team is winning on each day of the week. The result can be plotted
        as a line chart to show the progression of the matchup.
        
        Args:
            week: Week number
            
        Returns:
            List of dicts, one per matchup, each containing:
                - team1_name, team2_name: Team names
                - dates: List of dates (strings) in chronological order
                - team1_scores: List of category counts for team1 by day
                - team2_scores: List of category counts for team2 by day
                - stat_categories: List of stat categories being compared
            Returns empty list if no data.
        """
        snapshots = self.db.get_matchup_snapshots(week=week)
        
        if not snapshots:
            logger.warning(f"No matchup data for week {week}")
            return []
        
        # Group snapshots by matchup (team1_id, team2_id pair)
        matchups = {}
        for snap in snapshots:
            key = (snap['team1_id'], snap['team2_id'])
            if key not in matchups:
                matchups[key] = {
                    'team1_name': snap['team1_name'],
                    'team2_name': snap['team2_name'],
                    'snapshots': []
                }
            matchups[key]['snapshots'].append(snap)
        
        results = []
        
        for matchup_key, matchup_data in matchups.items():
            # Sort snapshots by date
            sorted_snapshots = sorted(
                matchup_data['snapshots'],
                key=lambda s: s['snapshot_date']
            )
            
            dates = []
            team1_scores = []
            team2_scores = []
            stat_categories = None
            
            for snap in sorted_snapshots:
                team1_stats = json.loads(snap['team1_stats'])
                team2_stats = json.loads(snap['team2_stats'])
                
                # Determine stat categories from first snapshot
                if stat_categories is None:
                    stat_categories = sorted(
                        set(team1_stats.keys()) & set(team2_stats.keys())
                    )
                
                # Count categories won by each team
                team1_wins = 0
                team2_wins = 0
                
                for stat in stat_categories:
                    if stat not in team1_stats or stat not in team2_stats:
                        continue
                    
                    try:
                        val1 = float(team1_stats[stat])
                        val2 = float(team2_stats[stat])
                        
                        # For lower-is-better stats, reverse the comparison
                        if stat in LOWER_IS_BETTER:
                            if val1 < val2 and val1 > 0:
                                team1_wins += 1
                            elif val2 < val1 and val2 > 0:
                                team2_wins += 1
                            # If tied or both zero, neither wins
                        else:
                            if val1 > val2:
                                team1_wins += 1
                            elif val2 > val1:
                                team2_wins += 1
                    except (ValueError, TypeError):
                        # Skip non-numeric stats
                        continue
                
                dates.append(snap['snapshot_date'])
                team1_scores.append(team1_wins)
                team2_scores.append(team2_wins)
            
            results.append({
                'team1_name': matchup_data['team1_name'],
                'team2_name': matchup_data['team2_name'],
                'dates': dates,
                'team1_scores': team1_scores,
                'team2_scores': team2_scores,
                'stat_categories': stat_categories
            })
        
        return results
    
    def generate_weekly_recap(self, week, composite_method='zscore', composite_weights=None):
        """
        Generate a comprehensive weekly recap.
        
        Includes matchup results, per-stat leaders and trailers (split by
        batter/pitcher), and composite best/worst batter and pitcher.
        
        Args:
            week: Week number
            composite_method: Scoring method for best/worst player.
                              One of: 'zscore', 'percentile', 'minmax', 'weighted_points'
            composite_weights: Optional weights dict for weighted_points method
            
        Returns:
            Dictionary with the full recap
        """
        logger.info(f"Generating weekly recap for week {week} (composite: {composite_method})")
        
        matchup_summary = self.get_weekly_matchup_summary(week)
        
        stat_leaders = self.get_stat_leaders(
            week,
            stat_categories=BATTING_STATS + PITCHING_STATS
        )
        
        composite_leaders = self.get_composite_leaders(
            week,
            method=composite_method,
            weights=composite_weights
        )
        
        return {
            'week': week,
            'matchups': matchup_summary,
            'stat_leaders': stat_leaders,
            'composite_leaders': composite_leaders,
            'composite_method': composite_method,
            'generated_at': str(date.today())
        }
    
    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    
    def export_to_csv(self, week=None, output_dir='data/exports'):
        """
        Export data to CSV files for R analysis.
        
        Args:
            week: Week number (None for all data)
            output_dir: Directory to save CSV files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Export matchup data
        matchup_snapshots = self.db.get_matchup_snapshots(week=week)
        if matchup_snapshots:
            matchup_data = []
            for snap in matchup_snapshots:
                team1_stats = json.loads(snap['team1_stats'])
                team2_stats = json.loads(snap['team2_stats'])
                
                matchup_data.append({
                    'date': snap['snapshot_date'],
                    'week': snap['week_number'],
                    'team1': snap['team1_name'],
                    'team2': snap['team2_name'],
                    **{f'team1_{k}': v for k, v in team1_stats.items()},
                    **{f'team2_{k}': v for k, v in team2_stats.items()}
                })
            
            df_matchups = pd.DataFrame(matchup_data)
            matchup_file = output_path / f'matchups_week_{week if week else "all"}.csv'
            df_matchups.to_csv(matchup_file, index=False)
            logger.info(f"Exported matchup data to {matchup_file}")
        
        # Export player data
        player_snapshots = self.db.get_player_snapshots(week=week)
        if player_snapshots:
            player_data = []
            for snap in player_snapshots:
                stats = json.loads(snap['stats'])
                player_data.append({
                    'date': snap['snapshot_date'],
                    'week': snap['week_number'],
                    'team': snap['team_name'],
                    'player': snap['player_name'],
                    'position': snap['player_position'],
                    'player_type': self._classify_player(snap['player_position']),
                    **stats
                })
            
            df_players = pd.DataFrame(player_data)
            player_file = output_path / f'players_week_{week if week else "all"}.csv'
            df_players.to_csv(player_file, index=False)
            logger.info(f"Exported player data to {player_file}")
        
        return output_path
    
    # ------------------------------------------------------------------
    # Formatted printing
    # ------------------------------------------------------------------
    
    def print_daily_recap(self, week, current_date=None, previous_date=None):
        """Print a formatted daily recap to console."""
        recap = self.get_daily_recap(week, current_date, previous_date)
        
        if not recap:
            print("\nNo daily recap data available. You may need more than one day of data.")
            return
        
        print(f"\n{'='*70}")
        print(f"DAILY RECAP - WEEK {week}")
        print(f"{'='*70}\n")
        
        for matchup in recap:
            print(f"{matchup['team1_name']} vs {matchup['team2_name']}")
            print("-" * 70)
            
            # Team 1
            print(f"\n  {matchup['team1_name']} (team deltas):")
            for stat, val in matchup['team1_delta'].items():
                if isinstance(val, float) and val != 0:
                    print(f"    {stat}: {val:+.1f}")
            
            if matchup['team1_players']:
                print(f"\n  Contributors:")
                for player in matchup['team1_players']:
                    contribs = ', '.join(
                        f"{stat}: {val:+.1f}" for stat, val in player['delta'].items()
                        if isinstance(val, (int, float)) and val > 0
                    )
                    print(f"    {player['player_name']} — {contribs}")
            
            # Team 2
            print(f"\n  {matchup['team2_name']} (team deltas):")
            for stat, val in matchup['team2_delta'].items():
                if isinstance(val, float) and val != 0:
                    print(f"    {stat}: {val:+.1f}")
            
            if matchup['team2_players']:
                print(f"\n  Contributors:")
                for player in matchup['team2_players']:
                    contribs = ', '.join(
                        f"{stat}: {val:+.1f}" for stat, val in player['delta'].items()
                        if isinstance(val, (int, float)) and val > 0
                    )
                    print(f"    {player['player_name']} — {contribs}")
            
            print()
        
        print(f"{'='*70}\n")
    
    def print_weekly_recap(self, week, composite_method='zscore', composite_weights=None):
        """Print a formatted weekly recap to console."""
        recap = self.generate_weekly_recap(week, composite_method, composite_weights)
        
        print(f"\n{'='*70}")
        print(f"WEEKLY RECAP - WEEK {week}")
        print(f"{'='*70}\n")
        
        # --- Matchup Results ---
        print("MATCHUP RESULTS:")
        print("-" * 70)
        for matchup in recap['matchups']:
            print(f"\n  {matchup['team1']} vs {matchup['team2']}")
            print(f"    {matchup['team1']}: {matchup['team1_stats']}")
            print(f"    {matchup['team2']}: {matchup['team2_stats']}")
        
        # --- Composite Best/Worst ---
        print(f"\n{'='*70}")
        print(f"BEST & WORST (Composite: {recap['composite_method']})")
        print("-" * 70)
        
        composite = recap.get('composite_leaders', {})
        
        if composite.get('batters'):
            print("\n  Batting:")
            for p in composite['batters']['best']:
                print(f"    Best Batter:  {p['player_name']} ({p['team_name']}) — score: {p['composite_score']}")
            for p in composite['batters']['worst']:
                print(f"    Worst Batter: {p['player_name']} ({p['team_name']}) — score: {p['composite_score']}")
        
        if composite.get('pitchers'):
            print("\n  Pitching:")
            for p in composite['pitchers']['best']:
                print(f"    Best Pitcher:  {p['player_name']} ({p['team_name']}) — score: {p['composite_score']}")
            for p in composite['pitchers']['worst']:
                print(f"    Worst Pitcher: {p['player_name']} ({p['team_name']}) — score: {p['composite_score']}")
        
        # --- Per-Stat Leaders ---
        print(f"\n{'='*70}")
        print("PER-STAT LEADERS & TRAILERS")
        print("-" * 70)
        
        stat_leaders = recap.get('stat_leaders', {})
        
        batting_stats_present = [s for s in BATTING_STATS if s in stat_leaders]
        pitching_stats_present = [s for s in PITCHING_STATS if s in stat_leaders]
        
        if batting_stats_present:
            print("\n  Batting:")
            for stat in batting_stats_present:
                data = stat_leaders[stat]
                leader = data['leaders'][0]
                trailer = data['trailers'][0]
                print(f"    {stat} Leader:  {leader['player_name']} ({leader['team_name']}) — {leader['stat_value']}")
                print(f"    {stat} Trailer: {trailer['player_name']} ({trailer['team_name']}) — {trailer['stat_value']}")
        
        if pitching_stats_present:
            print("\n  Pitching:")
            for stat in pitching_stats_present:
                data = stat_leaders[stat]
                leader = data['leaders'][0]
                trailer = data['trailers'][0]
                print(f"    {stat} Leader:  {leader['player_name']} ({leader['team_name']}) — {leader['stat_value']}")
                print(f"    {stat} Trailer: {trailer['player_name']} ({trailer['team_name']}) — {trailer['stat_value']}")
        
        print(f"\n{'='*70}\n")


def main():
    """Run analyzer when called directly."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze fantasy baseball data')
    parser.add_argument('--week', type=int, help='Week number to analyze')
    parser.add_argument('--recap', action='store_true', help='Generate weekly recap')
    parser.add_argument('--daily', action='store_true', help='Generate daily recap')
    parser.add_argument('--export', action='store_true', help='Export to CSV')
    parser.add_argument(
        '--composite-method', type=str, default='zscore',
        choices=['zscore', 'percentile', 'minmax', 'weighted_points', 'yahoo_points'],
        help='Composite scoring method for weekly recap (default: zscore)'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    analyzer = FantasyAnalyzer()
    
    if args.recap:
        if not args.week:
            print("Error: --week required for recap")
            return 1
        analyzer.print_weekly_recap(args.week, composite_method=args.composite_method)
    
    if args.daily:
        if not args.week:
            print("Error: --week required for daily recap")
            return 1
        analyzer.print_daily_recap(args.week)
    
    if args.export:
        output = analyzer.export_to_csv(week=args.week)
        print(f"✓ Data exported to {output}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
