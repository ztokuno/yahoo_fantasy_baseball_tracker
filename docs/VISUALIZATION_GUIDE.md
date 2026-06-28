# Visualization Sketches - Fantasy Baseball Recaps

This document describes what the daily and weekly recap images will look like when generated.

## Daily Recap Image

**File Location:** `data/recaps/daily_recap_w{week}_{YYYYMMDD}.png`

**Example:** `data/recaps/daily_recap_w5_20250415.png`

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│                  DAILY RECAP - WEEK 5                           │
│              Tuesday, April 15, 2025                            │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MATCHUP: The Sluggers vs The Pitchers                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Category Comparison (Daily Deltas)        │   │
│  │                                                        │   │
│  │  HR  ████████████ 3     vs    █████ 1.5              │   │
│  │       (green)                  (red)                  │   │
│  │                                                        │   │
│  │  R   ██████ 2               vs  ███████████ 4        │   │
│  │       (red)                      (green)              │   │
│  │                                                        │   │
│  │  RBI ████████ 3             vs  ████████ 3           │   │
│  │       (gray - tied)              (gray - tied)        │   │
│  │                                                        │   │
│  │  K   ██████████ 8           vs  ████████████ 10      │   │
│  │       (red)                      (green)              │   │
│  │                                                        │   │
│  │  (Diverging horizontal bars showing who won each     │   │
│  │   category today - green for winning, red for losing) │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                  TOP CONTRIBUTORS                       │   │
│  │                                                        │   │
│  │  [Photo]  Aaron Judge (The Sluggers)                  │   │
│  │  120x120  HR: +2, R: +1, RBI: +3                     │   │
│  │                                                        │   │
│  │  [Photo]  Shohei Ohtani (The Pitchers)               │   │
│  │  120x120  K: +10, W: +1                              │   │
│  │                                                        │   │
│  │  [Photo]  Mookie Betts (The Sluggers)                │   │
│  │  120x120  R: +2, SB: +1, 2B: +1                      │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  CLUTCH MOMENT:                                                 │
│  Aaron Judge hit 2 home runs in the HR category where          │
│  The Sluggers now lead by only 0.5 HR - a nail-biter!         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Visual Elements

1. **Title Banner** (top)
   - Week number and date
   - Clean sans-serif font (Arial/Helvetica)
   - White background with subtle gray border

2. **Matchup Section** (middle)
   - Team names displayed prominently
   - Diverging horizontal bar chart showing category-by-category comparison
   - Color coding:
     - Green (#2E7D32) = winning the category today
     - Red (#C62828) = losing the category today
     - Gray (#757575) = tied
   - Bars extend left and right from a center axis (like political polls)
   - Shows daily deltas, not cumulative totals

3. **Player Contribution Section**
   - Top 3 contributors from the day (across both teams)
   - Each player gets:
     - 120x120px headshot (downloaded from MLB Stats API)
     - Name and team
     - Stats they contributed (only positive deltas shown)
   - Laid out horizontally or in a grid

4. **Highlight Callout** (bottom)
   - 1-2 sentences identifying the most interesting moment
   - Examples:
     - "Clutch performance in a close category"
     - "Dominant performance in multiple categories"
     - "Comeback contribution after being behind"

### Dimensions
- Total width: ~1200px (suitable for social media sharing)
- Total height: Variable (depends on number of stats, ~800-1000px typical)

---

## Weekly Recap Image

**File Location:** `data/recaps/weekly_recap_w{week}.png`

**Example:** `data/recaps/weekly_recap_w5.png`

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│                      WEEKLY RECAP - WEEK 5                      │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         PLAYER OF THE WEEK (Yahoo Points)              │   │
│  │                                                        │   │
│  │  [Photo]  BEST BATTER:                    [Photo]     │   │
│  │  150x150  Aaron Judge (The Sluggers)      150x150     │   │
│  │           Score: 82.3 pts                             │   │
│  │                                                        │   │
│  │           BEST PITCHER:                               │   │
│  │           Gerrit Cole (The Pitchers)                  │   │
│  │           Score: 74.1 pts                             │   │
│  │                                                        │   │
│  │  [Photo]  WORST BATTER:                   [Photo]     │   │
│  │  150x150  Player X (Team)                 150x150     │   │
│  │           Score: -5.2 pts                             │   │
│  │                                                        │   │
│  │           WORST PITCHER:                              │   │
│  │           Player Y (Team)                             │   │
│  │           Score: -12.8 pts                            │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              CATEGORY LEADERS                          │   │
│  │                                                        │   │
│  │  HR:  Aaron Judge (The Sluggers) - 7                  │   │
│  │  R:   Mookie Betts (The Sluggers) - 12                │   │
│  │  RBI: Pete Alonso (Team 3) - 15                       │   │
│  │  K:   Gerrit Cole (The Pitchers) - 22                 │   │
│  │  W:   Sandy Alcantara (Team 4) - 3                    │   │
│  │  SV:  Josh Hader (Team 2) - 4                         │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │          FINAL MATCHUP RESULTS                         │   │
│  │                                                        │   │
│  │  The Sluggers vs The Pitchers                         │   │
│  │                                                        │   │
│  │  HR  ████████████████ 14   vs   █████████ 9          │   │
│  │  R   ████████████████ 25   vs   ███████████ 18       │   │
│  │  RBI ███████████████ 22    vs   ████████████ 20      │   │
│  │  SB  ████ 3               vs   ██████ 5              │   │
│  │  AVG █████████ .285        vs   ██████████ .298      │   │
│  │  W   ████████ 4            vs   ███████ 3            │   │
│  │  K   ████████████████ 45   vs   ███████████ 38       │   │
│  │  SV  ██████ 3              vs   ████ 2               │   │
│  │  ERA ████████ 3.42         vs   ███████ 2.98         │   │
│  │  WHIP ██████ 1.15          vs   ████████ 1.28        │   │
│  │                                                        │   │
│  │  (Cumulative totals for the week, showing who won    │   │
│  │   each category - green for winner, red for loser)    │   │
│  │                                                        │   │
│  │  Final Score: The Pitchers win 6-4                    │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Visual Elements

1. **Title Banner** (top)
   - Week number
   - Same clean styling as daily recap

2. **Player of the Week Section** (top)
   - Larger headshots (150x150px) for the 4 featured players
   - Best/worst for batters and pitchers separately
   - Composite scores displayed prominently
   - Uses whichever composite method you specified (yahoo_points by default)

3. **Category Leaders Section** (middle)
   - Simple list showing the league leader in each major stat
   - Player name, team, and stat value
   - Covers both batting and pitching categories

4. **Matchup Results Section** (bottom)
   - Same diverging bar chart style as daily recaps
   - But shows full week cumulative totals instead of daily deltas
   - Color coded by who won each category
   - Final score tally at the bottom (X categories to Y categories)
   - If multiple matchups, shows all of them stacked vertically

### Dimensions
- Total width: ~1200px
- Total height: Variable (~1200-1600px typical, depending on content)

---

## Style Details

### Colors
- **Winning**: #2E7D32 (Green) - vibrant but not too bright
- **Losing**: #C62828 (Red) - strong but readable
- **Neutral/Tied**: #757575 (Gray)
- **Background**: White (#FFFFFF) with light gray borders (#EEEEEE)
- **Text**: Dark gray (#212121) for readability

### Fonts
- **Headings**: Arial Bold, 18-24pt
- **Body text**: Arial Regular, 12-14pt
- **Stats**: Arial Bold, 14pt

### Chart Style
- Clean, minimal gridlines (seaborn "whitegrid" style)
- Horizontal bars for easy category-by-category comparison
- All bars same thickness for visual consistency
- Subtle shadows/borders for depth without clutter

### Player Photos
- Circular crops with subtle border
- Fallback to gray placeholder silhouette if photo not available
- Consistent sizing within each section

---

## Technical Implementation Notes

The visualization generation happens in `src/visualize.py`:

1. **Data Collection**: Pulls from analyzer.py methods
   - `get_daily_recap()` for daily images
   - `generate_weekly_recap()` for weekly images

2. **Chart Generation**: Uses matplotlib + seaborn
   - `_create_category_comparison_chart()` for the bar charts
   - `_create_player_contribution_chart()` for player spotlights

3. **Highlight Detection**: `identify_daily_highlights()`
   - Finds clutch performances (close categories + big contribution)
   - Identifies dominant performances
   - Detects comeback moments

4. **Photo Management**: `src/photos.py`
   - Downloads from MLB Stats API: `https://img.mlbstatic.com/mlb-photos/...`
   - Fuzzy name matching to handle differences between Yahoo and MLB names
   - Local caching in `data/player_photos/`
   - Mapping cache in `data/player_photos/player_mappings.json`

5. **Image Composition**: PIL (Pillow)
   - `_create_composite_image()` stitches everything together
   - Adds text overlays, borders, spacing
   - Exports as high-quality PNG

6. **Automatic Generation**:
   - Daily recaps: Auto-generated by `run_daily_update.py`
   - Weekly recaps: Run `python generate_weekly_recap.py <week>`

---

## Usage

### Daily (automatic)
```bash
python run_daily_update.py
```
This now:
1. Collects data from Yahoo API
2. Saves to database
3. Generates daily recap image → `data/recaps/daily_recap_w5_20250415.png`

### Weekly (on-demand)
```bash
python generate_weekly_recap.py 5
```
Or with a specific composite method:
```bash
python generate_weekly_recap.py 5 --composite-method zscore
```

### Output Location
All images saved to: `data/recaps/`

You can then:
- Share on social media
- Email to league members
- Post in your league's chat/Slack/Discord
- Keep as a personal archive

---

## Future Enhancement Ideas

- **Multi-day trends**: Line charts showing stat progression through the week
- **Head-to-head player comparisons**: Side-by-side stat cards
- **Animated GIFs**: Show daily progression as an animation
- **League-wide leaderboards**: Not just matchup-specific
- **Custom themes**: Team colors, logos, etc.
- **PDF reports**: Multi-page detailed breakdowns with more stats
