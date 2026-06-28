#!/usr/bin/env python3
"""
Generate Visual Recaps

Convenient wrapper for generating daily and weekly visual recaps.
"""

import sys
import logging
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.visualize import RecapVisualizer


def setup_logging():
    """Configure logging."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/visualize.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Generate visual recaps."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate visual recaps for fantasy baseball',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate today's daily recap for week 5
  python generate_recaps.py --week 5 --daily
  
  # Generate daily recap for a specific date
  python generate_recaps.py --week 5 --daily --date 2025-04-15
  
  # Generate weekly recap
  python generate_recaps.py --week 5 --weekly
  
  # Generate both
  python generate_recaps.py --week 5 --daily --weekly
        '''
    )
    
    parser.add_argument('--week', type=int, required=True, 
                       help='Week number to generate recap for')
    parser.add_argument('--daily', action='store_true',
                       help='Generate daily recap')
    parser.add_argument('--weekly', action='store_true',
                       help='Generate weekly recap')
    parser.add_argument('--date', type=str,
                       help='Date for daily recap (YYYY-MM-DD), defaults to today')
    
    args = parser.parse_args()
    
    if not args.daily and not args.weekly:
        print("Error: Must specify --daily and/or --weekly")
        return 1
    
    setup_logging()
    
    print("=" * 70)
    print("Visual Recap Generator")
    print("=" * 70)
    print()
    
    visualizer = RecapVisualizer()
    success = True
    
    if args.daily:
        print(f"Generating daily recap for week {args.week}...")
        
        recap_date = date.fromisoformat(args.date) if args.date else date.today()
        
        try:
            output = visualizer.generate_daily_recap(args.week, recap_date)
            if output:
                print(f"✓ Daily recap saved to: {output}")
                print()
            else:
                print("✗ Failed to generate daily recap (no data available)")
                success = False
        except Exception as e:
            print(f"✗ Error generating daily recap: {e}")
            logging.exception("Daily recap generation failed")
            success = False
    
    if args.weekly:
        print(f"Generating weekly recap for week {args.week}...")
        
        try:
            output = visualizer.generate_weekly_recap(args.week)
            if output:
                print(f"✓ Weekly recap saved to: {output}")
                print()
            else:
                print("✗ Failed to generate weekly recap (no data available)")
                success = False
        except Exception as e:
            print(f"✗ Error generating weekly recap: {e}")
            logging.exception("Weekly recap generation failed")
            success = False
    
    print("=" * 70)
    if success:
        print("Recap generation complete!")
    else:
        print("Recap generation completed with errors - check logs/visualize.log")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
