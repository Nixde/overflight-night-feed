#!/usr/bin/env python3
"""
Build Night JSON Feed for Overflight

This script:
1. Reads video data from local videos.json (Apple Aerials feed)
2. Analyzes each video for darkness using image/video frame analysis
3. Generates night.json with only dark/night videos
4. Creates detailed reports with enhanced metrics

Enhanced v2.0:
- Daylight veto reporting
- Multi-frame analysis info
- Border crop reporting
- All new metrics (p90_y, bright_pixel_ratio, mid_bright_ratio, low_sat_bright_ratio)
- Decision rule tracking
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any

from tqdm import tqdm

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from media_probe import MediaProbe, ClassificationResult, DarknessMetrics

# Configure logging
_repo_root = Path(__file__).resolve().parent.parent
_log_dir = _repo_root / 'reports'
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(_log_dir / 'build.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics from processing run"""
    total_items: int = 0
    accepted: int = 0
    rejected: int = 0
    errors: int = 0
    daylight_veto_count: int = 0
    processing_time_seconds: float = 0.0
    
    @property
    def acceptance_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.accepted / self.total_items) * 100


class NightFeedBuilder:
    """Builds the night-only video feed"""
    
    UPSTREAM_URL = "https://raw.githubusercontent.com/AmnesiaBeing/Aerial-Apple-tvos-videos-json/master/videos.json"
    LOCAL_SOURCE = "videos.json"
    
    def __init__(self, 
                 output_dir: Path = Path("."),
                 workers: int = 8,
                 save_debug_frames: int = 0):
        """
        Initialize builder
        
        Args:
            output_dir: Directory for output files
            workers: Number of concurrent workers
            save_debug_frames: If > 0, save debug frames for analysis
        """
        self.output_dir = output_dir
        self.workers = workers
        self.save_debug_frames = save_debug_frames
        
        # Setup directories
        self.reports_dir = output_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize probe with debug frame saving if requested
        self.probe = MediaProbe(save_debug_frames=save_debug_frames)
        
        # Results storage
        self.results: List[Dict[str, Any]] = []
        self.stats = ProcessingStats()
    
    def fetch_upstream_data(self) -> List[dict]:
        """
        Fetch video data from local file
        
        Returns:
            List of video items from source feed
        """
        source_path = self.output_dir / self.LOCAL_SOURCE
        
        if not source_path.exists():
            logger.error(f"Local source file not found: {source_path}")
            logger.info(f"Please download the upstream feed to: {source_path}")
            return []
        
        logger.info(f"Reading local source: {source_path}")
        
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if 'assets' in data:
                items = data['assets']
            elif 'videos' in data:
                items = data['videos']
            elif 'items' in data:
                items = data['items']
            else:
                # Try to find a list in the dict values
                for value in data.values():
                    if isinstance(value, list) and len(value) > 0:
                        items = value
                        break
                else:
                    items = [data]
        else:
            items = [data]
        
        logger.info(f"Found {len(items)} video items in source")
        return items
    
    def process_item(self, item: dict) -> Dict[str, Any]:
        """
        Process a single video item
        
        Returns:
            Result entry with classification details
        """
        title = item.get('title', item.get('name', 'Unknown'))
        
        try:
            result = self.probe.classify_item(item)
            
            result_entry = {
                'title': title,
                'location': item.get('location', ''),
                'accepted': result.accepted,
                'reason': result.reason,
                'metadata_category': result.metadata_category,
                'daylight_veto': result.daylight_veto,
                'decision_rule': result.decision_rule,
                'media_source': result.media_source,
                'original_item': item
            }
            
            if result.metrics:
                result_entry['metrics'] = {
                    'median_y': round(result.metrics.median_y, 4),
                    'p25_y': round(result.metrics.p25_y, 4),
                    'p75_y': round(result.metrics.p75_y, 4),
                    'p90_y': round(result.metrics.p90_y, 4),
                    'dark_pixel_ratio': round(result.metrics.dark_pixel_ratio, 4),
                    'mean_y': round(result.metrics.mean_y, 4),
                    'bright_pixel_ratio': round(result.metrics.bright_pixel_ratio, 4),
                    'mid_bright_ratio': round(result.metrics.mid_bright_ratio, 4),
                    'low_sat_bright_ratio': round(result.metrics.low_sat_bright_ratio, 4),
                    'frames_analyzed': result.metrics.frames_analyzed,
                    'timestamps_used': result.metrics.timestamps_used,
                    'border_crop': result.metrics.border_crop
                }
            
            return result_entry
            
        except Exception as e:
            logger.error(f"Error processing '{title}': {e}")
            return {
                'title': title,
                'location': item.get('location', ''),
                'accepted': False,
                'reason': f"Processing error: {str(e)}",
                'metadata_category': 'error',
                'daylight_veto': False,
                'decision_rule': 'error',
                'media_source': 'error',
                'original_item': item,
                'error': str(e)
            }
    
    def process_all(self, items: List[dict]) -> None:
        """
        Process all items concurrently
        
        Args:
            items: List of video items to process
        """
        self.stats.total_items = len(items)
        self.results = []
        
        start_time = time.time()
        
        logger.info(f"Processing {len(items)} items with {self.workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self.process_item, item): item for item in items}
            
            with tqdm(total=len(items), desc="Analyzing videos", unit="video") as pbar:
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        self.results.append(result)
                        
                        if result['accepted']:
                            self.stats.accepted += 1
                        else:
                            self.stats.rejected += 1
                            if result.get('daylight_veto'):
                                self.stats.daylight_veto_count += 1
                        
                        if 'error' in result:
                            self.stats.errors += 1
                            
                    except Exception as e:
                        logger.error(f"Future execution error: {e}")
                        self.stats.errors += 1
                    
                    pbar.update(1)
        
        self.stats.processing_time_seconds = time.time() - start_time
        
        logger.info(f"Processing complete in {self.stats.processing_time_seconds:.1f}s")
        logger.info(f"Accepted: {self.stats.accepted}, Rejected: {self.stats.rejected}, "
                   f"Errors: {self.stats.errors}, Daylight Vetos: {self.stats.daylight_veto_count}")
    
    def build_feed(self) -> dict:
        """
        Build the final night.json feed structure
        
        Returns:
            Feed dict ready for JSON serialization
        """
        accepted_items = [r['original_item'] for r in self.results if r['accepted']]
        
        feed = {
            "metadata": {
                "generator": "overflight-night-feed v2.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": self.LOCAL_SOURCE,
                "total_analyzed": self.stats.total_items,
                "total_accepted": len(accepted_items),
                "acceptance_rate": f"{self.stats.acceptance_rate:.1f}%",
                "daylight_veto_count": self.stats.daylight_veto_count,
                "processing_time_seconds": round(self.stats.processing_time_seconds, 1),
                "version": "2.0",
                "algorithm": "daylight_veto_with_multi_frame"
            },
            "assets": accepted_items
        }
        
        return feed
    
    def write_feed(self, feed: dict) -> Path:
        """
        Write feed to night.json
        
        Returns:
            Path to output file
        """
        output_path = self.output_dir / "night.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(feed, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Wrote feed to: {output_path}")
        return output_path
    
    def write_report(self) -> Path:
        """
        Write detailed classification report with enhanced metrics
        
        Returns:
            Path to report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"classification_report_{timestamp}.json"
        
        # Sort results for readability
        accepted = sorted(
            [r for r in self.results if r['accepted']],
            key=lambda x: x['metrics'].get('median_y', 0) if 'metrics' in x else 0
        )
        
        rejected = sorted(
            [r for r in self.results if not r['accepted']],
            key=lambda x: x['metrics'].get('median_y', 1) if 'metrics' in x else 1,
            reverse=True
        )
        
        # Group rejected by reason type
        rejected_by_daylight_veto = [r for r in rejected if r.get('daylight_veto')]
        rejected_by_rules = [r for r in rejected if not r.get('daylight_veto') and not r.get('error')]
        rejected_by_error = [r for r in rejected if r.get('error')]
        
        report = {
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "statistics": {
                "total_items": self.stats.total_items,
                "accepted": self.stats.accepted,
                "rejected": self.stats.rejected,
                "rejected_by_daylight_veto": len(rejected_by_daylight_veto),
                "rejected_by_rules": len(rejected_by_rules),
                "rejected_by_error": len(rejected_by_error),
                "errors": self.stats.errors,
                "acceptance_rate": f"{self.stats.acceptance_rate:.1f}%",
                "processing_time_seconds": round(self.stats.processing_time_seconds, 1)
            },
            "thresholds_used": {
                "veto_bright_pixel_ratio": 0.10,
                "veto_mid_bright_ratio": 0.25,
                "veto_p75_y": 0.40,
                "veto_p90_y": 0.55,
                "veto_low_sat_bright": 0.06,
                "night_median_threshold": 0.22,
                "night_dark_ratio_threshold": 0.65,
                "night_p75_threshold": 0.33,
                "neutral_p75_cap": 0.32,
                "neutral_p90_cap": 0.45,
                "neutral_mid_bright_cap": 0.18
            },
            "accepted_items": [
                {
                    "title": r['title'],
                    "location": r['location'],
                    "metadata_category": r['metadata_category'],
                    "decision_rule": r['decision_rule'],
                    "media_source": r.get('media_source', 'unknown'),
                    "reason": r['reason'],
                    "metrics": r.get('metrics', {})
                }
                for r in accepted
            ],
            "rejected_items": {
                "daylight_veto": [
                    {
                        "title": r['title'],
                        "location": r['location'],
                        "metadata_category": r['metadata_category'],
                        "decision_rule": r['decision_rule'],
                        "media_source": r.get('media_source', 'unknown'),
                        "reason": r['reason'],
                        "metrics": r.get('metrics', {})
                    }
                    for r in rejected_by_daylight_veto
                ],
                "failed_rules": [
                    {
                        "title": r['title'],
                        "location": r['location'],
                        "metadata_category": r['metadata_category'],
                        "decision_rule": r['decision_rule'],
                        "media_source": r.get('media_source', 'unknown'),
                        "reason": r['reason'],
                        "metrics": r.get('metrics', {})
                    }
                    for r in rejected_by_rules
                ],
                "errors": [
                    {
                        "title": r['title'],
                        "location": r['location'],
                        "error": r.get('error', r['reason'])
                    }
                    for r in rejected_by_error
                ]
            }
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Wrote classification report to: {report_path}")
        
        # Also write a simple summary to latest_report.json for easy access
        latest_path = self.reports_dir / "latest_report.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    def write_summary_txt(self) -> Path:
        """
        Write human-readable summary with decision explanations
        
        Returns:
            Path to summary file
        """
        summary_path = self.reports_dir / "summary.txt"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("OVERFLIGHT NIGHT FEED - CLASSIFICATION SUMMARY (v2.0)\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Processing time: {self.stats.processing_time_seconds:.1f} seconds\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("STATISTICS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total videos analyzed: {self.stats.total_items}\n")
            f.write(f"Accepted (night/dark): {self.stats.accepted}\n")
            f.write(f"Rejected: {self.stats.rejected}\n")
            f.write(f"  - By daylight veto: {self.stats.daylight_veto_count}\n")
            f.write(f"  - By other rules: {self.stats.rejected - self.stats.daylight_veto_count - self.stats.errors}\n")
            f.write(f"  - By errors: {self.stats.errors}\n")
            f.write(f"Acceptance rate: {self.stats.acceptance_rate:.1f}%\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("DAYLIGHT VETO THRESHOLDS\n")
            f.write("-" * 70 + "\n")
            f.write("Videos are REJECTED if ANY of these are exceeded:\n")
            f.write("  bright_pixel_ratio >= 0.10 (>10% bright pixels)\n")
            f.write("  mid_bright_ratio >= 0.25 (>25% medium-bright pixels)\n")
            f.write("  p75_y >= 0.40 (75th percentile luminance too high)\n")
            f.write("  p90_y >= 0.55 (90th percentile luminance too high)\n")
            f.write("  low_sat_bright_ratio >= 0.06 (>6% sky-like pixels)\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("ACCEPTED VIDEOS (sorted by darkness)\n")
            f.write("-" * 70 + "\n")
            
            accepted = sorted(
                [r for r in self.results if r['accepted']],
                key=lambda x: x['metrics'].get('median_y', 0) if 'metrics' in x else 0
            )
            
            for r in accepted:
                f.write(f"\n  {r['title']}")
                if r['location']:
                    f.write(f" ({r['location']})")
                f.write("\n")
                f.write(f"    Category: {r['metadata_category']}\n")
                f.write(f"    Decision: {r['decision_rule']}\n")
                if 'metrics' in r:
                    m = r['metrics']
                    f.write(f"    Metrics: median={m.get('median_y', 'N/A'):.3f}, "
                           f"p75={m.get('p75_y', 'N/A'):.3f}, "
                           f"p90={m.get('p90_y', 'N/A'):.3f}, "
                           f"bright={m.get('bright_pixel_ratio', 'N/A'):.3f}\n")
                    if m.get('frames_analyzed', 1) > 1:
                        f.write(f"    Frames: {m['frames_analyzed']} @ {m.get('timestamps_used', [])}\n")
            
            f.write("\n" + "-" * 70 + "\n")
            f.write("REJECTED VIDEOS (by reason)\n")
            f.write("-" * 70 + "\n")
            
            # Group by reason type
            rejected_veto = [r for r in self.results if not r['accepted'] and r.get('daylight_veto')]
            rejected_rules = [r for r in self.results if not r['accepted'] and not r.get('daylight_veto') and not r.get('error')]
            rejected_error = [r for r in self.results if not r['accepted'] and r.get('error')]
            
            if rejected_veto:
                f.write("\n--- DAYLIGHT VETO (bright sky/daylight detected) ---\n")
                for r in rejected_veto:
                    f.write(f"\n  {r['title']}")
                    if r['location']:
                        f.write(f" ({r['location']})")
                    f.write("\n")
                    f.write(f"    Veto reason: {r['reason']}\n")
                    if 'metrics' in r:
                        m = r['metrics']
                        f.write(f"    Metrics: median={m.get('median_y', 'N/A'):.3f}, "
                               f"p75={m.get('p75_y', 'N/A'):.3f}, "
                               f"p90={m.get('p90_y', 'N/A'):.3f}, "
                               f"bright={m.get('bright_pixel_ratio', 'N/A'):.3f}, "
                               f"sky={m.get('low_sat_bright_ratio', 'N/A'):.3f}\n")
            
            if rejected_rules:
                f.write("\n--- FAILED ACCEPTANCE RULES ---\n")
                for r in rejected_rules:
                    f.write(f"\n  {r['title']}")
                    if r['location']:
                        f.write(f" ({r['location']})")
                    f.write("\n")
                    f.write(f"    Category: {r['metadata_category']}\n")
                    f.write(f"    Reason: {r['reason']}\n")
                    if 'metrics' in r:
                        m = r['metrics']
                        f.write(f"    Metrics: median={m.get('median_y', 'N/A'):.3f}, "
                               f"p75={m.get('p75_y', 'N/A'):.3f}\n")
            
            if rejected_error:
                f.write("\n--- ERRORS ---\n")
                for r in rejected_error:
                    f.write(f"\n  {r['title']}: {r.get('error', r['reason'])}\n")
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 70 + "\n")
        
        logger.info(f"Wrote summary to: {summary_path}")
        return summary_path
    
    def run(self) -> bool:
        """
        Run the full pipeline
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Starting Overflight Night Feed Builder v2.0")
        logger.info("=" * 60)
        
        # Fetch source data
        items = self.fetch_upstream_data()
        if not items:
            logger.error("No items to process")
            return False
        
        # Process all items
        self.process_all(items)
        
        # Build and write feed
        feed = self.build_feed()
        self.write_feed(feed)
        
        # Write reports
        self.write_report()
        self.write_summary_txt()
        
        # Cleanup old cache
        self.probe.cleanup_cache(max_age_days=7)
        
        logger.info("=" * 60)
        logger.info(f"Pipeline complete!")
        logger.info(f"Accepted: {self.stats.accepted}/{self.stats.total_items} "
                   f"({self.stats.acceptance_rate:.1f}%)")
        logger.info(f"Daylight vetos: {self.stats.daylight_veto_count}")
        logger.info("=" * 60)
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build night-only video feed for Overflight"
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=Path("."),
        help="Output directory (default: current directory)"
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=8,
        help="Number of concurrent workers (default: 8)"
    )
    parser.add_argument(
        '--debug-frames',
        type=int,
        default=0,
        help="Save debug frames for analysis (0 = disabled)"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure reports directory exists
    reports_dir = args.output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    builder = NightFeedBuilder(
        output_dir=args.output_dir,
        workers=args.workers,
        save_debug_frames=args.debug_frames
    )
    
    success = builder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
