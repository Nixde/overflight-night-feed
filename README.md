# Overflight Night Feed 🌙

A production-grade pipeline that generates a filtered JSON feed containing **only night/dark aerial videos** for the [Projectivy Overflight](https://github.com/projectivy/overflight) wallpaper plugin.

Uses robust image analysis with luminance-based darkness classification—not just keyword matching.

## 🌟 Features

- **Daylight Veto System**: Hard rejection of any video with bright sky content (v2.0)
- **Multi-frame Analysis**: Analyzes 3 frames per video (at 3s, 12s, 24s) using worst-case metrics
- **Border/Letterbox Detection**: Automatically crops black borders before analysis
- **HSV Sky Detection**: Detects low-saturation bright pixels (sky-like content)
- **Real darkness analysis**: Measures actual luminance from video frames/thumbnails using ITU-R BT.709 standards
- **Intelligent frame extraction**: Automatically extracts representative frames when thumbnails aren't available
- **Hybrid classification**: Combines metadata keywords with measured darkness metrics
- **Sunset filtering**: Includes only dark-ish sunsets based on configurable thresholds
- **Production-ready**: Concurrent processing, retries, timeouts, caching, and deterministic output
- **Auto-updating**: GitHub Actions workflow regenerates feed daily
- **Detailed reports**: JSON/TXT analysis reports with all metrics and decision rules

## 📊 How It Works

### Darkness Classification Process (v2.0)

1. **Metadata Gating** (lightweight, not sufficient alone)
   - Scans `title` and `location` for keywords:
     - **Night keywords**: `night`, `twilight`, `dusk`, `evening`, `aurora`
     - **Sunset keywords**: `sunset` (requires strict darkness check)
     - **Day keywords**: `day`, `noon`, `sunrise`, `morning` (mostly excluded)

2. **Image Acquisition**
   - Uses thumbnail if available (`url_img`, `image`, `thumbnail`, etc.)
   - Otherwise extracts **3 frames** at 3s, 12s, 24s from video using ffmpeg
   - **Border cropping**: Automatically detects and removes letterbox borders

3. **Luminance Analysis**
   - Converts sRGB → linear RGB
   - Computes luminance: **Y = 0.2126R + 0.7152G + 0.0722B**
   - Calculates metrics:
     - `median_Y`: Median luminance
     - `p25_Y`, `p75_Y`, `p90_Y`: 25th/75th/90th percentile luminance
     - `dark_pixel_ratio`: Fraction of pixels with Y < 0.18
     - `bright_pixel_ratio`: Fraction of pixels with Y > 0.65
     - `mid_bright_ratio`: Fraction of pixels with Y > 0.45
     - `low_sat_bright_ratio`: Fraction of HSV pixels with V > 0.65 and S < 0.25 (sky-like)
   - **Multi-frame**: Uses worst-case (brightest) metrics across all frames

4. **🚫 Daylight Veto (HARD REJECT)**
   
   If ANY of these conditions are met, the video is **immediately rejected**:
   - `bright_pixel_ratio ≥ 0.10` (>10% very bright pixels)
   - `mid_bright_ratio ≥ 0.25` (>25% medium-bright pixels)
   - `p75_Y ≥ 0.40` (75th percentile too bright)
   - `p90_Y ≥ 0.55` (90th percentile too bright)
   - `low_sat_bright_ratio ≥ 0.06` (>6% sky-like pixels)

5. **Acceptance Rules** (only if daylight veto passes)
   
   **Night keyword content:**
   - `median_Y ≤ 0.22` **OR** (`dark_pixel_ratio ≥ 0.65` AND `p75_Y ≤ 0.33`)
   
   **Sunset content (stricter):**
   - `median_Y ≤ 0.26` AND `p25_Y ≤ 0.14` AND `dark_pixel_ratio ≥ 0.55` AND `p75_Y ≤ 0.36`
   
   **Neutral content (strictest):**
   - Must pass night rules PLUS:
   - `p75_Y ≤ 0.32` AND `p90_Y ≤ 0.45` AND `mid_bright_ratio ≤ 0.18`
   
   **Day keyword content:**
   - Must have near-night profile: `median_Y ≤ 0.12`, `p75_Y ≤ 0.28`, `p90_Y ≤ 0.36`, `bright ≤ 0.03`

## 🚀 Quick Start

### Using the Pre-Generated Feed

The easiest way to use this feed is to point Overflight directly at the raw GitHub URL:

```
https://raw.githubusercontent.com/YOUR_USERNAME/overflight-night-feed/main/night.json
```

**Steps:**
1. Open Projectivy Launcher settings
2. Navigate to Overflight wallpaper settings
3. Enter the raw URL above (replace `YOUR_USERNAME` with your GitHub username)
4. Save and enjoy night-only aerial videos!

### Running Locally

#### Prerequisites

- Python 3.11+
- ffmpeg (for video frame extraction)

**Install ffmpeg:**
- **Windows**: `winget install FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

#### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/overflight-night-feed.git
cd overflight-night-feed

# Install Python dependencies
pip install -r requirements.txt

# Verify ffmpeg is installed
ffmpeg -version
```

#### Basic Usage

```bash
# Generate night.json (default upstream URL)
cd scripts
python build_night_json.py

# Dry run to preview results
python build_night_json.py --dry-run

# Generate with detailed analysis report
python build_night_json.py --write-report

# Limit items for testing
python build_night_json.py --max-items 20 --write-report
```

#### Advanced Options

```bash
python build_night_json.py \
  --upstream-url https://custom.url/videos.json \
  --output ../custom_night.json \
  --max-workers 12 \
  --cache-dir ./cache \
  --timeout 60 \
  --verbose
```

**Options:**
- `--upstream-url`: Custom upstream JSON URL
- `--output`: Output file path (default: `../night.json`)
- `--max-items`: Limit items to process (for testing)
- `--max-workers`: Concurrent workers (default: 8)
- `--cache-dir`: Custom cache directory
- `--timeout`: Request timeout in seconds (default: 30)
- `--dry-run`: Preview without writing output
- `--write-report`: Generate CSV/JSON analysis reports
- `--verbose`, `-v`: Enable debug logging

## 🔧 Configuration

### Tuning Darkness Thresholds

Edit [scripts/media_probe.py](scripts/media_probe.py) to adjust thresholds:

```python
# Night/Dark acceptance
NIGHT_MEDIAN_THRESHOLD = 0.22        # Median luminance threshold
NIGHT_DARK_RATIO_THRESHOLD = 0.65    # Min fraction of dark pixels
NIGHT_P75_THRESHOLD = 0.35           # 75th percentile threshold
NIGHT_DARK_LUMINANCE = 0.18          # What counts as "dark pixel"

# Sunset acceptance (stricter)
SUNSET_MEDIAN_THRESHOLD = 0.28
SUNSET_P25_THRESHOLD = 0.14
SUNSET_DARK_RATIO_THRESHOLD = 0.55
```

**Tips:**
- **More restrictive**: Lower thresholds (e.g., `NIGHT_MEDIAN_THRESHOLD = 0.18`)
- **More permissive**: Raise thresholds (e.g., `NIGHT_MEDIAN_THRESHOLD = 0.25`)
- **Test changes**: Use `--write-report` to see metrics for all items

### Custom Upstream URL

Set the upstream URL in the script call:

```bash
python build_night_json.py --upstream-url https://your-custom-url.com/videos.json
```

Or modify the default in [scripts/build_night_json.py](scripts/build_night_json.py):

```python
DEFAULT_UPSTREAM_URL = "https://your-custom-url.com/videos.json"
```

## 🤖 GitHub Actions Auto-Update

The repository includes a workflow that automatically regenerates `night.json` daily.

### Setup

1. **Create GitHub repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/overflight-night-feed.git
   git push -u origin main
   ```

2. **Enable GitHub Actions**
   - Go to repository Settings → Actions → General
   - Under "Workflow permissions", select "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"
   - Save

3. **Workflow runs automatically**
   - Daily at 3 AM UTC
   - On manual trigger (Actions tab → "Update Night Feed" → "Run workflow")
   - On push to scripts or workflow files

### Workflow Details

See [.github/workflows/update.yml](.github/workflows/update.yml)

**Features:**
- Installs Python dependencies and ffmpeg
- Runs `build_night_json.py` with report generation
- Commits changes if `night.json` updated
- Uploads analysis reports as artifacts (30-day retention)
- Prevents infinite loops (ignores bot commits)

## 📈 Analysis Reports

Generate detailed reports to understand classification decisions:

```bash
python build_night_json.py --write-report
```

Creates two files in `reports/`:
- `analysis_report.csv`: Spreadsheet-friendly format
- `analysis_report.json`: Structured JSON format

**Report fields:**
- `title`, `location`: Item metadata
- `accepted`: Boolean (True/False)
- `reason`: Explanation for acceptance/rejection
- `metadata_category`: `night`, `sunset`, `day`, or `neutral`
- `median_y`, `p25_y`, `p75_y`: Luminance metrics
- `dark_pixel_ratio`: Fraction of dark pixels

## 📁 Repository Structure

```
overflight-night-feed/
├── night.json                    # Generated feed (auto-updated)
├── scripts/
│   ├── build_night_json.py       # Main pipeline script
│   └── media_probe.py            # Darkness analysis module
├── reports/
│   ├── analysis_report.csv       # Generated report (CSV)
│   └── analysis_report.json      # Generated report (JSON)
├── .github/
│   └── workflows/
│       └── update.yml            # Auto-update workflow
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── LICENSE                       # MIT License
└── .gitignore
```

## 🧪 Testing

### Dry Run

Preview results without writing output:

```bash
python build_night_json.py --dry-run --max-items 10
```

### Test with Limited Items

Process only first N items:

```bash
python build_night_json.py --max-items 20 --write-report
```

Check `reports/analysis_report.csv` to verify classification accuracy.

### Manual Classification Check

To manually verify a specific video:

```python
from scripts.media_probe import MediaProbe

probe = MediaProbe()
result = probe.classify_item({
    'title': 'Night View of City',
    'location': 'Tokyo',
    'url_1080p': 'https://example.com/video.mp4'
})

print(f"Accepted: {result.accepted}")
print(f"Reason: {result.reason}")
print(f"Metrics: {result.metrics}")
```

## 🐛 Troubleshooting

### FFmpeg Not Found

**Error:** `ffmpeg not available - cannot extract video frames`

**Solution:**
- Install ffmpeg (see Prerequisites)
- Verify: `ffmpeg -version`
- On Windows, ensure ffmpeg is in PATH

### Timeout Errors

**Error:** `Request timeout` or `Video frame extraction timed out`

**Solution:**
- Increase timeout: `--timeout 60`
- Reduce workers: `--max-workers 4`
- Check internet connection

### Low Acceptance Rate

If too few videos are accepted:

1. Generate report: `--write-report`
2. Check `reports/analysis_report.csv`
3. Review `median_y` values of rejected items
4. Adjust thresholds in `media_probe.py` (see Configuration)
5. Re-run and verify

### GitHub Actions Failing

1. Check Actions tab for error logs
2. Verify workflow permissions (Settings → Actions → General)
3. Ensure ffmpeg installation step succeeds
4. Test locally first: `python build_night_json.py --write-report`

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Better frame extraction heuristics (detect black frames)
- ML-based classification (train on labeled data)
- Support for more video formats
- Adaptive thresholds based on location/season
- Multi-frame analysis for better accuracy

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [Projectivy Overflight](https://github.com/projectivy/overflight) - Original wallpaper plugin
- ITU-R BT.709 - Luminance calculation standard
- FFmpeg - Video frame extraction

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/overflight-night-feed/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/overflight-night-feed/discussions)

---

**Enjoy your night-time aerial wallpapers! 🌙✨**
