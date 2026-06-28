# Yahoo Fantasy Baseball Stat Tracker

A comprehensive stat tracking and recap generator for Yahoo Fantasy Baseball leagues.

## Features

- **Daily Matchup Snapshots**: Capture weekly matchup stats at end of each day
- **Player-Level Stats**: Track individual player performance daily (27+ stat categories)
- **Delta Calculations**: See what changed since yesterday with player attribution
- **Weekly Recaps**: Generate comprehensive weekly summaries with composite scoring
- **Visual Recaps**: Automated generation of shareable recap images with charts and player photos
- **Clutch Performance Detection**: Identify key moments and clutch players
- **Multiple Composite Scoring Methods**: z-score, percentile, min-max, weighted points, Yahoo points
- **Data Storage**: SQLite database for historical tracking
- **CSV Export**: Export data for R/tidyverse analysis

## Project Structure

```
yahoo_fantasy_tracker/
├── config/
│   ├── credentials.json      # Yahoo API credentials (DO NOT COMMIT)
│   └── config.yaml           # Project configuration
├── data/
│   ├── fantasy_baseball.db   # SQLite database
│   ├── exports/              # CSV exports for R analysis
│   ├── player_photos/        # Cached MLB player headshots
│   └── recaps/               # Generated visual recap images
├── logs/
│   └── tracker.log           # Application logs
├── src/
│   ├── auth.py               # Yahoo OAuth authentication
│   ├── data_collector.py     # Main data collection logic
│   ├── database.py           # Database operations
│   ├── analyzer.py           # Stats analysis and recaps
│   ├── photos.py             # Player photo management
│   └── visualize.py          # Visual recap generation
├── requirements.txt          # Python dependencies
├── run_daily_update.py       # Main script to run daily
└── generate_recaps.py        # Generate visual recaps
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Yahoo API Credentials

Follow the `yahoo_api_setup_guide.md` to get your credentials, then create:

`config/credentials.json`:
```json
{
  "consumer_key": "YOUR_CLIENT_ID",
  "consumer_secret": "YOUR_CLIENT_SECRET"
}
```

### 3. Configure Your League

Edit `config/config.yaml` with your league details:
```yaml
league_id: "YOUR_LEAGUE_ID"
game_code: "mlb"
season: 2025
```

### 4. First-Time Authentication

```bash
python src/auth.py
```

This will open a browser for OAuth authorization. Follow the prompts.

### 5. Run Your First Data Collection

```bash
python run_daily_update.py
```

## Daily Automation

### Using Cron (Linux/Mac)

Add to your crontab to run at 2 AM daily (after West Coast games finish):

```bash
crontab -e
```

Add this line:
```
0 2 * * * cd /path/to/yahoo_fantasy_tracker && /usr/bin/python3 run_daily_update.py >> logs/cron.log 2>&1
```

### Using Task Scheduler (Windows)

Create a scheduled task to run `run_daily_update.py` daily at 2 AM.

## Usage Examples

### Generate Visual Recaps

```bash
# Generate daily visual recap for today
python generate_recaps.py --week 5 --daily

# Generate daily recap for a specific date
python generate_recaps.py --week 5 --daily --date 2025-04-15

# Generate weekly visual recap
python generate_recaps.py --week 5 --weekly

# Generate both daily and weekly
python generate_recaps.py --week 5 --daily --weekly
```

Visual recaps are saved to `data/recaps/` as PNG images.

### Generate Text-Based Weekly Recap

```bash
# Standard recap with z-score composite scoring
python -m src.analyzer --week 5 --recap

# Use Yahoo points scoring
python -m src.analyzer --week 5 --recap --composite-method yahoo_points

# Generate daily recap with player attribution
python -m src.analyzer --week 5 --daily
```

### Export Data for R Analysis

```bash
# Export all data
python -m src.analyzer --export

# Export specific week
python -m src.analyzer --week 5 --export
```

## Data Analysis with R

Exported CSV files will be available in `data/exports/` for analysis with R/tidyverse.

## Troubleshooting

See `yahoo_api_setup_guide.md` for common authentication issues.

## API Usage

Expected daily API calls: ~20-25 per day (well under Yahoo's 10,000/day limit)
