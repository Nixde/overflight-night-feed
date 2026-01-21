"""
Media Probe Module - Darkness Classification for Aerial Videos
Analyzes images and video frames to determine darkness levels
"""

import hashlib
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import requests
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class DarknessMetrics:
    """Computed darkness metrics for an image"""
    median_y: float
    p25_y: float
    p75_y: float
    dark_pixel_ratio: float
    mean_y: float
    
    def __str__(self):
        return (f"DarknessMetrics(median={self.median_y:.3f}, "
                f"p25={self.p25_y:.3f}, p75={self.p75_y:.3f}, "
                f"dark_ratio={self.dark_pixel_ratio:.3f})")


@dataclass
class ClassificationResult:
    """Result of darkness classification"""
    accepted: bool
    reason: str
    metrics: Optional[DarknessMetrics]
    metadata_category: str  # 'night', 'sunset', 'day', 'neutral'


class MediaProbe:
    """Analyzes media for darkness classification"""
    
    # Darkness acceptance thresholds
    NIGHT_MEDIAN_THRESHOLD = 0.22
    NIGHT_DARK_RATIO_THRESHOLD = 0.65
    NIGHT_P75_THRESHOLD = 0.35
    NIGHT_DARK_LUMINANCE = 0.18
    
    SUNSET_MEDIAN_THRESHOLD = 0.28
    SUNSET_P25_THRESHOLD = 0.14
    SUNSET_DARK_RATIO_THRESHOLD = 0.55
    
    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 30):
        """
        Initialize MediaProbe
        
        Args:
            cache_dir: Directory for caching downloaded media
            timeout: Request timeout in seconds
        """
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "overflight_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
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
    
    def classify_item(self, item: dict) -> ClassificationResult:
        """
        Classify a video item as night/dark or not
        
        Args:
            item: Video item dict with location, title, and URL fields
            
        Returns:
            ClassificationResult with acceptance decision and metrics
        """
        # Step 1: Metadata gating
        title = item.get('title', '').lower()
        location = item.get('location', '').lower()
        combined_text = f"{title} {location}"
        
        metadata_category = self._classify_metadata(combined_text)
        logger.info(f"Item '{item.get('title', 'unknown')}' - metadata: {metadata_category}")
        
        # Step 2: Get representative image
        try:
            image_path = self._get_representative_image(item)
            if not image_path:
                logger.warning(f"Could not get image for '{item.get('title', 'unknown')}'")
                return ClassificationResult(
                    accepted=False,
                    reason="Failed to obtain image for analysis",
                    metrics=None,
                    metadata_category=metadata_category
                )
            
            # Step 3: Compute darkness metrics
            metrics = self._compute_darkness_metrics(image_path)
            logger.info(f"Metrics: {metrics}")
            
            # Step 4: Apply acceptance rules
            accepted, reason = self._apply_acceptance_rules(metadata_category, metrics)
            
            return ClassificationResult(
                accepted=accepted,
                reason=reason,
                metrics=metrics,
                metadata_category=metadata_category
            )
            
        except Exception as e:
            logger.error(f"Error classifying item: {e}", exc_info=True)
            # Fail-closed: reject if we can't analyze
            return ClassificationResult(
                accepted=False,
                reason=f"Analysis error: {str(e)}",
                metrics=None,
                metadata_category=metadata_category
            )
    
    def _classify_metadata(self, text: str) -> str:
        """Classify based on metadata keywords"""
        night_keywords = ['night', 'twilight', 'dusk', 'evening', 'aurora']
        sunset_keywords = ['sunset']
        day_keywords = ['day', 'noon', 'sunrise', 'morning']
        
        if any(kw in text for kw in night_keywords):
            return 'night'
        elif any(kw in text for kw in sunset_keywords):
            return 'sunset'
        elif any(kw in text for kw in day_keywords):
            return 'day'
        else:
            return 'neutral'
    
    def _get_representative_image(self, item: dict) -> Optional[Path]:
        """
        Get a representative image from item (thumbnail or extracted frame)
        
        Args:
            item: Video item dict
            
        Returns:
            Path to cached image file or None
        """
        # Try to find thumbnail URL
        thumbnail_keys = ['url_img', 'image', 'thumbnail', 'thumb', 'poster']
        thumbnail_url = None
        
        for key in thumbnail_keys:
            if key in item and item[key]:
                thumbnail_url = item[key]
                break
        
        if thumbnail_url:
            logger.debug(f"Using thumbnail URL: {thumbnail_url}")
            return self._download_image(thumbnail_url)
        
        # No thumbnail - extract from video
        video_url = self._get_best_video_url(item)
        if video_url:
            logger.debug(f"Extracting frame from video: {video_url}")
            return self._extract_video_frame(video_url)
        
        logger.warning("No thumbnail or video URL found")
        return None
    
    def _get_best_video_url(self, item: dict) -> Optional[str]:
        """Get best video URL (prefer 1080p over 4K for speed)"""
        # Priority order: 1080p, 720p, 4K, any url_* field
        priority_keys = ['url_1080p', 'url_720p', 'url_4k', 'url_2160p']
        
        for key in priority_keys:
            if key in item and item[key]:
                return item[key]
        
        # Fallback: find any url_* field
        for key, value in item.items():
            if key.startswith('url_') and value and isinstance(value, str):
                if value.startswith('http'):
                    return value
        
        return None
    
    def _download_image(self, url: str) -> Optional[Path]:
        """Download image with caching"""
        # Generate cache key from URL
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        cache_path = self.cache_dir / f"{cache_key}.jpg"
        
        if cache_path.exists():
            logger.debug(f"Using cached image: {cache_path}")
            return cache_path
        
        try:
            logger.debug(f"Downloading image: {url}")
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"Saved to cache: {cache_path}")
            return cache_path
            
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def _extract_video_frame(self, video_url: str) -> Optional[Path]:
        """Extract a single frame from video using ffmpeg"""
        # Generate cache key
        cache_key = hashlib.sha256(video_url.encode()).hexdigest()
        cache_path = self.cache_dir / f"{cache_key}_frame.jpg"
        
        if cache_path.exists():
            logger.debug(f"Using cached frame: {cache_path}")
            return cache_path
        
        # Check if ffmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True,
                         timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("ffmpeg not available - cannot extract video frames")
            return None
        
        try:
            # Extract frame at 4 seconds, resize to 256px width for speed
            logger.debug(f"Extracting frame from video: {video_url}")
            
            # Use ffmpeg to extract a single frame
            # -ss 4: seek to 4 seconds
            # -i: input URL
            # -vframes 1: extract 1 frame
            # -vf scale=256:-1: resize to 256px width
            # -q:v 2: high quality JPEG
            cmd = [
                'ffmpeg',
                '-ss', '4',  # Seek to 4 seconds
                '-i', video_url,
                '-vframes', '1',
                '-vf', 'scale=256:-1',
                '-q:v', '2',
                '-y',  # Overwrite
                str(cache_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,  # 60 second timeout for extraction
                text=True
            )
            
            if result.returncode == 0 and cache_path.exists():
                logger.debug(f"Extracted frame to: {cache_path}")
                return cache_path
            else:
                logger.error(f"ffmpeg failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Video frame extraction timed out for {video_url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting video frame: {e}")
            return None
    
    def _compute_darkness_metrics(self, image_path: Path) -> DarknessMetrics:
        """
        Compute darkness metrics from image
        
        Converts sRGB to linear and computes luminance Y = 0.2126R + 0.7152G + 0.0722B
        
        Args:
            image_path: Path to image file
            
        Returns:
            DarknessMetrics object
        """
        # Load and resize image for faster processing
        img = Image.open(image_path)
        
        # Resize if too large (max 512px on longest side)
        max_dim = max(img.size)
        if max_dim > 512:
            scale = 512 / max_dim
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get numpy array
        img_array = np.array(img, dtype=np.float32) / 255.0  # Normalize to [0, 1]
        
        # Convert sRGB to linear
        linear = self._srgb_to_linear(img_array)
        
        # Compute luminance Y = 0.2126R + 0.7152G + 0.0722B (ITU-R BT.709)
        luminance = (0.2126 * linear[:, :, 0] + 
                    0.7152 * linear[:, :, 1] + 
                    0.0722 * linear[:, :, 2])
        
        # Compute metrics
        median_y = float(np.median(luminance))
        p25_y = float(np.percentile(luminance, 25))
        p75_y = float(np.percentile(luminance, 75))
        mean_y = float(np.mean(luminance))
        dark_pixel_ratio = float(np.sum(luminance < self.NIGHT_DARK_LUMINANCE) / luminance.size)
        
        return DarknessMetrics(
            median_y=median_y,
            p25_y=p25_y,
            p75_y=p75_y,
            dark_pixel_ratio=dark_pixel_ratio,
            mean_y=mean_y
        )
    
    @staticmethod
    def _srgb_to_linear(srgb: np.ndarray) -> np.ndarray:
        """Convert sRGB values to linear RGB"""
        # sRGB to linear conversion
        # if sRGB <= 0.04045: linear = sRGB / 12.92
        # else: linear = ((sRGB + 0.055) / 1.055) ^ 2.4
        linear = np.where(
            srgb <= 0.04045,
            srgb / 12.92,
            np.power((srgb + 0.055) / 1.055, 2.4)
        )
        return linear
    
    def _apply_acceptance_rules(
        self, 
        metadata_category: str, 
        metrics: DarknessMetrics
    ) -> Tuple[bool, str]:
        """
        Apply acceptance rules based on metadata and metrics
        
        Returns:
            (accepted: bool, reason: str)
        """
        # Night/Dark acceptance criteria
        night_accepted = (
            metrics.median_y <= self.NIGHT_MEDIAN_THRESHOLD or
            (metrics.dark_pixel_ratio >= self.NIGHT_DARK_RATIO_THRESHOLD and 
             metrics.p75_y <= self.NIGHT_P75_THRESHOLD)
        )
        
        # Sunset acceptance criteria (stricter)
        sunset_accepted = (
            metrics.median_y <= self.SUNSET_MEDIAN_THRESHOLD and
            metrics.p25_y <= self.SUNSET_P25_THRESHOLD and
            metrics.dark_pixel_ratio >= self.SUNSET_DARK_RATIO_THRESHOLD
        )
        
        # Apply rules based on metadata category
        if metadata_category == 'night':
            if night_accepted:
                return True, f"Night video with dark metrics (median={metrics.median_y:.3f})"
            else:
                return False, f"Night keyword but too bright (median={metrics.median_y:.3f})"
        
        elif metadata_category == 'sunset':
            if sunset_accepted:
                return True, f"Dark-ish sunset accepted (median={metrics.median_y:.3f})"
            else:
                return False, f"Sunset too bright (median={metrics.median_y:.3f})"
        
        elif metadata_category == 'day':
            # Day videos need very strict criteria
            if night_accepted and metrics.median_y <= 0.15:
                return True, f"Day keyword but extremely dark (median={metrics.median_y:.3f})"
            else:
                return False, f"Day keyword, rejected (median={metrics.median_y:.3f})"
        
        else:  # neutral
            if night_accepted:
                return True, f"Neutral metadata but dark enough (median={metrics.median_y:.3f})"
            else:
                return False, f"Neutral metadata, not dark enough (median={metrics.median_y:.3f})"
    
    def cleanup_cache(self, max_age_days: int = 7):
        """Remove cache files older than max_age_days"""
        import time
        cutoff_time = time.time() - (max_age_days * 86400)
        
        removed = 0
        for cache_file in self.cache_dir.glob('*'):
            if cache_file.is_file() and cache_file.stat().st_mtime < cutoff_time:
                cache_file.unlink()
                removed += 1
        
        logger.info(f"Cleaned up {removed} old cache files")
