"""
Visualization Module

Generates visual recaps of daily and weekly fantasy baseball matchups,
including charts, player headshots, and highlight callouts.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import logging
import platform
from datetime import date, timedelta

from src.analyzer import FantasyAnalyzer, BATTING_STATS, PITCHING_STATS
from src.photos import PlayerPhotoManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cross-platform font resolution
# ---------------------------------------------------------------------------
# Real Helvetica is a commercial typeface (Monotype) - we don't bundle a copy
# of it in this repo. Instead, we bundle TeX Gyre Heros: an open-licensed
# (GUST Font License) font based on URW++'s Nimbus Sans, which is itself
# drawn directly from Helvetica's actual letterforms - not just metrically
# compatible the way Arial/Liberation Sans are. This is the closest open
# alternative to genuine Helvetica available, and bundling it means every
# visualization looks identical regardless of which OS generates it (no
# dependency on what's installed locally).
#
# Source: https://pypi.org/project/rinoh-typeface-texgyreheros/
# License: GUST Font License (free to use/modify/redistribute) - see
#          assets/fonts/GUST-FONT-LICENSE.txt
#
# Priority order:
#   1. Bundled TeX Gyre Heros (assets/fonts/) - identical on every OS
#   2. OS-native fallback (real Helvetica Neue on Mac, Arial on Windows,
#      Liberation/DejaVu on Linux) - used only if the bundled font is
#      somehow missing
# ---------------------------------------------------------------------------

_FONTS_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
_BUNDLED_FONT = (
    str(_FONTS_DIR / 'TeXGyreHeros-Regular.ttf'),
    str(_FONTS_DIR / 'TeXGyreHeros-Bold.ttf'),
)

# (regular_path, bold_path) OS-native fallback candidates, in priority order
_FONT_CANDIDATES = {
    'Darwin': [  # macOS
        ('/System/Library/Fonts/HelveticaNeue.ttc', '/System/Library/Fonts/HelveticaNeue.ttc'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
        ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
    ],
    'Windows': [
        (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
    ],
    'Linux': [
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ],
}


def get_font_paths():
    """
    Find the best available (regular, bold) font file paths.
    
    Checks the bundled TeX Gyre Heros font first (assets/fonts/) - this is
    the same on every OS, so visualizations look identical whether generated
    on Windows, Mac, or Linux. Only falls back to OS-native system fonts
    (real Helvetica Neue on Mac, Arial on Windows, Liberation/DejaVu on
    Linux) if the bundled font is missing for some reason.
    
    Returns:
        Tuple of (regular_path, bold_path) as strings, or (None, None)
    """
    bundled_regular, bundled_bold = _BUNDLED_FONT
    if Path(bundled_regular).exists() and Path(bundled_bold).exists():
        return bundled_regular, bundled_bold
    
    logger.warning(
        f"Bundled font not found at {_FONTS_DIR} - falling back to OS-native fonts"
    )
    
    system = platform.system()
    fallback_order = [system] + [s for s in _FONT_CANDIDATES if s != system]
    
    for os_name in fallback_order:
        for regular, bold in _FONT_CANDIDATES.get(os_name, []):
            if Path(regular).exists() and Path(bold).exists():
                return regular, bold
    
    logger.warning(
        "No bundled font and no system Helvetica/Arial/Liberation/DejaVu "
        "found - falling back to PIL's default bitmap font"
    )
    return None, None


def load_font(size, bold=False):
    """
    Load a font at the given size, using the best available cross-platform
    Helvetica-equivalent. Falls back to PIL's default font if none found.
    
    Args:
        size: Font point size
        bold: Whether to load the bold variant
        
    Returns:
        PIL ImageFont object
    """
    regular_path, bold_path = get_font_paths()
    path = bold_path if bold else regular_path
    
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception as e:
            logger.warning(f"Found font at {path} but could not load it: {e}")
    
    return ImageFont.load_default()

# Set style
sns.set_theme(style="whitegrid")

# Register the bundled TeX Gyre Heros font with matplotlib so chart text
# matches the PIL-rendered images exactly, regardless of OS. Falls back
# silently to the OS-native list (matplotlib will search installed system
# fonts, then its own bundled DejaVu Sans) if the bundled file is missing.
try:
    import matplotlib.font_manager as fm
    _bundled_regular, _bundled_bold = _BUNDLED_FONT
    if Path(_bundled_regular).exists():
        fm.fontManager.addfont(_bundled_regular)
    if Path(_bundled_bold).exists():
        fm.fontManager.addfont(_bundled_bold)
except Exception as e:
    logger.warning(f"Could not register bundled font with matplotlib: {e}")

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['TeX Gyre Heros', 'Helvetica', 'Arial', 'DejaVu Sans']


class RecapVisualizer:
    """
    Generate visual recaps for fantasy baseball matchups.
    
    Creates shareable PNG images with:
    - Matchup stat comparisons
    - Player headshots
    - Highlight callouts for clutch performances
    - Clean, mobile-friendly layouts
    """
    
    def __init__(self, db_path='data/fantasy_baseball.db'):
        """Initialize visualizer with analyzer and photo manager."""
        self.analyzer = FantasyAnalyzer(db_path=db_path)
        self.photo_manager = PlayerPhotoManager()
        self.output_dir = Path('data/recaps')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------------------------
    # Chart generation helpers
    # ----------------------------------------------------------------
    
    def _create_category_comparison_chart(self, team1_stats, team2_stats,
                                         team1_name, team2_name,
                                         categories=None):
        """
        Create a horizontal bar chart comparing team stats by category.
        
        Returns a matplotlib figure.
        """
        if categories is None:
            # Use all stats present in both teams
            categories = sorted(set(team1_stats.keys()) & set(team2_stats.keys()))
        
        # Filter to only categories both teams have
        categories = [c for c in categories if c in team1_stats and c in team2_stats]
        
        if not categories:
            return None
        
        fig, ax = plt.subplots(figsize=(10, max(6, len(categories) * 0.4)))
        
        y_pos = np.arange(len(categories))
        
        # Extract values
        team1_vals = [float(team1_stats.get(cat, 0)) for cat in categories]
        team2_vals = [float(team2_stats.get(cat, 0)) for cat in categories]
        
        # Determine bar colors based on who's winning each category
        team1_colors = []
        team2_colors = []
        
        for t1, t2 in zip(team1_vals, team2_vals):
            if t1 > t2:
                team1_colors.append('#2E7D32')  # Green for winning
                team2_colors.append('#C62828')  # Red for losing
            elif t2 > t1:
                team1_colors.append('#C62828')
                team2_colors.append('#2E7D32')
            else:
                team1_colors.append('#757575')  # Gray for tied
                team2_colors.append('#757575')
        
        # Create diverging bar chart
        ax.barh(y_pos, [-v for v in team1_vals], align='center',
               color=team1_colors, alpha=0.8, label=team1_name)
        ax.barh(y_pos, team2_vals, align='center',
               color=team2_colors, alpha=0.8, label=team2_name)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories)
        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_xlabel('Stats')
        ax.legend(loc='best')
        ax.set_title(f'{team1_name} vs {team2_name}', fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for i, (t1, t2) in enumerate(zip(team1_vals, team2_vals)):
            ax.text(-t1/2, i, f'{t1:.1f}', ha='center', va='center',
                   color='black', fontweight='bold', fontsize=9)
            ax.text(t2/2, i, f'{t2:.1f}', ha='center', va='center',
                   color='black', fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        return fig
    
    def _create_player_contribution_chart(self, players, stat_category='HR',
                                         title='Top Contributors'):
        """
        Create a bar chart showing top player contributions in a stat category.
        
        Returns a matplotlib figure.
        """
        if not players:
            return None
        
        # Sort by the stat value
        sorted_players = sorted(players, key=lambda p: p.get('stat_value', 0), reverse=True)
        top_players = sorted_players[:5]  # Top 5
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        names = [p['player_name'] for p in top_players]
        values = [p['stat_value'] for p in top_players]
        colors = sns.color_palette("RdYlGn_r", len(top_players))
        
        bars = ax.barh(names, values, color=colors, alpha=0.8)
        ax.set_xlabel(stat_category)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.invert_yaxis()
        
        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2,
                   f' {val:.1f}', ha='left', va='center', fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def _create_score_progression_chart(self, team1_name, team2_name,
                                       dates, team1_scores, team2_scores):
        """
        Create a line chart showing day-by-day matchup score progression.
        
        Shows how many stat categories each team is winning on each day.
        
        Args:
            team1_name, team2_name: Team names
            dates: List of date strings
            team1_scores: List of category counts for team1
            team2_scores: List of category counts for team2
            
        Returns:
            matplotlib figure
        """
        if not dates or not team1_scores or not team2_scores:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Convert dates to day labels (Mon, Tue, etc.)
        from datetime import datetime
        day_labels = []
        for date_str in dates:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                day_labels.append(dt.strftime('%a'))  # Mon, Tue, Wed, etc.
            except:
                day_labels.append(date_str[-2:])  # Last 2 chars as fallback
        
        x = range(len(dates))
        
        # Plot lines
        line1 = ax.plot(x, team1_scores, marker='o', linewidth=2.5, 
                       markersize=8, label=team1_name, color='#1976D2', alpha=0.9)
        line2 = ax.plot(x, team2_scores, marker='s', linewidth=2.5,
                       markersize=8, label=team2_name, color='#D32F2F', alpha=0.9)
        
        # Styling
        ax.set_xticks(x)
        ax.set_xticklabels(day_labels)
        ax.set_xlabel('Day of Week', fontsize=12, fontweight='bold')
        ax.set_ylabel('Categories Won', fontsize=12, fontweight='bold')
        ax.set_title('Matchup Score Progression', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Set y-axis to integers only
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # Add value labels on points (above for higher line, below for lower line)
        for i, (score1, score2) in enumerate(zip(team1_scores, team2_scores)):
            # Determine which team is on top at this point
            if score1 > score2:
                # Team 1 is winning - label above
                ax.text(i, score1, str(score1), ha='center', va='bottom',
                       fontweight='bold', fontsize=9, color='#1976D2')
                # Team 2 is losing - label below
                ax.text(i, score2, str(score2), ha='center', va='top',
                       fontweight='bold', fontsize=9, color='#D32F2F')
            elif score2 > score1:
                # Team 2 is winning - label above
                ax.text(i, score2, str(score2), ha='center', va='bottom',
                       fontweight='bold', fontsize=9, color='#D32F2F')
                # Team 1 is losing - label below
                ax.text(i, score1, str(score1), ha='center', va='top',
                       fontweight='bold', fontsize=9, color='#1976D2')
            else:
                # Tied - both above
                ax.text(i, score1 + 0.1, str(score1), ha='center', va='bottom',
                       fontweight='bold', fontsize=9, color='#1976D2')
                ax.text(i, score2 + 0.1, str(score2), ha='center', va='bottom',
                       fontweight='bold', fontsize=9, color='#D32F2F')
        
        # Highlight the final day
        if len(x) > 0:
            ax.axvline(x=x[-1], color='gray', linestyle=':', alpha=0.5, linewidth=2)
            ax.text(x[-1], ax.get_ylim()[1] * 0.95, 'Final', 
                   ha='center', fontsize=9, style='italic', color='gray')
        
        # Add final score annotation
        if team1_scores and team2_scores:
            final_t1 = team1_scores[-1]
            final_t2 = team2_scores[-1]
            winner = team1_name if final_t1 > final_t2 else team2_name
            
            # Add text box with final result
            result_text = f"Final: {team1_name} {final_t1} - {final_t2} {team2_name}"
            if final_t1 != final_t2:
                result_text += f"\n{winner} Wins!"
            else:
                result_text += "\nTied!"
            
            ax.text(0.02, 0.98, result_text,
                   transform=ax.transAxes,
                   fontsize=10,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        return fig
    
    # ----------------------------------------------------------------
    # Highlight/moment detection
    # ----------------------------------------------------------------
    
    def identify_daily_highlights(self, week, current_date=None, previous_date=None):
        """
        Identify key moments/performances from a single day.
        
        Returns a dict with:
            - clutch_players: Players who contributed heavily in close categories
            - blowout_stats: Categories with huge margins
            - top_performers: Highest-scoring players of the day
        """
        if current_date is None:
            current_date = date.today()
        if previous_date is None:
            previous_date = current_date - timedelta(days=1)
        
        # Get daily recap data
        recap = self.analyzer.get_daily_recap(week, current_date, previous_date)
        
        if not recap:
            return {}
        
        highlights = {
            'clutch_players': [],
            'blowout_stats': [],
            'top_performers': []
        }
        
        for matchup in recap:
            # Identify blowouts - categories with >20% margin
            for stat in matchup['team1_delta'].keys():
                t1_val = matchup['team1_delta'].get(stat, 0)
                t2_val = matchup['team2_delta'].get(stat, 0)
                
                if isinstance(t1_val, (int, float)) and isinstance(t2_val, (int, float)):
                    total = abs(t1_val) + abs(t2_val)
                    if total > 0:
                        margin = abs(t1_val - t2_val) / total
                        if margin > 0.6:  # 60%+ of total production
                            highlights['blowout_stats'].append({
                                'stat': stat,
                                'team1': matchup['team1_name'],
                                'team1_val': t1_val,
                                'team2': matchup['team2_name'],
                                'team2_val': t2_val
                            })
            
            # Find top individual contributors
            all_players = matchup['team1_players'] + matchup['team2_players']
            for player in all_players:
                # Calculate a simple "impact score" - sum of positive deltas
                impact = sum(v for v in player['delta'].values()
                           if isinstance(v, (int, float)) and v > 0)
                if impact > 0:
                    highlights['top_performers'].append({
                        'player_name': player['player_name'],
                        'team': matchup.get('team1_name') if player in matchup['team1_players']
                                else matchup.get('team2_name'),
                        'impact_score': impact,
                        'stats': player['delta']
                    })
        
        # Sort top performers
        highlights['top_performers'].sort(key=lambda p: p['impact_score'], reverse=True)
        highlights['top_performers'] = highlights['top_performers'][:5]
        
        return highlights
    
    # ----------------------------------------------------------------
    # Image composition
    # ----------------------------------------------------------------
    
    def _add_player_headshot(self, img, player_name, position, size=(120, 120)):
        """
        Add a player headshot to an image.
        
        Args:
            img: PIL Image to modify
            player_name: Name of player
            position: (x, y) tuple for placement
            size: (width, height) tuple for headshot size
            
        Returns:
            Modified PIL Image
        """
        photo_path = self.photo_manager.get_player_photo(player_name)
        
        if photo_path and photo_path.exists():
            headshot = Image.open(photo_path)
            headshot = headshot.resize(size, Image.Resampling.LANCZOS)
            
            # Create circular mask
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            
            # Paste with mask
            img.paste(headshot, position, mask)
        
        return img
    
    def _create_composite_image(self, charts, headshots=None, highlights=None,
                               title="Fantasy Baseball Recap", width=1200):
        """
        Composite multiple charts and headshots into a single image.
        
        Args:
            charts: List of matplotlib figures
            headshots: List of (player_name, position) tuples
            highlights: List of text highlights to add
            title: Title for the recap
            width: Target width in pixels
            
        Returns:
            PIL Image
        """
        # Calculate total height needed
        margin = 40
        title_height = 100
        chart_heights = []
        
        for fig in charts:
            # Save chart to temporary bytes
            from io import BytesIO
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            chart_img = Image.open(buf)
            chart_heights.append(chart_img.size[1])
            buf.close()
        
        total_height = title_height + sum(chart_heights) + margin * (len(charts) + 2)
        
        if highlights:
            total_height += 30 * len(highlights) + margin
        
        # Create canvas
        canvas = Image.new('RGB', (width, total_height), color='#F5F5F5')
        draw = ImageDraw.Draw(canvas)
        
        # Load fonts (cross-platform: Helvetica/Arial/Liberation/DejaVu)
        title_font = load_font(40, bold=True)
        text_font = load_font(20, bold=False)
        
        # Draw title
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) / 2, margin), title,
                 fill='#1A237E', font=title_font)
        
        # Add charts
        y_offset = title_height + margin
        for i, fig in enumerate(charts):
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            chart_img = Image.open(buf)
            
            # Resize to fit width
            aspect = chart_img.size[1] / chart_img.size[0]
            new_width = width - 2 * margin
            new_height = int(new_width * aspect)
            chart_img = chart_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            canvas.paste(chart_img, (margin, y_offset))
            y_offset += new_height + margin
            buf.close()
            plt.close(fig)
        
        # Add highlights text
        if highlights:
            y_offset += margin
            draw.text((margin, y_offset), "Key Highlights:",
                     fill='#1A237E', font=text_font)
            y_offset += 35
            
            for highlight in highlights:
                draw.text((margin + 20, y_offset), f"• {highlight}",
                         fill='#212121', font=text_font)
                y_offset += 30
        
        return canvas
    
    def _create_player_highlights_image(self, composite_leaders, week, composite_method):
        """
        Create a player highlights image with headshots for weekly recap.
        
        Shows best/worst batter and pitcher with their headshots and composite scores.
        
        Args:
            composite_leaders: Dict with 'batters' and 'pitchers' sections
            week: Week number
            composite_method: Name of composite scoring method used
            
        Returns:
            PIL Image
        """
        # Create image with white background
        img_width = 1000
        img_height = 700
        img = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Load fonts (cross-platform: Helvetica/Arial/Liberation/DejaVu)
        title_font = load_font(28, bold=True)
        heading_font = load_font(20, bold=True)
        text_font = load_font(16, bold=False)
        score_font = load_font(18, bold=True)
        
        # Title
        y_pos = 30
        title_text = f"Week {week} - Player of the Week ({composite_method})"
        draw.text((img_width//2, y_pos), title_text, font=title_font, fill='black', anchor='mt')
        
        # Draw separator line
        y_pos += 50
        draw.line([(50, y_pos), (img_width-50, y_pos)], fill='gray', width=2)
        
        y_pos += 40
        
        # BATTING SECTION
        if composite_leaders.get('batters'):
            draw.text((img_width//2, y_pos), "BATTING", font=heading_font, fill='#1976D2', anchor='mt')
            y_pos += 40
            
            # Best Batter (left side)
            best_batter = composite_leaders['batters']['best'][0]
            self._draw_player_card(img, draw, best_batter, 100, y_pos, "BEST", text_font, score_font)
            
            # Worst Batter (right side)
            worst_batter = composite_leaders['batters']['worst'][0]
            self._draw_player_card(img, draw, worst_batter, 550, y_pos, "WORST", text_font, score_font)
            
            y_pos += 200
        
        # PITCHING SECTION
        if composite_leaders.get('pitchers'):
            draw.text((img_width//2, y_pos), "PITCHING", font=heading_font, fill='#D32F2F', anchor='mt')
            y_pos += 40
            
            # Best Pitcher (left side)
            best_pitcher = composite_leaders['pitchers']['best'][0]
            self._draw_player_card(img, draw, best_pitcher, 100, y_pos, "BEST", text_font, score_font)
            
            # Worst Pitcher (right side)
            worst_pitcher = composite_leaders['pitchers']['worst'][0]
            self._draw_player_card(img, draw, worst_pitcher, 550, y_pos, "WORST", text_font, score_font)
        
        return img
    
    def _draw_player_card(self, img, draw, player, x, y, label, text_font, score_font):
        """
        Draw a player card with headshot, name, team, and score.
        
        Args:
            img: PIL Image to draw on
            draw: ImageDraw object
            player: Player dict with player_name, team_name, composite_score
            x, y: Top-left position
            label: "BEST" or "WORST"
            text_font: Font for text
            score_font: Font for score
        """
        # Get player photo
        photo_path = self.photo_manager.get_player_photo(player['player_name'])
        
        headshot_size = 120
        
        # Draw headshot
        if photo_path and photo_path.exists():
            try:
                headshot = Image.open(photo_path)
                headshot = headshot.resize((headshot_size, headshot_size), Image.Resampling.LANCZOS)
                
                # Create circular mask
                mask = Image.new('L', (headshot_size, headshot_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, headshot_size, headshot_size), fill=255)
                
                # Paste with mask
                img.paste(headshot, (x, y), mask)
            except Exception as e:
                logger.warning(f"Could not load headshot for {player['player_name']}: {e}")
                # Draw placeholder circle
                draw.ellipse((x, y, x + headshot_size, y + headshot_size), 
                           fill='lightgray', outline='gray', width=2)
        else:
            # Draw placeholder circle
            draw.ellipse((x, y, x + headshot_size, y + headshot_size), 
                       fill='lightgray', outline='gray', width=2)
        
        # Draw player info to the right of headshot
        text_x = x + headshot_size + 20
        text_y = y + 10
        
        # Label (BEST/WORST)
        label_color = '#2E7D32' if label == "BEST" else '#C62828'
        draw.text((text_x, text_y), label, font=score_font, fill=label_color)
        text_y += 30
        
        # Player name
        draw.text((text_x, text_y), player['player_name'], font=text_font, fill='black')
        text_y += 25
        
        # Team name
        draw.text((text_x, text_y), f"({player['team_name']})", font=text_font, fill='gray')
        text_y += 30
        
        # Score
        score_text = f"Score: {player['composite_score']:.1f}"
        draw.text((text_x, text_y), score_text, font=score_font, fill='black')
    
    # ----------------------------------------------------------------
    # Main recap generation methods
    # ----------------------------------------------------------------
    
    def generate_daily_recap_image(self, week, current_date=None, previous_date=None):
        """
        Generate a visual daily recap image.
        
        Args:
            week: Week number
            current_date: Date of recap (defaults to today)
            previous_date: Previous date for comparison (defaults to yesterday)
            
        Returns:
            Path to the saved PNG file
        """
        if current_date is None:
            current_date = date.today()
        if previous_date is None:
            previous_date = current_date - timedelta(days=1)
        
        logger.info(f"Generating daily recap for week {week}, {current_date}")
        
        # Get recap data
        recap_data = self.analyzer.get_daily_recap(week, current_date, previous_date)
        
        if not recap_data:
            logger.warning("No daily recap data available")
            return None
        
        # Identify highlights
        highlights = self.identify_daily_highlights(week, current_date, previous_date)
        
        # Generate charts for each matchup
        charts = []
        highlight_texts = []
        
        for matchup in recap_data:
            # Create category comparison chart
            fig = self._create_category_comparison_chart(
                matchup['team1_delta'],
                matchup['team2_delta'],
                matchup['team1_name'],
                matchup['team2_name']
            )
            if fig:
                charts.append(fig)
        
        # Add highlight text
        for performer in highlights['top_performers'][:3]:
            stats_str = ', '.join([f"{k}: +{v:.1f}" for k, v in performer['stats'].items()
                                  if isinstance(v, (int, float)) and v > 0])
            highlight_texts.append(
                f"{performer['player_name']} ({performer['team']}): {stats_str}"
            )
        
        # Composite into single image
        title = f"Daily Recap - Week {week}, {current_date.strftime('%A, %b %d')}"
        composite = self._create_composite_image(charts, highlights=highlight_texts, title=title)
        
        # Save
        filename = f"daily_recap_w{week}_{current_date.strftime('%Y%m%d')}.png"
        save_path = self.output_dir / filename
        composite.save(save_path, quality=95)
        
        logger.info(f"Daily recap saved to {save_path}")
        return save_path
    
    def generate_weekly_recap_image(self, week, composite_method='yahoo_points'):
        """
        Generate visual weekly recap images (multiple files).
        
        Creates separate images for:
        1. Score progression chart (line chart showing day-by-day scores)
        2. Player of the week highlights
        3. Final matchup results
        
        Args:
            week: Week number
            composite_method: Scoring method for best/worst players
            
        Returns:
            List of Paths to the saved PNG files
        """
        logger.info(f"Generating weekly recap images for week {week}")
        
        saved_files = []
        
        # Get weekly data
        recap = self.analyzer.generate_weekly_recap(week, composite_method=composite_method)
        stat_leaders = recap['stat_leaders']
        composite_leaders = recap['composite_leaders']
        
        # Get score progression data
        score_progressions = self.analyzer.get_matchup_score_progression(week)
        
        # ----------------------------------------------------------------
        # Image 1: Score Progression Chart(s)
        # ----------------------------------------------------------------
        for i, progression in enumerate(score_progressions):
            fig = self._create_score_progression_chart(
                progression['team1_name'],
                progression['team2_name'],
                progression['dates'],
                progression['team1_scores'],
                progression['team2_scores']
            )
            
            if fig:
                filename = f"weekly_recap_w{week}_progression_{i+1}.png"
                save_path = self.output_dir / filename
                fig.savefig(save_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
                saved_files.append(save_path)
                logger.info(f"Score progression saved to {save_path}")
        
        # ----------------------------------------------------------------
        # Image 2: Player of the Week Highlights (with headshots)
        # ----------------------------------------------------------------
        if composite_leaders.get('batters') or composite_leaders.get('pitchers'):
            highlights_img = self._create_player_highlights_image(
                composite_leaders, 
                week,
                composite_method
            )
            if highlights_img:
                filename = f"weekly_recap_w{week}_highlights.png"
                save_path = self.output_dir / filename
                highlights_img.save(save_path, quality=95)
                saved_files.append(save_path)
                logger.info(f"Player highlights saved to {save_path}")
        
        # ----------------------------------------------------------------
        # Image 3: Final Matchup Results
        # ----------------------------------------------------------------
        matchup_charts = []
        for matchup in recap['matchups']:
            fig = self._create_category_comparison_chart(
                matchup['team1_stats'],
                matchup['team2_stats'],
                matchup['team1'],
                matchup['team2']
            )
            if fig:
                matchup_charts.append(fig)
        
        if matchup_charts:
            # Save each matchup result as a separate image
            for i, fig in enumerate(matchup_charts):
                filename = f"weekly_recap_w{week}_matchup_{i+1}.png"
                save_path = self.output_dir / filename
                fig.savefig(save_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
                saved_files.append(save_path)
                logger.info(f"Matchup result saved to {save_path}")
        
        logger.info(f"Weekly recap complete: {len(saved_files)} images generated")
        return saved_files


def main():
    """Test visualization generation when run directly."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate fantasy baseball visual recaps')
    parser.add_argument('--week', type=int, required=True, help='Week number')
    parser.add_argument('--daily', action='store_true', help='Generate daily recap')
    parser.add_argument('--weekly', action='store_true', help='Generate weekly recap')
    parser.add_argument('--composite-method', type=str, default='yahoo_points',
                       help='Composite scoring method for weekly recap')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    visualizer = RecapVisualizer()
    
    if args.daily:
        img_path = visualizer.generate_daily_recap_image(args.week)
        if img_path:
            print(f"\n✓ Daily recap generated: {img_path}")
        else:
            print("\n✗ Failed to generate daily recap")
    
    if args.weekly:
        img_paths = visualizer.generate_weekly_recap_image(args.week, args.composite_method)
        if img_paths:
            print(f"\n✓ Weekly recap generated ({len(img_paths)} images):")
            for path in img_paths:
                print(f"  - {path}")
        else:
            print("\n✗ Failed to generate weekly recap")


if __name__ == "__main__":
    main()
