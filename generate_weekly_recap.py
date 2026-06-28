#!/usr/bin/env python3
"""
Weekly Recap Generator

Generates visual recap images for a completed week of fantasy baseball.
Run this at the end of each matchup week to create shareable recap graphics.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualize import RecapVisualizer


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )


def main():
    """Generate weekly recap visualization."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate visual recap for a fantasy baseball week'
    )
    parser.add_argument(
        'week',
        type=int,
        help='Week number to generate recap for'
    )
    parser.add_argument(
        '--composite-method',
        type=str,
        default='yahoo_points',
        choices=['zscore', 'percentile', 'minmax', 'weighted_points', 'yahoo_points'],
        help='Composite scoring method for player of week (default: yahoo_points)'
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
    print(f"\n{'='*70}")
    print(f"Generating Weekly Recap - Week {args.week}")
    print(f"{'='*70}\n")
    
    try:
        visualizer = RecapVisualizer()
        
        print(f"Composite method: {args.composite_method}")
        print("Generating visualizations...")
        
        recap_images = visualizer.generate_weekly_recap_image(
            week=args.week,
            composite_method=args.composite_method
        )
        
        if recap_images:
            print(f"\n✓ Weekly recap complete! Generated {len(recap_images)} images:")
            for img_path in recap_images:
                print(f"  • {img_path.name}")
            print(f"\nAll saved to: {recap_images[0].parent.absolute()}")
            print(f"\n{'='*70}\n")
            return 0
        else:
            print("\n✗ Failed to generate weekly recap")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
