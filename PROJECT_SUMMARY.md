# Overflight Night Feed - Project Summary

**Version:** 1.0.0  
**Created:** January 2026  
**Status:** ✅ Production Ready

## 🎯 Project Overview

This project provides a production-grade pipeline that generates a filtered JSON feed containing **only night/dark aerial videos** for the Projectivy Overflight wallpaper plugin. It uses robust image analysis with luminance-based darkness classification rather than simple keyword matching.

## 📦 Deliverables

All required components have been created and are production-ready:

### Core Application Files

1. **`scripts/media_probe.py`** (520 lines)
   - Darkness analysis engine
   - Image acquisition (thumbnails + video frame extraction)
   - sRGB→linear conversion + luminance calculation
   - Classification logic with configurable thresholds
   - Caching system with automatic cleanup

2. **`scripts/build_night_json.py`** (350 lines)
   - Main pipeline orchestrator
   - Concurrent processing with ThreadPoolExecutor
   - Upstream JSON fetching with retries
   - Report generation (CSV + JSON)
   - CLI interface with comprehensive options
   - Dry-run mode for testing

### Infrastructure Files

3. **`.github/workflows/update.yml`**
   - Daily scheduled execution (3 AM UTC)
   - Manual trigger support
   - FFmpeg installation
   - Automated commit + push
   - Artifact upload for reports
   - Loop prevention (ignores bot commits)

4. **`requirements.txt`**
   - Python dependencies with version constraints
   - Core: requests, Pillow, numpy, tqdm
   - All dependencies available on PyPI

### Configuration Files

5. **`config.example.py`**
   - Template for user customization
   - All tunable parameters documented
   - Threshold values with explanations

6. **`.gitignore`**
   - Excludes cache, reports, Python artifacts
   - Preserves important files

7. **`LICENSE`** (MIT)
   - Open source friendly
   - Commercial use allowed

### Documentation

8. **`README.md`** (Comprehensive)
   - Feature overview
   - How classification works (detailed)
   - Quick start guide
   - Local installation instructions
   - GitHub Actions setup
   - Configuration guide
   - Troubleshooting section
   - Testing instructions

9. **`SETUP.md`** (Step-by-step)
   - Prerequisites installation
   - Clone and install
   - Local testing
   - GitHub repository creation
   - Push and configure
   - Overflight configuration
   - Verification steps

10. **`ASSUMPTIONS.md`** (Design rationale)
    - Upstream format assumptions
    - Classification logic reasoning
    - Threshold selection justification
    - Error handling philosophy
    - Known limitations
    - Future improvements

11. **`DEPLOYMENT_CHECKLIST.md`**
    - Complete setup checklist
    - Pre-deployment verification
    - Testing steps
    - GitHub Actions configuration
    - Success criteria
    - Maintenance plan

### Sample/Test Files

12. **`night.json`** (Sample output)
    - 5 example night videos
    - Demonstrates output format
    - Ready to replace with real data

13. **`test_pipeline.py`**
    - Quick verification script
    - Tests with 5 items
    - Generates report
    - User-friendly output

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│          build_night_json.py (Main)             │
│  - Fetches upstream JSON                        │
│  - Orchestrates concurrent processing           │
│  - Writes filtered output                       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│           media_probe.py (Core)                 │
│  ┌─────────────────────────────────────────┐   │
│  │ 1. Metadata Classification              │   │
│  │    - Scans title/location for keywords  │   │
│  │    - Categories: night/sunset/day       │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ 2. Image Acquisition                    │   │
│  │    - Download thumbnail if exists       │   │
│  │    - Extract video frame otherwise      │   │
│  │    - Cache with SHA256 URL hash         │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ 3. Darkness Analysis                    │   │
│  │    - sRGB → linear conversion           │   │
│  │    - Luminance: Y = 0.2126R + ...       │   │
│  │    - Compute metrics (median, p25, p75) │   │
│  │    - Calculate dark pixel ratio         │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ 4. Accept/Reject Decision               │   │
│  │    - Apply threshold rules              │   │
│  │    - Generate reason string             │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              Outputs                             │
│  - night.json (filtered feed)                   │
│  - analysis_report.csv (metrics)                │
│  - analysis_report.json (structured)            │
└─────────────────────────────────────────────────┘
```

## 🔬 Classification Algorithm

### Metadata Gating
- **Night**: `night`, `twilight`, `dusk`, `evening`, `aurora`
- **Sunset**: `sunset` (requires darkness check)
- **Day**: `day`, `noon`, `sunrise`, `morning` (strict check)

### Luminance Metrics (ITU-R BT.709)
```python
Y = 0.2126 * R_linear + 0.7152 * G_linear + 0.0722 * B_linear

median_Y = median(all_pixels)
p25_Y = 25th_percentile(all_pixels)
p75_Y = 75th_percentile(all_pixels)
dark_ratio = count(Y < 0.18) / total_pixels
```

### Acceptance Rules

**Night/Dark:**
```python
accepted = (median_Y <= 0.22) OR
           (dark_ratio >= 0.65 AND p75_Y <= 0.35)
```

**Sunset (stricter):**
```python
accepted = (median_Y <= 0.28) AND
           (p25_Y <= 0.14) AND
           (dark_ratio >= 0.55)
```

## 🚀 Usage Examples

### Basic Usage
```bash
cd scripts
python build_night_json.py
```

### Testing with Limited Items
```bash
python build_night_json.py --max-items 10 --dry-run
```

### Full Run with Reports
```bash
python build_night_json.py --write-report --verbose
```

### Custom Configuration
```bash
python build_night_json.py \
  --upstream-url https://custom.com/videos.json \
  --output ../custom_night.json \
  --max-workers 12
```

## 📊 Expected Performance

For typical 100-item feed:
- **With thumbnails**: 2-3 minutes
- **Without thumbnails**: 5-10 minutes (FFmpeg extraction)
- **With cache hits**: ~1 minute

Scales linearly with concurrent processing (8 workers default).

## ✅ Quality Assurance

### Code Quality
- ✅ Comprehensive error handling (try-except blocks)
- ✅ Type hints throughout
- ✅ Docstrings for all functions/classes
- ✅ Logging at appropriate levels
- ✅ Progress bars for user feedback

### Robustness
- ✅ Retries with exponential backoff
- ✅ Request timeouts
- ✅ Graceful degradation (fail-closed)
- ✅ Cache management
- ✅ Deterministic output

### Testing
- ✅ Test script included (`test_pipeline.py`)
- ✅ Dry-run mode for safe testing
- ✅ Report generation for verification
- ✅ GitHub Actions serves as integration test

### Documentation
- ✅ README with examples
- ✅ Setup guide (step-by-step)
- ✅ Design rationale document
- ✅ Deployment checklist
- ✅ Code comments and docstrings

## 🔧 Customization Points

Users can customize:

1. **Darkness thresholds** (`media_probe.py`)
   - Adjust acceptance criteria
   - Tune for local preferences

2. **Upstream URL** (command line or `config.example.py`)
   - Use different video source

3. **Update frequency** (`.github/workflows/update.yml`)
   - Change from daily to custom schedule

4. **Concurrency** (command line)
   - Adjust worker count based on resources

5. **Cache settings** (`media_probe.py`)
   - Change cache location
   - Adjust expiry time

## 📈 Monitoring

### GitHub Actions
- Daily runs visible in Actions tab
- Email notifications on failures
- Downloadable artifacts (reports)
- Commit history shows changes

### Analysis Reports
- CSV format for spreadsheet analysis
- JSON format for programmatic access
- Includes all metrics for tuning

### Logs
- Structured logging (timestamp, level, message)
- Verbose mode for debugging
- Progress bars for long operations

## 🎓 Learning Resources

The project demonstrates:
- **Computer Vision**: Luminance analysis, color space conversion
- **Concurrent Programming**: ThreadPoolExecutor, futures
- **API Design**: Clean separation of concerns
- **CI/CD**: GitHub Actions automation
- **Documentation**: Multi-level documentation strategy

## 🔮 Future Enhancements

Potential improvements identified:
1. Multi-frame analysis (sample 3-5 frames)
2. ML/CNN classification
3. Scene detection integration
4. Adaptive thresholds by location
5. Confidence scoring (not just binary)
6. Web UI for threshold tuning

## 📝 Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `media_probe.py` | 520 | Core darkness analysis |
| `build_night_json.py` | 350 | Main pipeline |
| `update.yml` | 60 | GitHub Actions workflow |
| `README.md` | 400+ | User documentation |
| `SETUP.md` | 300+ | Setup guide |
| `ASSUMPTIONS.md` | 400+ | Design rationale |
| `DEPLOYMENT_CHECKLIST.md` | 150+ | Deployment guide |
| `requirements.txt` | 10 | Dependencies |
| `config.example.py` | 30 | Configuration template |
| `test_pipeline.py` | 60 | Quick test script |
| **Total** | **~2,300** | **Complete solution** |

## 🎉 Success Metrics

This project is successful when:
- ✅ Generates accurate night-only feed
- ✅ Runs automatically without intervention
- ✅ Users can customize to preferences
- ✅ Documentation enables self-service setup
- ✅ Code is maintainable and extensible

## 🙏 Credits

- **ITU-R BT.709**: Luminance calculation standard
- **FFmpeg**: Video frame extraction
- **GitHub Actions**: Automation platform
- **Projectivy Overflight**: Original video feed concept

---

**Ready for deployment!** 🚀

Follow `SETUP.md` for step-by-step instructions.
