# 🎯 START HERE

Welcome to your Yahoo Fantasy Baseball Stat Tracker!

## 📋 What to Read First

1. **PROJECT_OVERVIEW.md** - Understand what you've got and how it works
2. **yahoo_api_setup_guide.md** - Set up your Yahoo API credentials (REQUIRED)
3. **QUICKSTART.md** - Step-by-step setup instructions
4. **README.md** - Technical documentation and usage

## 🚀 Quick Setup (5 steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Yahoo API Credentials
Follow the instructions in `yahoo_api_setup_guide.md` to create a Yahoo Developer app and get your credentials.

### 3. Configure Credentials
```bash
cp config/credentials.json.template config/credentials.json
# Edit config/credentials.json with your actual Yahoo API credentials
```

### 4. Configure Your League
Edit `config/config.yaml`:
- Add your league ID (find it in your league URL)
- Update the season year

### 5. Authenticate & Run
```bash
# First time authentication
python src/auth.py

# Collect data
python run_daily_update.py
```

## ✅ What This Does

Your tracker implements **BOTH** approaches you wanted:

✓ **Daily Matchup Snapshots** - Track weekly matchup stats each day
✓ **Player-Level Stats** - Individual player performance data
✓ **Daily Deltas** - See what changed since yesterday
✓ **Weekly Recaps** - Generate comprehensive summaries
✓ **CSV Export** - Export data for R/tidyverse analysis
✓ **Efficient API Usage** - Only ~20-25 calls per day (well under limits)

## 📊 Usage Examples

```bash
# Daily data collection (set this up as a cron job)
python run_daily_update.py

# Generate weekly recap
python -m src.analyzer --week 5 --recap

# Find player of the week (home runs)
python -m src.analyzer --week 5 --player-of-week HR

# Export data for R analysis
python -m src.analyzer --week 5 --export
```

## 🔍 Project Structure

```
yahoo_fantasy_tracker/
├── START_HERE.md              ← You are here!
├── PROJECT_OVERVIEW.md        ← Read this next
├── yahoo_api_setup_guide.md   ← Then this (REQUIRED)
├── QUICKSTART.md              ← Step-by-step setup
├── README.md                  ← Technical docs
│
├── run_daily_update.py        ← Main script - run daily!
│
├── src/                       ← Python modules
│   ├── auth.py               ← Yahoo authentication
│   ├── data_collector.py     ← Data collection (both approaches)
│   ├── database.py           ← SQLite operations
│   └── analyzer.py           ← Analysis and recaps
│
├── config/                    ← Configuration
│   ├── credentials.json.template
│   ├── credentials.json      ← CREATE THIS (your API keys)
│   └── config.yaml          ← Configure your league
│
├── data/                      ← Auto-created when you run
│   ├── fantasy_baseball.db   ← SQLite database
│   └── exports/              ← CSV files for R
│
└── logs/                      ← Auto-created when you run
    └── tracker.log           ← Application logs
```

## 🎓 Learning Python Data Analysis?

This project is perfect for practicing:
- API interactions
- Database operations (SQLite)
- Pandas for data manipulation
- Data visualization
- Command-line tools
- Scheduled jobs

The code is well-commented and structured to be readable!

## 🤔 Need Help?

Check these files:
- **Authentication issues**: `yahoo_api_setup_guide.md`
- **Setup questions**: `QUICKSTART.md`
- **How it works**: `PROJECT_OVERVIEW.md`
- **Error messages**: Check `logs/tracker.log`

## 📈 Next Steps

1. ✅ Read `PROJECT_OVERVIEW.md`
2. ✅ Follow `yahoo_api_setup_guide.md` to get API credentials
3. ✅ Complete setup in `QUICKSTART.md`
4. ✅ Run your first data collection
5. ✅ Set up daily automation (cron job)
6. ✅ Start analyzing your data!

---

**Ready?** Start with `PROJECT_OVERVIEW.md` to understand what you've got! 🚀⚾
