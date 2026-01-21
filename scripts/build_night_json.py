#!/usr/bin/env python3
"""
Overflight Night Feed Generator

Generates a filtered JSON feed containing only night/dark aerial videos
for Projectivy Overflight wallpaper plugin.
"""

import argparse
import csv
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

import requests
from tqdm import tqdm

from media_probe import ClassificationResult, MediaProbe

# Configuration
# Default to local videos.json if it exists, otherwise use upstream URL
import os
_LOCAL_JSON = Path(__file__).parent.parent / "videos.json"
DEFAULT_UPSTREAM_URL = str(_LOCAL_JSON) if _LOCAL_JSON.exists() else "https://raw.githubusercontent.com/projectivy/overflight/main/videos.json"
DEFAULT_OUTPUT_NAME = "night.json"
DEFAULT_MAX_WORKERS = 8

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NightFeedBuilder:
    """Builds filtered night feed from upstream JSON"""
    
    def __init__(
        self,
        upstream_url: str,
        output_path: Path,
        max_items: Optional[int] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
        cache_dir: Optional[Path] = None,
        timeout: int = 30
    ):
        """
        Initialize NightFeedBuilder
        
        Args:
            upstream_url: URL to upstream videos.json
            output_path: Path for output night.json
            max_items: Optional limit on items to process
            max_workers: Max concurrent workers for analysis
            cache_dir: Cache directory for media files
            timeout: Request timeout in seconds
        """
        self.upstream_url = upstream_url
        self.output_path = output_path
        self.max_items = max_items
        self.max_workers = max_workers
        self.media_probe = MediaProbe(cache_dir=cache_dir, timeout=timeout)
        self.session = requests.Session()
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def fetch_upstream_data(self) -> List[dict]:
        """
        Fetch upstream JSON data
        
        Returns:
            List of video items
        """
        logger.info(f"Fetching upstream data from: {self.upstream_url}")
        
        try:
            # Check if it's a local file
            if os.path.exists(self.upstream_url):
                logger.info(f"Loading local file: {self.upstream_url}")
                with open(self.upstream_url, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Fetch from URL
                response = self.session.get(
                    self.upstream_url, 
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
            
            # Handle different JSON structures
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and 'videos' in data:
                items = data['videos']
            elif isinstance(data, dict) and 'items' in data:
                items = data['items']
            else:
                logger.error(f"Unexpected JSON structure: {type(data)}")
                items = []
            
            logger.info(f"Fetched {len(items)} items from upstream")
            
            # Apply max_items limit if specified
            if self.max_items:
                items = items[:self.max_items]
                logger.info(f"Limited to {len(items)} items")
            
            return items
            
        except requests.RequestException as e:
            logger.error(f"Error fetching upstream data: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            raise
    
    def process_item(self, item: dict) -> tuple[dict, ClassificationResult]:
        """
        Process a single item
        
        Args:
            item: Video item dict
            
        Returns:
            (item, classification_result)
        """
        try:
            result = self.media_probe.classify_item(item)
            return item, result
        except Exception as e:
            logger.error(f"Error processing item '{item.get('title', 'unknown')}': {e}")
            # Return a failed result
            from media_probe import ClassificationResult
            result = ClassificationResult(
                accepted=False,
                reason=f"Processing error: {str(e)}",
                metrics=None,
                metadata_category='unknown'
            )
            return item, result
    
    def build_feed(self, write_report: bool = False) -> dict:
        """
        Build night feed by filtering upstream data
        
        Args:
            write_report: Whether to write detailed report
            
        Returns:
            Dict with 'accepted' and 'rejected' items and results
        """
        # Fetch upstream data
        items = self.fetch_upstream_data()
        
        if not items:
            logger.warning("No items to process")
            return {'accepted': [], 'rejected': []}
        
        # Process items concurrently
        logger.info(f"Processing {len(items)} items with {self.max_workers} workers...")
        
        accepted_items = []
        rejected_items = []
        results_data = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(self.process_item, item): item 
                for item in items
            }
            
            # Process completed tasks with progress bar
            with tqdm(total=len(items), desc="Analyzing videos") as pbar:
                for future in as_completed(future_to_item):
                    try:
                        item, result = future.result()
                        
                        # Store result
                        result_entry = {
                            'title': item.get('title', ''),
                            'location': item.get('location', ''),
                            'accepted': result.accepted,
                            'reason': result.reason,
                            'metadata_category': result.metadata_category
                        }
                        
                        if result.metrics:
                            result_entry.update({
                                'median_y': result.metrics.median_y,
                                'p25_y': result.metrics.p25_y,
                                'p75_y': result.metrics.p75_y,
                                'dark_pixel_ratio': result.metrics.dark_pixel_ratio
                            })
                        
                        results_data.append(result_entry)
                        
                        if result.accepted:
                            accepted_items.append((item, result))
                        else:
                            rejected_items.append((item, result))
                        
                    except Exception as e:
                        logger.error(f"Error processing future: {e}")
                    
                    pbar.update(1)
        
        logger.info(f"Processing complete: {len(accepted_items)} accepted, "
                   f"{len(rejected_items)} rejected")
        
        # Write report if requested
        if write_report:
            self._write_report(results_data)
        
        return {
            'accepted': accepted_items,
            'rejected': rejected_items,
            'results': results_data
        }
    
    def _write_report(self, results_data: List[dict]):
        """Write detailed analysis report"""
        reports_dir = self.output_path.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        # Write CSV report
        csv_path = reports_dir / 'analysis_report.csv'
        logger.info(f"Writing analysis report to: {csv_path}")
        
        fieldnames = [
            'title', 'location', 'accepted', 'reason', 
            'metadata_category', 'median_y', 'p25_y', 'p75_y', 
            'dark_pixel_ratio'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results_data)
        
        # Write JSON report
        json_path = reports_dir / 'analysis_report.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"Reports written to {reports_dir}")
    
    def write_output(self, accepted_items: List[tuple], dry_run: bool = False):
        """
        Write filtered output JSON
        
        Args:
            accepted_items: List of (item, result) tuples
            dry_run: If True, don't write file
        """
        # Extract just the items (without results)
        output_items = [item for item, _ in accepted_items]
        
        # Sort for deterministic output (by location, then title)
        output_items.sort(key=lambda x: (x.get('location', ''), x.get('title', '')))
        
        if dry_run:
            logger.info("DRY RUN: Would write output JSON with "
                       f"{len(output_items)} items")
            # Print first few items as preview
            print("\nPreview (first 3 items):")
            print(json.dumps(output_items[:3], indent=2))
            return
        
        # Write output file
        logger.info(f"Writing output to: {self.output_path}")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(output_items, f, indent=2)
        
        logger.info(f"Successfully wrote {len(output_items)} items to {self.output_path}")
    
    def run(self, dry_run: bool = False, write_report: bool = False):
        """
        Run the complete pipeline
        
        Args:
            dry_run: If True, don't write output file
            write_report: If True, write detailed analysis report
        """
        logger.info("=" * 60)
        logger.info("Overflight Night Feed Generator")
        logger.info("=" * 60)
        logger.info(f"Upstream: {self.upstream_url}")
        logger.info(f"Output: {self.output_path}")
        logger.info(f"Max workers: {self.max_workers}")
        logger.info(f"Max items: {self.max_items or 'unlimited'}")
        logger.info("=" * 60)
        
        # Build feed
        results = self.build_feed(write_report=write_report)
        
        # Write output
        self.write_output(results['accepted'], dry_run=dry_run)
        
        # Summary statistics
        logger.info("=" * 60)
        logger.info("Summary:")
        logger.info(f"  Total items: {len(results['accepted']) + len(results['rejected'])}")
        logger.info(f"  Accepted: {len(results['accepted'])}")
        logger.info(f"  Rejected: {len(results['rejected'])}")
        logger.info(f"  Acceptance rate: "
                   f"{len(results['accepted']) / (len(results['accepted']) + len(results['rejected'])) * 100:.1f}%")
        logger.info("=" * 60)
        
        # Cleanup old cache files
        self.media_probe.cleanup_cache(max_age_days=7)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate night-only feed for Overflight',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default upstream URL
  python build_night_json.py
  
  # Dry run to preview results
  python build_night_json.py --dry-run
  
  # Generate with detailed report
  python build_night_json.py --write-report
  
  # Use custom upstream URL and limit items
  python build_night_json.py --upstream-url https://example.com/videos.json --max-items 50
  
  # Custom output location
  python build_night_json.py --output ../night.json
        """
    )
    
    parser.add_argument(
        '--upstream-url',
        default=DEFAULT_UPSTREAM_URL,
        help=f'Upstream JSON URL (default: {DEFAULT_UPSTREAM_URL})'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path(__file__).parent.parent / DEFAULT_OUTPUT_NAME,
        help=f'Output file path (default: ../{DEFAULT_OUTPUT_NAME})'
    )
    
    parser.add_argument(
        '--max-items',
        type=int,
        help='Maximum items to process (for testing)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f'Max concurrent workers (default: {DEFAULT_MAX_WORKERS})'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=Path,
        help='Cache directory for media files'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview results without writing output file'
    )
    
    parser.add_argument(
        '--write-report',
        action='store_true',
        help='Write detailed analysis report (CSV/JSON)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Build feed
    try:
        builder = NightFeedBuilder(
            upstream_url=args.upstream_url,
            output_path=args.output,
            max_items=args.max_items,
            max_workers=args.max_workers,
            cache_dir=args.cache_dir,
            timeout=args.timeout
        )
        
        builder.run(dry_run=args.dry_run, write_report=args.write_report)
        
        logger.info("Build complete!")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Build interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
