#!/usr/bin/env python3
"""
Quick test script to verify the pipeline works
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from build_night_json import NightFeedBuilder

def main():
    print("=" * 60)
    print("Overflight Night Feed - Quick Test")
    print("=" * 60)
    print()
    print("This will test the pipeline with 5 items from the upstream feed.")
    print()
    
    # Create builder
    builder = NightFeedBuilder(
        upstream_url="https://raw.githubusercontent.com/projectivy/overflight/main/videos.json",
        output_path=Path(__file__).parent / "test_night.json",
        max_items=5,
        max_workers=2
    )
    
    try:
        # Run with report
        builder.run(dry_run=False, write_report=True)
        
        print()
        print("=" * 60)
        print("✅ Test successful!")
        print("=" * 60)
        print()
        print("Check these files:")
        print("  - test_night.json (filtered output)")
        print("  - reports/analysis_report.csv (detailed report)")
        print()
        print("If everything looks good, you can run the full pipeline:")
        print("  cd scripts")
        print("  python build_night_json.py")
        print()
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Test failed!")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("  1. FFmpeg not installed: install from https://ffmpeg.org")
        print("  2. Missing dependencies: pip install -r requirements.txt")
        print("  3. Network error: check your internet connection")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
