#!/usr/bin/env python3
"""
Daily Update Script for Yahoo Fantasy Baseball Tracker

This script should be run once per day (typically after all games conclude)
to capture daily snapshots of matchup and player stats.
"""

import sys
import logging
from datetime import datetime, date
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_collector import FantasyDataCollector
from src.visualize import RecapVisualizer


def setup_logging():
    """Configure logging to both file and console."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'tracker.log'
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger


def main():
    """Run daily data collection."""
    logger = setup_logging()
    
    print("=" * 70)
    print("Yahoo Fantasy Baseball Tracker - Daily Update")
    print("=" * 70)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Initialize collector
        logger.info("Initializing data collector...")
        collector = FantasyDataCollector()
        
        # Authenticate
        logger.info("Authenticating with Yahoo...")
        collector.connect()
        
        # Take snapshot
        logger.info("Taking daily snapshot...")
        collector.save_daily_snapshot()
        
        # Generate daily recap visualization
        logger.info("Generating daily recap visualization...")
        try:
            visualizer = RecapVisualizer()
            recap_image = visualizer.generate_daily_recap_image(
                week=collector.league.current_week()
            )
            if recap_image:
                logger.info(f"Daily recap saved to: {recap_image}")
                print(f"  Daily recap image: {recap_image}")
        except Exception as e:
            logger.warning(f"Could not generate daily recap visualization: {e}")
            print(f"  Warning: Visualization generation failed (data still saved)")
        
        # Clean up
        collector.close()
        
        print()
        print("=" * 70)
        print("✓ Daily update completed successfully!")
        print("=" * 70)
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        print()
        print("✗ Configuration file missing. Please check:")
        print("  - config/credentials.json exists with your Yahoo API credentials")
        print("  - config/config.yaml exists with your league settings")
        return 1
        
    except Exception as e:
        logger.error(f"Error during data collection: {e}", exc_info=True)
        print()
        print(f"✗ Error: {e}")
        print("Check logs/tracker.log for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
