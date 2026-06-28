# Quick Start Guide

## Step 1: Install Dependencies

```bash
cd yahoo_fantasy_tracker
pip install -r requirements.txt
```

## Step 2: Set Up Yahoo API Credentials

1. Follow the **yahoo_api_setup_guide.md** to get your Yahoo API credentials
2. Copy the template and add your credentials:

```bash
cp config/credentials.json.template config/credentials.json
```

3. Edit `config/credentials.json` with your actual credentials:
   - Replace `YOUR_YAHOO_CLIENT_ID_HERE` with your Consumer Key
   - Replace `YOUR_YAHOO_CLIENT_SECRET_HERE` with your Consumer Secret

## Step 3: Configure Your League

Edit `config/config.yaml`:

1. Find your league ID:
   - Go to your Yahoo Fantasy Baseball league
   - Look at the URL: `https://baseball.fantasysports.yahoo.com/b1/[LEAGUE_ID]/...`
   - Copy the league ID number

2. Update the config:
```yaml
league_id: "12345"  # Your actual league ID
season: 2025
```

## Step 4: Authenticate (First Time Only)

```bash
python src/auth.py
```

This will:
- Open your browser for Yahoo authorization
- Save your OAuth tokens to `config/oauth2.json`
- You only need to do this once!

## Step 5: Run Your First Data Collection

```bash
python run_daily_update.py
```

This will:
- Connect to Yahoo API
- Collect current matchup data
- Collect player stats
- Save everything to the database

## Step 6: Set Up Daily Automation

### On Linux/Mac (using cron):

```bash
crontab -e
```

Add this line (runs at 2 AM every day):
```
0 2 * * * cd /full/path/to/yahoo_fantasy_tracker && python3 run_daily_update.py >> logs/cron.log 2>&1
```

### On Windows (using Task Scheduler):

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 2:00 AM
4. Set action: Start a program
5. Program: `python`
6. Arguments: `run_daily_update.py`
7. Start in: `C:\path\to\yahoo_fantasy_tracker`

## Analyzing Your Data

### Generate Weekly Recap

```bash
python -m src.analyzer --week 5 --recap
```

### Find Player of the Week

```bash
python -m src.analyzer --week 5 --player-of-week HR
```

### Export Data for R Analysis

```bash
python -m src.analyzer --week 5 --export
```

CSV files will be saved to `data/exports/` for use with R/tidyverse!

## Troubleshooting

### "credentials.json not found"
- Make sure you copied the template and added your actual credentials

### "Authentication failed"
- Double-check your consumer key and secret
- Try deleting `config/oauth2.json` and re-running `python src/auth.py`

### "League not found"
- Verify your league ID in `config/config.yaml`
- Make sure you're using the league ID from the URL, not the team ID

### No data collected
- Check that it's during baseball season
- Verify the current week number
- Look at `logs/tracker.log` for detailed error messages

## Next Steps

Once you have a few days of data:

1. **View daily changes**: Compare today vs yesterday
2. **Generate visualizations**: Create charts with Python or R
3. **Build custom reports**: Use the database directly or export to CSV
4. **Analyze trends**: Track player/team performance over time

## File Locations

- **Database**: `data/fantasy_baseball.db` (SQLite)
- **Logs**: `logs/tracker.log`
- **CSV Exports**: `data/exports/`
- **Config**: `config/` (keep these files private!)

## Security Reminder

Never commit these files to git:
- `config/credentials.json`
- `config/oauth2.json`
- `data/fantasy_baseball.db`

They're already in `.gitignore` for you!
