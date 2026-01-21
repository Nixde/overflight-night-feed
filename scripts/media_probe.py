"""
Media Probe Module - Darkness Classification for Aerial Videos
Analyzes images and video frames to determine darkness levels.

FIXES IMPLEMENTED (v2.0):
- Multi-frame video analysis (3 frames at 3s, 12s, 24s)
- Border/letterbox detection and cropping
- Daylight veto system with bright pixel detection
- HSV-based sky detection (low_sat_bright_ratio)
- Stricter acceptance rules for neutral/day content
- Enhanced metrics: p90_Y, bright_pixel_ratio, mid_bright_ratio
"""

import hashlib
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

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
    p90_y: float  # NEW: 90th percentile
    dark_pixel_ratio: float
    mean_y: float
    bright_pixel_ratio: float  # NEW: fraction with Y > 0.65
    mid_bright_ratio: float    # NEW: fraction with Y > 0.45
    low_sat_bright_ratio: float  # NEW: HSV-based sky detection
    
    # Border crop info
    border_crop: Dict[str, int] = field(default_factory=dict)
    
    # Multi-frame info
    frames_analyzed: int = 1
    timestamps_used: List[float] = field(default_factory=list)
    
    def __str__(self):
        return (f"DarknessMetrics(median={self.median_y:.3f}, "
                f"p25={self.p25_y:.3f}, p75={self.p75_y:.3f}, p90={self.p90_y:.3f}, "
                f"dark_ratio={self.dark_pixel_ratio:.3f}, bright_ratio={self.bright_pixel_ratio:.3f}, "
                f"mid_bright={self.mid_bright_ratio:.3f}, low_sat_bright={self.low_sat_bright_ratio:.3f})")


@dataclass
class ClassificationResult:
    """Result of darkness classification"""
    accepted: bool
    reason: str
    metrics: Optional[DarknessMetrics]
    metadata_category: str  # 'night_strong', 'sunset', 'day_strong', 'neutral'
    daylight_veto: bool = False
    decision_rule: str = ""
    media_source: str = ""  # thumbnail key or video URL used


class MediaProbe:
    """Analyzes media for darkness classification with daylight veto"""
    
    # ===== THRESHOLDS =====
    
    # Base darkness threshold
    NIGHT_DARK_LUMINANCE = 0.18  # What counts as "dark pixel"
    
    # Daylight veto thresholds (if ANY is exceeded, reject)
    VETO_BRIGHT_PIXEL_RATIO = 0.10    # >10% pixels with Y > 0.65
    VETO_MID_BRIGHT_RATIO = 0.25      # >25% pixels with Y > 0.45
    VETO_P75_Y = 0.40                  # 75th percentile too bright
    VETO_P90_Y = 0.55                  # 90th percentile too bright
    VETO_LOW_SAT_BRIGHT = 0.06        # >6% sky-like bright pixels
    
    # Night/dark acceptance (must ALSO pass daylight veto)
    NIGHT_MEDIAN_THRESHOLD = 0.22
    NIGHT_DARK_RATIO_THRESHOLD = 0.65
    NIGHT_P75_THRESHOLD = 0.33        # Tightened from 0.35
    
    # Sunset acceptance (stricter)
    SUNSET_MEDIAN_THRESHOLD = 0.26
    SUNSET_P25_THRESHOLD = 0.14
    SUNSET_DARK_RATIO_THRESHOLD = 0.55
    SUNSET_P75_THRESHOLD = 0.36
    
    # Neutral content: extra restrictions beyond night_ok
    NEUTRAL_P75_CAP = 0.32
    NEUTRAL_P90_CAP = 0.45
    NEUTRAL_MID_BRIGHT_CAP = 0.18
    
    # Day keyword: near-night requirements
    DAY_MEDIAN_CAP = 0.12
    DAY_P75_CAP = 0.28
    DAY_P90_CAP = 0.36
    DAY_BRIGHT_RATIO_CAP = 0.03
    DAY_MID_BRIGHT_CAP = 0.12
    
    # Border detection
    BORDER_LUMINANCE_THRESHOLD = 0.03  # Mean Y below this = border
    BORDER_MAX_CROP_RATIO = 0.25       # Don't crop more than 25% per side
    
    # Multi-frame extraction timestamps (seconds)
    MULTI_FRAME_TIMESTAMPS = [3.0, 12.0, 24.0]
    
    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 30,
                 save_debug_frames: int = 0):
        """
        Initialize MediaProbe
        
        Args:
            cache_dir: Directory for caching downloaded media
            timeout: Request timeout in seconds
            save_debug_frames: If > 0, save this many debug frames per item
        """
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "overflight_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.save_debug_frames = save_debug_frames
        self.debug_frames_dir = None
        
        if save_debug_frames > 0:
            self.debug_frames_dir = Path("reports/debug_frames")
            self.debug_frames_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
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
        title = item.get('title', '').lower()
        location = item.get('location', '').lower()
        combined_text = f"{title} {location}"
        
        metadata_category = self._classify_metadata(combined_text)
        logger.info(f"Item '{item.get('title', 'unknown')}' - metadata: {metadata_category}")
        
        try:
            # Get representative image(s) and media source info
            image_paths, media_source, timestamps = self._get_representative_images(item)
            
            if not image_paths:
                logger.warning(f"Could not get image for '{item.get('title', 'unknown')}'")
                return ClassificationResult(
                    accepted=False,
                    reason="Failed to obtain image for analysis",
                    metrics=None,
                    metadata_category=metadata_category,
                    daylight_veto=False,
                    decision_rule="no_media",
                    media_source="none"
                )
            
            # Compute metrics (with multi-frame worst-case analysis)
            metrics = self._compute_combined_metrics(image_paths, timestamps, item.get('title', 'unknown'))
            logger.info(f"Metrics: {metrics}")
            
            # Check daylight veto FIRST
            daylight_veto, veto_reason = self._check_daylight_veto(metrics)
            
            if daylight_veto:
                logger.info(f"DAYLIGHT VETO: {veto_reason}")
                return ClassificationResult(
                    accepted=False,
                    reason=f"Daylight veto: {veto_reason}",
                    metrics=metrics,
                    metadata_category=metadata_category,
                    daylight_veto=True,
                    decision_rule=f"daylight_veto:{veto_reason}",
                    media_source=media_source
                )
            
            # Apply category-specific acceptance rules
            accepted, reason, decision_rule = self._apply_acceptance_rules(metadata_category, metrics)
            
            return ClassificationResult(
                accepted=accepted,
                reason=reason,
                metrics=metrics,
                metadata_category=metadata_category,
                daylight_veto=False,
                decision_rule=decision_rule,
                media_source=media_source
            )
            
        except Exception as e:
            logger.error(f"Error classifying item: {e}", exc_info=True)
            return ClassificationResult(
                accepted=False,
                reason=f"Analysis error: {str(e)}",
                metrics=None,
                metadata_category=metadata_category,
                daylight_veto=False,
                decision_rule="error",
                media_source="error"
            )
    
    def _classify_metadata(self, text: str) -> str:
        """Classify based on metadata keywords"""
        night_keywords = ['night', 'twilight', 'dusk', 'evening', 'aurora']
        sunset_keywords = ['sunset']
        day_keywords = ['day', 'noon', 'sunrise', 'morning']
        
        if any(kw in text for kw in night_keywords):
            return 'night_strong'
        elif any(kw in text for kw in sunset_keywords):
            return 'sunset'
        elif any(kw in text for kw in day_keywords):
            return 'day_strong'
        else:
            return 'neutral'
    
    def _get_representative_images(self, item: dict) -> Tuple[List[Path], str, List[float]]:
        """
        Get representative image(s) from item (thumbnail or extracted frames)
        
        Returns:
            (list of image paths, media source description, timestamps used)
        """
        # Try to find thumbnail URL
        thumbnail_keys = ['url_img', 'image', 'thumbnail', 'thumb', 'poster']
        thumbnail_url = None
        thumbnail_key_used = None
        
        for key in thumbnail_keys:
            if key in item and item[key]:
                thumbnail_url = item[key]
                thumbnail_key_used = key
                break
        
        if thumbnail_url:
            logger.debug(f"Using thumbnail URL ({thumbnail_key_used}): {thumbnail_url}")
            image_path = self._download_image(thumbnail_url)
            if image_path:
                return [image_path], f"thumbnail:{thumbnail_key_used}", [0.0]
        
        # No thumbnail - extract multiple frames from video
        video_url = self._get_best_video_url(item)
        if video_url:
            logger.debug(f"Extracting frames from video: {video_url}")
            frames, timestamps = self._extract_multiple_frames(video_url)
            if frames:
                return frames, f"video:{video_url[:80]}...", timestamps
        
        logger.warning("No thumbnail or video URL found")
        return [], "none", []
    
    def _get_best_video_url(self, item: dict) -> Optional[str]:
        """Get best video URL (prefer 1080p over 4K for speed)"""
        priority_keys = ['url_1080p', 'url_720p', 'url_4k', 'url_2160p']
        
        for key in priority_keys:
            if key in item and item[key]:
                return item[key]
        
        for key, value in item.items():
            if key.startswith('url_') and value and isinstance(value, str):
                if value.startswith('http'):
                    return value
        
        return None
    
    def _download_image(self, url: str) -> Optional[Path]:
        """Download image with caching"""
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        cache_path = self.cache_dir / f"{cache_key}.jpg"
        
        if cache_path.exists():
            logger.debug(f"Using cached image: {cache_path}")
            return cache_path
        
        try:
            logger.debug(f"Downloading image: {url}")
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"Saved to cache: {cache_path}")
            return cache_path
            
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def _extract_multiple_frames(self, video_url: str) -> Tuple[List[Path], List[float]]:
        """
        Extract multiple frames from video for worst-case analysis
        
        Returns:
            (list of frame paths, list of timestamps)
        """
        # Check ffmpeg availability
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("ffmpeg not available")
            return [], []
        
        frames = []
        successful_timestamps = []
        
        for ts in self.MULTI_FRAME_TIMESTAMPS:
            cache_key = hashlib.sha256(f"{video_url}@{ts}".encode()).hexdigest()
            cache_path = self.cache_dir / f"{cache_key}_frame_{ts:.0f}s.jpg"
            
            if cache_path.exists():
                frames.append(cache_path)
                successful_timestamps.append(ts)
                continue
            
            try:
                cmd = [
                    'ffmpeg',
                    '-ss', str(ts),
                    '-i', video_url,
                    '-vframes', '1',
                    '-vf', 'scale=384:-1',  # Slightly larger for better analysis
                    '-q:v', '2',
                    '-y',
                    str(cache_path)
                ]
                
                result = subprocess.run(
                    cmd, capture_output=True, timeout=45, text=True
                )
                
                if result.returncode == 0 and cache_path.exists():
                    frames.append(cache_path)
                    successful_timestamps.append(ts)
                else:
                    logger.warning(f"Failed to extract frame at {ts}s")
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout extracting frame at {ts}s")
            except Exception as e:
                logger.warning(f"Error extracting frame at {ts}s: {e}")
        
        if not frames:
            # Fallback to single frame at 4s
            cache_key = hashlib.sha256(f"{video_url}@4".encode()).hexdigest()
            cache_path = self.cache_dir / f"{cache_key}_frame_4s.jpg"
            
            if cache_path.exists():
                return [cache_path], [4.0]
            
            try:
                cmd = [
                    'ffmpeg', '-ss', '4', '-i', video_url,
                    '-vframes', '1', '-vf', 'scale=384:-1',
                    '-q:v', '2', '-y', str(cache_path)
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=60, text=True)
                if result.returncode == 0 and cache_path.exists():
                    return [cache_path], [4.0]
            except Exception:
                pass
        
        return frames, successful_timestamps
    
    def _compute_combined_metrics(self, image_paths: List[Path], timestamps: List[float],
                                   item_title: str) -> DarknessMetrics:
        """
        Compute combined metrics using worst-case (brightest) frame for conservative filtering
        """
        all_metrics = []
        
        for i, image_path in enumerate(image_paths):
            metrics = self._compute_single_frame_metrics(image_path, item_title, i)
            all_metrics.append(metrics)
        
        if len(all_metrics) == 1:
            m = all_metrics[0]
            m.frames_analyzed = 1
            m.timestamps_used = timestamps
            return m
        
        # WORST-CASE combination (max brightness = most likely to trigger rejection)
        combined = DarknessMetrics(
            median_y=max(m.median_y for m in all_metrics),
            p25_y=max(m.p25_y for m in all_metrics),
            p75_y=max(m.p75_y for m in all_metrics),
            p90_y=max(m.p90_y for m in all_metrics),
            dark_pixel_ratio=min(m.dark_pixel_ratio for m in all_metrics),  # Min = worst
            mean_y=max(m.mean_y for m in all_metrics),
            bright_pixel_ratio=max(m.bright_pixel_ratio for m in all_metrics),
            mid_bright_ratio=max(m.mid_bright_ratio for m in all_metrics),
            low_sat_bright_ratio=max(m.low_sat_bright_ratio for m in all_metrics),
            border_crop=all_metrics[0].border_crop,  # Use first frame's crop info
            frames_analyzed=len(all_metrics),
            timestamps_used=timestamps
        )
        
        logger.debug(f"Combined {len(all_metrics)} frames using worst-case metrics")
        return combined
    
    def _compute_single_frame_metrics(self, image_path: Path, item_title: str = "",
                                       frame_idx: int = 0) -> DarknessMetrics:
        """
        Compute darkness metrics from a single image with border cropping
        """
        img = Image.open(image_path)
        
        # Resize if too large
        max_dim = max(img.size)
        if max_dim > 512:
            scale = 512 / max_dim
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        # Detect and crop borders FIRST
        img_array, border_crop = self._crop_borders(img_array)
        
        # Save debug frame if requested
        if self.debug_frames_dir and self.save_debug_frames > 0:
            self._save_debug_frame(img_array, item_title, frame_idx)
        
        # Convert to linear RGB
        linear = self._srgb_to_linear(img_array)
        
        # Compute luminance
        luminance = (0.2126 * linear[:, :, 0] + 
                    0.7152 * linear[:, :, 1] + 
                    0.0722 * linear[:, :, 2])
        
        # Core metrics
        median_y = float(np.median(luminance))
        p25_y = float(np.percentile(luminance, 25))
        p75_y = float(np.percentile(luminance, 75))
        p90_y = float(np.percentile(luminance, 90))
        mean_y = float(np.mean(luminance))
        dark_pixel_ratio = float(np.sum(luminance < self.NIGHT_DARK_LUMINANCE) / luminance.size)
        
        # NEW metrics for daylight detection
        bright_pixel_ratio = float(np.sum(luminance > 0.65) / luminance.size)
        mid_bright_ratio = float(np.sum(luminance > 0.45) / luminance.size)
        
        # HSV-based sky detection
        low_sat_bright_ratio = self._compute_low_sat_bright_ratio(img_array)
        
        return DarknessMetrics(
            median_y=median_y,
            p25_y=p25_y,
            p75_y=p75_y,
            p90_y=p90_y,
            dark_pixel_ratio=dark_pixel_ratio,
            mean_y=mean_y,
            bright_pixel_ratio=bright_pixel_ratio,
            mid_bright_ratio=mid_bright_ratio,
            low_sat_bright_ratio=low_sat_bright_ratio,
            border_crop=border_crop
        )
    
    def _crop_borders(self, img_array: np.ndarray) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Detect and crop near-black borders/letterboxing
        
        Returns:
            (cropped image array, crop info dict)
        """
        h, w = img_array.shape[:2]
        max_crop_h = int(h * self.BORDER_MAX_CROP_RATIO)
        max_crop_w = int(w * self.BORDER_MAX_CROP_RATIO)
        
        # Quick luminance for border detection
        gray = 0.299 * img_array[:, :, 0] + 0.587 * img_array[:, :, 1] + 0.114 * img_array[:, :, 2]
        
        crop_top = 0
        crop_bottom = 0
        crop_left = 0
        crop_right = 0
        
        # Detect top border
        for i in range(max_crop_h):
            if np.mean(gray[i, :]) < self.BORDER_LUMINANCE_THRESHOLD:
                crop_top = i + 1
            else:
                break
        
        # Detect bottom border
        for i in range(max_crop_h):
            if np.mean(gray[h - 1 - i, :]) < self.BORDER_LUMINANCE_THRESHOLD:
                crop_bottom = i + 1
            else:
                break
        
        # Detect left border
        for i in range(max_crop_w):
            if np.mean(gray[:, i]) < self.BORDER_LUMINANCE_THRESHOLD:
                crop_left = i + 1
            else:
                break
        
        # Detect right border
        for i in range(max_crop_w):
            if np.mean(gray[:, w - 1 - i]) < self.BORDER_LUMINANCE_THRESHOLD:
                crop_right = i + 1
            else:
                break
        
        crop_info = {
            'top': crop_top,
            'bottom': crop_bottom,
            'left': crop_left,
            'right': crop_right
        }
        
        # Apply crop if any borders detected
        if any([crop_top, crop_bottom, crop_left, crop_right]):
            y1 = crop_top
            y2 = h - crop_bottom if crop_bottom > 0 else h
            x1 = crop_left
            x2 = w - crop_right if crop_right > 0 else w
            
            # Safety check
            if y2 > y1 and x2 > x1:
                img_array = img_array[y1:y2, x1:x2]
                logger.debug(f"Cropped borders: top={crop_top}, bottom={crop_bottom}, "
                           f"left={crop_left}, right={crop_right}")
        
        return img_array, crop_info
    
    def _compute_low_sat_bright_ratio(self, img_array: np.ndarray) -> float:
        """
        Compute fraction of pixels that are bright but low saturation (sky-like)
        Uses HSV: V > 0.65 AND S < 0.25
        """
        # Convert to HSV manually for speed
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
        
        v = np.maximum(np.maximum(r, g), b)  # Value
        c = v - np.minimum(np.minimum(r, g), b)  # Chroma
        
        # Saturation (avoid divide by zero)
        s = np.where(v > 0.001, c / v, 0)
        
        # Sky-like: bright (V > 0.65) but low saturation (S < 0.25)
        sky_mask = (v > 0.65) & (s < 0.25)
        
        return float(np.sum(sky_mask) / sky_mask.size)
    
    def _save_debug_frame(self, img_array: np.ndarray, item_title: str, frame_idx: int):
        """Save cropped frame for debugging"""
        if not self.debug_frames_dir:
            return
        
        safe_title = "".join(c if c.isalnum() or c in ' -_' else '_' for c in item_title)
        safe_title = safe_title[:50]
        
        img = Image.fromarray((img_array * 255).astype(np.uint8))
        path = self.debug_frames_dir / f"{safe_title}_frame{frame_idx}.jpg"
        img.save(path, quality=85)
        logger.debug(f"Saved debug frame: {path}")
    
    @staticmethod
    def _srgb_to_linear(srgb: np.ndarray) -> np.ndarray:
        """Convert sRGB values to linear RGB"""
        return np.where(
            srgb <= 0.04045,
            srgb / 12.92,
            np.power((srgb + 0.055) / 1.055, 2.4)
        )
    
    def _check_daylight_veto(self, metrics: DarknessMetrics) -> Tuple[bool, str]:
        """
        Check if daylight veto conditions are met
        
        Returns:
            (veto triggered, reason string)
        """
        if metrics.bright_pixel_ratio >= self.VETO_BRIGHT_PIXEL_RATIO:
            return True, f"bright_pixel_ratio={metrics.bright_pixel_ratio:.3f} >= {self.VETO_BRIGHT_PIXEL_RATIO}"
        
        if metrics.mid_bright_ratio >= self.VETO_MID_BRIGHT_RATIO:
            return True, f"mid_bright_ratio={metrics.mid_bright_ratio:.3f} >= {self.VETO_MID_BRIGHT_RATIO}"
        
        if metrics.p75_y >= self.VETO_P75_Y:
            return True, f"p75_y={metrics.p75_y:.3f} >= {self.VETO_P75_Y}"
        
        if metrics.p90_y >= self.VETO_P90_Y:
            return True, f"p90_y={metrics.p90_y:.3f} >= {self.VETO_P90_Y}"
        
        if metrics.low_sat_bright_ratio >= self.VETO_LOW_SAT_BRIGHT:
            return True, f"low_sat_bright_ratio={metrics.low_sat_bright_ratio:.3f} >= {self.VETO_LOW_SAT_BRIGHT}"
        
        return False, ""
    
    def _apply_acceptance_rules(
        self, 
        metadata_category: str, 
        metrics: DarknessMetrics
    ) -> Tuple[bool, str, str]:
        """
        Apply category-specific acceptance rules
        
        Returns:
            (accepted, reason, decision_rule)
        """
        # Base night/dark acceptance check
        night_ok = (
            metrics.median_y <= self.NIGHT_MEDIAN_THRESHOLD or
            (metrics.dark_pixel_ratio >= self.NIGHT_DARK_RATIO_THRESHOLD and 
             metrics.p75_y <= self.NIGHT_P75_THRESHOLD)
        )
        
        # Sunset acceptance (stricter)
        sunset_ok = (
            metrics.median_y <= self.SUNSET_MEDIAN_THRESHOLD and
            metrics.p25_y <= self.SUNSET_P25_THRESHOLD and
            metrics.dark_pixel_ratio >= self.SUNSET_DARK_RATIO_THRESHOLD and
            metrics.p75_y <= self.SUNSET_P75_THRESHOLD
        )
        
        # Apply rules based on metadata category
        if metadata_category == 'night_strong':
            if night_ok:
                return True, f"Night video accepted (median={metrics.median_y:.3f})", "night_strong_pass"
            else:
                return False, f"Night keyword but too bright (median={metrics.median_y:.3f})", "night_strong_fail"
        
        elif metadata_category == 'sunset':
            if sunset_ok:
                return True, f"Dark sunset accepted (median={metrics.median_y:.3f})", "sunset_pass"
            else:
                return False, f"Sunset too bright (median={metrics.median_y:.3f}, p75={metrics.p75_y:.3f})", "sunset_fail"
        
        elif metadata_category == 'day_strong':
            # Day items must meet near-night profile
            day_ok = (
                metrics.median_y <= self.DAY_MEDIAN_CAP and
                metrics.p75_y <= self.DAY_P75_CAP and
                metrics.p90_y <= self.DAY_P90_CAP and
                metrics.bright_pixel_ratio <= self.DAY_BRIGHT_RATIO_CAP and
                metrics.mid_bright_ratio <= self.DAY_MID_BRIGHT_CAP
            )
            
            if day_ok:
                return True, f"Day keyword but near-night profile (median={metrics.median_y:.3f})", "day_near_night_pass"
            else:
                reason_parts = []
                if metrics.median_y > self.DAY_MEDIAN_CAP:
                    reason_parts.append(f"median={metrics.median_y:.3f}>{self.DAY_MEDIAN_CAP}")
                if metrics.p75_y > self.DAY_P75_CAP:
                    reason_parts.append(f"p75={metrics.p75_y:.3f}>{self.DAY_P75_CAP}")
                if metrics.p90_y > self.DAY_P90_CAP:
                    reason_parts.append(f"p90={metrics.p90_y:.3f}>{self.DAY_P90_CAP}")
                if metrics.bright_pixel_ratio > self.DAY_BRIGHT_RATIO_CAP:
                    reason_parts.append(f"bright={metrics.bright_pixel_ratio:.3f}>{self.DAY_BRIGHT_RATIO_CAP}")
                if metrics.mid_bright_ratio > self.DAY_MID_BRIGHT_CAP:
                    reason_parts.append(f"mid_bright={metrics.mid_bright_ratio:.3f}>{self.DAY_MID_BRIGHT_CAP}")
                
                return False, f"Day keyword rejected: {', '.join(reason_parts)}", "day_reject"
        
        else:  # neutral
            # Neutral must pass night_ok PLUS additional restrictions
            if not night_ok:
                return False, f"Neutral too bright (median={metrics.median_y:.3f})", "neutral_bright_fail"
            
            # Additional restrictions for neutral content
            if metrics.p75_y > self.NEUTRAL_P75_CAP:
                return False, f"Neutral p75 too high ({metrics.p75_y:.3f} > {self.NEUTRAL_P75_CAP})", "neutral_p75_fail"
            
            if metrics.p90_y > self.NEUTRAL_P90_CAP:
                return False, f"Neutral p90 too high ({metrics.p90_y:.3f} > {self.NEUTRAL_P90_CAP})", "neutral_p90_fail"
            
            if metrics.mid_bright_ratio > self.NEUTRAL_MID_BRIGHT_CAP:
                return False, f"Neutral mid_bright too high ({metrics.mid_bright_ratio:.3f} > {self.NEUTRAL_MID_BRIGHT_CAP})", "neutral_mid_bright_fail"
            
            return True, f"Neutral dark enough (median={metrics.median_y:.3f}, p75={metrics.p75_y:.3f})", "neutral_pass"
    
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


# === REGRESSION TEST UTILITIES ===

def analyze_image_for_test(image_path: Path) -> DarknessMetrics:
    """Utility function for regression tests to analyze a single image"""
    probe = MediaProbe()
    return probe._compute_single_frame_metrics(image_path)


def check_classification(metrics: DarknessMetrics, metadata_category: str) -> Tuple[bool, bool, str]:
    """
    Utility for regression tests
    
    Returns:
        (accepted, daylight_veto, decision_rule)
    """
    probe = MediaProbe()
    
    daylight_veto, veto_reason = probe._check_daylight_veto(metrics)
    if daylight_veto:
        return False, True, f"daylight_veto:{veto_reason}"
    
    accepted, reason, rule = probe._apply_acceptance_rules(metadata_category, metrics)
    return accepted, False, rule
