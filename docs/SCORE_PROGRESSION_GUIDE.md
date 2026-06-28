# Score Progression Chart - Visual Example

## What It Shows

The score progression chart displays how many stat categories each team is winning on each day of the week. It's a line chart that tells the story of the matchup as it unfolds.

## Example Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Matchup Score Progression                         │
│                                                                     │
│  10 ┤                                                               │
│     │                                                               │
│   9 ┤                                          ●───9 (Team A)       │
│     │                                     ●                         │
│   8 ┤                                ●                              │
│     │                           ●                                   │
│   7 ┤  ■───7 (Team B)      ●                                        │
│     │  │              ■                                             │
│   6 ┤  │         ■                                                  │
│     │  │    ■                                                       │
│   5 ┤  ■                                                            │
│     │                                                               │
│   4 ┤                                                               │
│     │                                                               │
│   3 ┤                                                               │
│     │                                                               │
│   2 ┤                                                               │
│     │                                                               │
│   1 ┤                                                               │
│     │                                                               │
│   0 ┴───────────────────────────────────────────────────────       │
│     Mon    Tue    Wed    Thu    Fri    Sat    Sun        Final    │
│                                                             ︙      │
│  Legend:                                                           │
│  ● Team A (Blue line)                                              │
│  ■ Team B (Red line)                                               │
│                                                                     │
│  ┌──────────────────────────────────────────┐                     │
│  │ Final: Team A 9 - 7 Team B               │                     │
│  │ Team A Wins!                             │                     │
│  └──────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

## What The Chart Tells You

### Day-by-Day Story

**Monday:**
- Team B leads 5-4 (winning in 5 categories)
- Close matchup from the start

**Tuesday - Wednesday:**
- Teams trade category wins
- Team B extends lead to 7-5
- Team A fighting back

**Thursday - Friday:**
- Team A mounts comeback
- Takes lead 8-7 on Friday
- Critical turning point in the week

**Saturday - Sunday (Final):**
- Team A extends lead
- Wins final matchup 9-7
- Team A wins 2 more categories than Team B

### Visual Elements

**Colors:**
- **Blue line (#1976D2)**: First team (typically home team)
- **Red line (#D32F2F)**: Second team (typically away team)
- Markers: Circles (●) and squares (■) for clear distinction

**Chart Features:**
- Clean grid background for easy reading
- Value labels on each point showing exact category count
- Final day marked with vertical dotted line
- Result box showing final score and winner

**Interactive Story Elements:**
The line pattern reveals:
- **Steep rises**: Team won multiple categories that day
- **Flat sections**: No change in categories won
- **Crossovers**: Momentum shifts between teams
- **Final gap**: How decisive the victory was

## Multiple Matchups

If your league has multiple matchups (e.g., 12 teams = 6 matchups), the weekly recap will generate **one progression chart per matchup**. Each matchup gets its own image file:

- `weekly_recap_w5_progression_1.png` - First matchup
- `weekly_recap_w5_progression_2.png` - Second matchup
- `weekly_recap_w5_progression_3.png` - Third matchup
- etc.

## Complete Weekly Recap Package

When you run `python generate_weekly_recap.py 5`, you'll get multiple images:

### 1. Score Progression Charts
**Files:** `weekly_recap_w5_progression_1.png`, `_2.png`, etc.

One line chart per matchup showing day-by-day category scores.

### 2. Player Highlights
**File:** `weekly_recap_w5_highlights.png`

Text-based summary showing:
- Best/worst batter and pitcher (with composite scores)
- Stat category leaders (HR, R, RBI, K, W, SV)

### 3. Final Matchup Results
**Files:** `weekly_recap_w5_matchup_1.png`, `_2.png`, etc.

Diverging bar charts showing final cumulative stats for each category with color coding for winners.

## Sharing in Group Chat

The multi-image format is perfect for group chats because you can:

1. **Post progression chart first** - Shows the dramatic narrative
2. **Follow with highlights** - Celebrates/roasts individual performances
3. **End with final results** - Shows the detailed category breakdown

Each image stands alone but tells part of the complete story.

## Technical Details

### Data Source
The chart uses `get_matchup_score_progression()` from `analyzer.py`, which:
- Pulls all daily snapshots for the week
- Counts categories won by each team per day
- Handles "lower is better" stats (ERA, WHIP) correctly
- Returns chronological progression data

### Rendering
- **Library**: matplotlib with seaborn styling
- **Size**: 10" x 6" (1000px x 600px at 100 DPI, 1500px x 900px at 150 DPI)
- **Format**: PNG at 150 DPI for crisp display on phones and computers
- **File size**: ~50-150 KB per chart

### When It's Most Useful

The score progression chart really shines when:
- **Close matchups**: Shows nail-biting back-and-forth
- **Comebacks**: Visualizes dramatic momentum swings
- **Blowouts**: Makes dominance visually obvious
- **Multi-day trends**: See if a team built an early lead or rallied late

## Example Scenarios

### The Comeback
```
Mon: 3-7 (down big)
Tue: 4-6 (gaining ground)
Wed: 5-5 (all tied up!)
Thu: 6-4 (take the lead)
Fri-Sun: 8-2 (dominate to finish)
```
The chart would show a dramatic upward slope for the comeback team.

### The Runaway
```
Mon: 8-2 (strong start)
Tue-Sun: 9-1 (maintain dominance)
```
Flat line at the top showing consistent dominance.

### The Seesaw Battle
```
Mon: 5-5
Tue: 6-4
Wed: 5-5
Thu: 4-6
Fri: 6-4
Sat: 5-5
Sun: 6-4 (final)
```
Lines crossing multiple times showing competitive back-and-forth.

---

**Generated automatically by:**
```bash
python generate_weekly_recap.py <week>
```

**Saved to:** `data/recaps/`
