# Quick Reference Card 🚀

Keep this handy for common commands and URLs.

## 📍 Your Feed URL
```
https://raw.githubusercontent.com/YOUR_USERNAME/overflight-night-feed/main/night.json
```
👆 Replace `YOUR_USERNAME` and use this in Overflight settings

## ⚡ Common Commands

### Generate Feed
```bash
cd scripts
python build_night_json.py
```

### Test First (Recommended)
```bash
# Test with 10 items
python build_night_json.py --max-items 10 --dry-run

# Generate with report
python build_night_json.py --max-items 10 --write-report
```

### Quick Test (From Root)
```bash
python test_pipeline.py
```

### Full Run with Reports
```bash
cd scripts
python build_night_json.py --write-report --verbose
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Check FFmpeg
```bash
ffmpeg -version
```

## 📂 Important Files

| File | What It Does |
|------|--------------|
| `night.json` | **Your filtered feed** - use this URL |
| `scripts/build_night_json.py` | Main generator script |
| `scripts/media_probe.py` | Darkness classifier (edit thresholds here) |
| `reports/analysis_report.csv` | See why items accepted/rejected |
| `.github/workflows/update.yml` | Auto-update schedule (edit here) |

## 🎛️ Tuning Darkness Thresholds

Edit `scripts/media_probe.py`:

```python
# Lines 22-30: Make more restrictive (fewer items)
NIGHT_MEDIAN_THRESHOLD = 0.18  # Lower = darker required

# Make more permissive (more items)
NIGHT_MEDIAN_THRESHOLD = 0.25  # Higher = lighter allowed
```

After changing, test:
```bash
python build_night_json.py --max-items 20 --write-report
# Check reports/analysis_report.csv
```

## 🤖 GitHub Actions

### Trigger Manual Run
1. Go to **Actions** tab
2. Click **"Update Night Feed"**
3. Click **"Run workflow"** → **"Run workflow"**

### Change Schedule
Edit `.github/workflows/update.yml`:
```yaml
# Daily at 3 AM UTC
schedule:
  - cron: '0 3 * * *'

# Every 6 hours
schedule:
  - cron: '0 */6 * * *'

# Weekly on Monday
schedule:
  - cron: '0 3 * * 1'
```

## 🔍 Check What's Happening

### View Generated Feed
```bash
cat night.json | python -m json.tool | head -n 20
```

### Count Items
```bash
# Linux/Mac
cat night.json | python -m json.tool | grep -c '"location"'

# Python
python -c "import json; print(len(json.load(open('night.json'))))"
```

### View Reports
```bash
# Open CSV in Excel/LibreOffice
start reports/analysis_report.csv  # Windows
open reports/analysis_report.csv   # Mac
xdg-open reports/analysis_report.csv  # Linux
```

## 🐛 Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| FFmpeg not found | Install: `winget install FFmpeg` (Windows) / `brew install ffmpeg` (Mac) |
| Module not found | `pip install -r requirements.txt` |
| Timeout errors | Add `--timeout 60` to command |
| Too few items | Lower thresholds in `media_probe.py` |
| Too many items | Raise thresholds (be more strict) |
| Workflow fails | Check Actions logs; verify permissions |

## 📱 Overflight Setup

1. Open Projectivy Launcher on Android TV
2. Settings → Wallpaper → Overflight
3. Find "Custom JSON URL" or "Feed URL"
4. Paste your raw GitHub URL
5. Save

## 🔗 Quick Links

- **Your Repo**: `https://github.com/YOUR_USERNAME/overflight-night-feed`
- **Actions**: `https://github.com/YOUR_USERNAME/overflight-night-feed/actions`
- **Raw Feed**: `https://raw.githubusercontent.com/YOUR_USERNAME/overflight-night-feed/main/night.json`

## 📊 Understanding Metrics

From `analysis_report.csv`:

- **median_y**: 0.0 = black, 1.0 = white
  - Night: usually < 0.22
  - Sunset: < 0.28
  - Day: > 0.35

- **dark_pixel_ratio**: Fraction of dark pixels
  - Night: usually > 0.65
  - Day: < 0.40

- **accepted**: `True` = included in feed

## 💡 Pro Tips

1. **Test before full run**: Always use `--max-items 10` first
2. **Check reports**: Use `--write-report` to understand decisions
3. **Cache is your friend**: Re-runs are faster (uses cached images)
4. **Dry run for preview**: Use `--dry-run` to see what would happen
5. **Monitor Actions**: Check weekly for failures

## 🆘 Get Help

- Check `README.md` for detailed docs
- Check `SETUP.md` for step-by-step setup
- Check `ASSUMPTIONS.md` for "why" questions
- Open GitHub Issue for bugs

## 🎯 Success Checklist

- [ ] FFmpeg installed and working
- [ ] Python dependencies installed
- [ ] Test run succeeds
- [ ] GitHub repo created and pushed
- [ ] Actions workflow runs successfully
- [ ] `night.json` generated
- [ ] Overflight configured with raw URL
- [ ] Night videos display on TV

---

**Keep this card bookmarked!** 🔖

Last updated: January 2026
