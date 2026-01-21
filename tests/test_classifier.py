"""
Regression Tests for Night Feed Classifier

Tests known failure cases that MUST be rejected:
- Great Wall: neutral with high p75 (0.386)
- Silhouette: neutral with high p75 (0.531)
- Ocean: neutral with high p75 (0.494)
- Caribbean Day: day keyword with high brightness

These tests ensure the daylight veto and stricter acceptance rules work correctly.
"""

import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from media_probe import MediaProbe, DarknessMetrics, check_classification


class TestDaylightVeto:
    """Test the daylight veto system"""
    
    @pytest.fixture
    def probe(self):
        return MediaProbe()
    
    def test_veto_bright_pixel_ratio(self, probe):
        """Veto should trigger when bright_pixel_ratio >= 0.10"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.30,
            p90_y=0.40,
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.12,  # Over veto threshold
            mid_bright_ratio=0.15,
            low_sat_bright_ratio=0.02
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto, "Should trigger veto for bright_pixel_ratio >= 0.10"
        assert "bright_pixel_ratio" in reason
    
    def test_veto_mid_bright_ratio(self, probe):
        """Veto should trigger when mid_bright_ratio >= 0.25"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.30,
            p90_y=0.40,
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.05,
            mid_bright_ratio=0.28,  # Over veto threshold
            low_sat_bright_ratio=0.02
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto, "Should trigger veto for mid_bright_ratio >= 0.25"
        assert "mid_bright_ratio" in reason
    
    def test_veto_p75(self, probe):
        """Veto should trigger when p75_y >= 0.40"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.42,  # Over veto threshold
            p90_y=0.50,
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.05,
            mid_bright_ratio=0.15,
            low_sat_bright_ratio=0.02
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto, "Should trigger veto for p75_y >= 0.40"
        assert "p75_y" in reason
    
    def test_veto_p90(self, probe):
        """Veto should trigger when p90_y >= 0.55"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.35,
            p90_y=0.58,  # Over veto threshold
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.05,
            mid_bright_ratio=0.15,
            low_sat_bright_ratio=0.02
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto, "Should trigger veto for p90_y >= 0.55"
        assert "p90_y" in reason
    
    def test_veto_low_sat_bright(self, probe):
        """Veto should trigger when low_sat_bright_ratio >= 0.06"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.30,
            p90_y=0.40,
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.05,
            mid_bright_ratio=0.15,
            low_sat_bright_ratio=0.08  # Over veto threshold (sky-like)
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto, "Should trigger veto for low_sat_bright_ratio >= 0.06"
        assert "low_sat_bright_ratio" in reason
    
    def test_no_veto_dark_video(self, probe):
        """No veto for genuinely dark videos"""
        metrics = DarknessMetrics(
            median_y=0.08,
            p25_y=0.02,
            p75_y=0.18,
            p90_y=0.28,
            dark_pixel_ratio=0.85,
            mean_y=0.10,
            bright_pixel_ratio=0.01,
            mid_bright_ratio=0.05,
            low_sat_bright_ratio=0.01
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert not veto, "Should not trigger veto for genuinely dark video"


class TestKnownFailureCases:
    """Test that known failure cases are now correctly rejected"""
    
    def test_great_wall_like_metrics(self):
        """
        Great Wall scenario: neutral with low median but high p75
        Original: median=0.180, p75=0.386 -> was ACCEPTED (bug)
        Now: should be REJECTED by daylight veto (p75 >= 0.40) or neutral rules (p75 > 0.32)
        """
        metrics = DarknessMetrics(
            median_y=0.180,
            p25_y=0.100,
            p75_y=0.386,  # High - bright sky content
            p90_y=0.50,
            dark_pixel_ratio=0.55,
            mean_y=0.22,
            bright_pixel_ratio=0.08,
            mid_bright_ratio=0.22,
            low_sat_bright_ratio=0.04
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'neutral')
        assert not accepted, f"Great Wall-like metrics should be REJECTED (rule: {rule})"
    
    def test_silhouette_like_metrics(self):
        """
        Silhouette scenario: neutral with very high p75
        Original: median=0.138, p75=0.531 -> was ACCEPTED (bug)
        Now: should be REJECTED by daylight veto (p75 >= 0.40)
        """
        metrics = DarknessMetrics(
            median_y=0.138,
            p25_y=0.050,
            p75_y=0.531,  # Very high - bright sky
            p90_y=0.65,
            dark_pixel_ratio=0.60,
            mean_y=0.25,
            bright_pixel_ratio=0.15,
            mid_bright_ratio=0.30,
            low_sat_bright_ratio=0.10
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'neutral')
        assert not accepted, f"Silhouette-like metrics should be REJECTED (rule: {rule})"
        assert daylight_veto, "Should be rejected by daylight veto"
    
    def test_ocean_like_metrics(self):
        """
        Ocean scenario: neutral with high p75
        Original: median=0.165, p75=0.494 -> was ACCEPTED (bug)
        Now: should be REJECTED by daylight veto (p75 >= 0.40)
        """
        metrics = DarknessMetrics(
            median_y=0.165,
            p25_y=0.080,
            p75_y=0.494,  # High - bright ocean/sky
            p90_y=0.60,
            dark_pixel_ratio=0.50,
            mean_y=0.24,
            bright_pixel_ratio=0.12,
            mid_bright_ratio=0.28,
            low_sat_bright_ratio=0.08
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'neutral')
        assert not accepted, f"Ocean-like metrics should be REJECTED (rule: {rule})"
        assert daylight_veto, "Should be rejected by daylight veto"
    
    def test_caribbean_day_like_metrics(self):
        """
        Caribbean Day scenario: day keyword should require near-night profile
        Original: median=0.148 -> was ACCEPTED (bug)
        Now: day keyword must meet strict thresholds
        """
        metrics = DarknessMetrics(
            median_y=0.148,
            p25_y=0.080,
            p75_y=0.35,
            p90_y=0.48,
            dark_pixel_ratio=0.58,
            mean_y=0.20,
            bright_pixel_ratio=0.06,
            mid_bright_ratio=0.18,
            low_sat_bright_ratio=0.03
        )
        
        # day_strong requires: median<=0.12, p75<=0.28, p90<=0.36, bright<=0.03, mid_bright<=0.12
        accepted, daylight_veto, rule = check_classification(metrics, 'day_strong')
        assert not accepted, f"Caribbean Day-like metrics should be REJECTED (rule: {rule})"


class TestAcceptanceRules:
    """Test category-specific acceptance rules"""
    
    def test_night_strong_accepts_dark(self):
        """Night keyword videos with dark metrics should be accepted"""
        metrics = DarknessMetrics(
            median_y=0.12,
            p25_y=0.04,
            p75_y=0.25,
            p90_y=0.35,
            dark_pixel_ratio=0.80,
            mean_y=0.15,
            bright_pixel_ratio=0.02,
            mid_bright_ratio=0.08,
            low_sat_bright_ratio=0.01
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'night_strong')
        assert accepted, f"Dark night video should be accepted (rule: {rule})"
        assert rule == "night_strong_pass"
    
    def test_neutral_extra_restrictions(self):
        """Neutral content must pass additional p75, p90, mid_bright checks"""
        # This would pass basic night_ok but should fail neutral's extra checks
        metrics = DarknessMetrics(
            median_y=0.18,  # Passes NIGHT_MEDIAN_THRESHOLD (0.22)
            p25_y=0.08,
            p75_y=0.35,  # Fails NEUTRAL_P75_CAP (0.32)
            p90_y=0.42,
            dark_pixel_ratio=0.65,
            mean_y=0.20,
            bright_pixel_ratio=0.04,
            mid_bright_ratio=0.12,
            low_sat_bright_ratio=0.02
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'neutral')
        assert not accepted, f"Neutral with high p75 should be rejected (rule: {rule})"
        assert "p75" in rule, f"Should mention p75 in rejection rule: {rule}"
    
    def test_sunset_strict_thresholds(self):
        """Sunset videos have stricter combined requirements"""
        # Bright sunset - should fail
        metrics = DarknessMetrics(
            median_y=0.28,  # Over SUNSET_MEDIAN_THRESHOLD (0.26)
            p25_y=0.15,
            p75_y=0.38,
            p90_y=0.50,
            dark_pixel_ratio=0.45,
            mean_y=0.30,
            bright_pixel_ratio=0.08,
            mid_bright_ratio=0.20,
            low_sat_bright_ratio=0.04
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'sunset')
        assert not accepted, "Bright sunset should be rejected"
    
    def test_sunset_dark_enough(self):
        """Dark enough sunset should be accepted"""
        metrics = DarknessMetrics(
            median_y=0.20,
            p25_y=0.10,
            p75_y=0.32,
            p90_y=0.42,
            dark_pixel_ratio=0.60,
            mean_y=0.22,
            bright_pixel_ratio=0.04,
            mid_bright_ratio=0.15,
            low_sat_bright_ratio=0.02
        )
        
        accepted, daylight_veto, rule = check_classification(metrics, 'sunset')
        assert accepted, f"Dark sunset should be accepted (rule: {rule})"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.fixture
    def probe(self):
        return MediaProbe()
    
    def test_exactly_at_veto_threshold(self, probe):
        """Test behavior at exact veto thresholds"""
        # p75 exactly at threshold
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.40,  # Exactly at VETO_P75_Y
            p90_y=0.45,
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.05,
            mid_bright_ratio=0.15,
            low_sat_bright_ratio=0.02
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto, "Should veto at exactly the threshold (>= comparison)"
    
    def test_just_below_veto_threshold(self, probe):
        """Test behavior just below veto thresholds"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.399,  # Just below VETO_P75_Y
            p90_y=0.549,  # Just below VETO_P90_Y
            dark_pixel_ratio=0.70,
            mean_y=0.20,
            bright_pixel_ratio=0.099,  # Just below 0.10
            mid_bright_ratio=0.249,  # Just below 0.25
            low_sat_bright_ratio=0.059  # Just below 0.06
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert not veto, "Should not veto just below all thresholds"
    
    def test_multiple_veto_conditions(self, probe):
        """When multiple veto conditions are met, first one is reported"""
        metrics = DarknessMetrics(
            median_y=0.15,
            p25_y=0.05,
            p75_y=0.50,  # Veto 1
            p90_y=0.65,  # Veto 2
            dark_pixel_ratio=0.30,
            mean_y=0.30,
            bright_pixel_ratio=0.20,  # Veto 3 - checked first
            mid_bright_ratio=0.40,  # Veto 4
            low_sat_bright_ratio=0.10  # Veto 5
        )
        
        veto, reason = probe._check_daylight_veto(metrics)
        assert veto
        assert "bright_pixel_ratio" in reason, "First veto condition should be reported"


class TestBorderCropping:
    """Test border detection and cropping"""
    
    @pytest.fixture
    def probe(self):
        return MediaProbe()
    
    def test_border_detection_logic(self, probe):
        """Test that border cropping logic is correct"""
        import numpy as np
        
        # Create image with black borders
        h, w = 100, 160
        img = np.ones((h, w, 3), dtype=np.float32) * 0.5  # Mid-gray
        
        # Add 10-pixel black borders
        img[:10, :, :] = 0.01  # Top border
        img[-10:, :, :] = 0.01  # Bottom border
        img[:, :5, :] = 0.01   # Left border
        img[:, -5:, :] = 0.01  # Right border
        
        cropped, crop_info = probe._crop_borders(img)
        
        # Should detect borders
        assert crop_info['top'] > 0, "Should detect top border"
        assert crop_info['bottom'] > 0, "Should detect bottom border"
        assert crop_info['left'] > 0, "Should detect left border"
        assert crop_info['right'] > 0, "Should detect right border"
        
        # Cropped image should be smaller
        assert cropped.shape[0] < h, "Height should be reduced"
        assert cropped.shape[1] < w, "Width should be reduced"
    
    def test_no_false_border_detection(self, probe):
        """Dark content should not be mistaken for borders"""
        import numpy as np
        
        # Create dark but not black image (no borders)
        h, w = 100, 160
        img = np.ones((h, w, 3), dtype=np.float32) * 0.15  # Dark gray, above threshold
        
        cropped, crop_info = probe._crop_borders(img)
        
        # Should not detect borders
        assert crop_info['top'] == 0, "Should not detect false top border"
        assert crop_info['bottom'] == 0, "Should not detect false bottom border"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
