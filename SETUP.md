# Setup Guide for Overflight Night Feed

This guide walks you through setting up your own auto-updating night feed.

## Step 1: Install Prerequisites

### Python 3.11+

**Windows:**
```powershell
# Using winget
winget install Python.Python.3.11

# Or download from python.org
# https://www.python.org/downloads/
```

**macOS:**
```bash
brew install python@3.11
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3-pip
```

### FFmpeg

**Windows:**
```powershell
# Using winget
winget install FFmpeg

# Or using Chocolatey
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
python --version  # Should be 3.11+
```

## Step 2: Clone and Install

```bash
# Navigate to your projects directory
cd ~/projects  # or wherever you keep projects

# Clone this repository
git clone https://github.com/YOUR_USERNAME/overflight-night-feed.git
cd overflight-night-feed

# Install Python dependencies
pip install -r requirements.txt
```

## Step 3: Test Locally

```bash
# Run a test with limited items
cd scripts
python build_night_json.py --max-items 10 --write-report --dry-run

# If successful, generate the full feed
python build_night_json.py --write-report
```

Check the output:
- `night.json` should be created in the parent directory
- `reports/analysis_report.csv` shows classification details

## Step 4: Create GitHub Repository

### Option A: Create New Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `overflight-night-feed`
3. Description: "Night-only aerial video feed for Projectivy Overflight"
4. Public repository (required for raw URL access)
5. Don't initialize with README (we already have one)
6. Click "Create repository"

### Option B: Use GitHub CLI

```bash
# Install GitHub CLI if needed
# Windows: winget install GitHub.cli
# macOS: brew install gh
# Linux: https://github.com/cli/cli#installation

# Login to GitHub
gh auth login

# Create repository
gh repo create overflight-night-feed --public --source=. --remote=origin
```

## Step 5: Push to GitHub

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Overflight night feed generator"

# Set branch name
git branch -M main

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/overflight-night-feed.git

# Push to GitHub
git push -u origin main
```

## Step 6: Configure GitHub Actions

1. Go to your repository on GitHub
2. Click **Settings** → **Actions** → **General**
3. Scroll to "Workflow permissions"
4. Select **"Read and write permissions"**
5. Check **"Allow GitHub Actions to create and approve pull requests"**
6. Click **Save**

## Step 7: Trigger First Run

### Option A: Wait for Scheduled Run
The workflow runs automatically daily at 3 AM UTC.

### Option B: Trigger Manually
1. Go to **Actions** tab in your repository
2. Click **"Update Night Feed"** workflow
3. Click **"Run workflow"** dropdown
4. Click green **"Run workflow"** button
5. Watch the progress

## Step 8: Get Your Raw URL

Once `night.json` is generated:

1. Navigate to your `night.json` file on GitHub
2. Click the **"Raw"** button
3. Copy the URL - it will look like:
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/overflight-night-feed/main/night.json
   ```

## Step 9: Configure Overflight

1. Open **Projectivy Launcher** on your Android TV device
2. Go to **Settings**
3. Navigate to **Screensaver / Wallpaper** settings
4. Find **Overflight** settings
5. Look for custom URL or JSON feed option
6. Paste your raw GitHub URL
7. Save settings

**Note:** The exact steps may vary by Projectivy version. Consult Overflight documentation if needed.

## Step 10: Verify Auto-Updates

Check that the workflow runs successfully:

1. Go to **Actions** tab
2. Look for green checkmarks ✅
3. Click on a run to see details
4. Download "analysis-report" artifact to review classifications

## Troubleshooting Setup Issues

### "Permission denied" when pushing to GitHub

```bash
# Use HTTPS with token or SSH
# For HTTPS, generate a Personal Access Token:
# GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
# Grant "repo" scope

# Use token when pushing:
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/overflight-night-feed.git
```

### GitHub Actions workflow not running

1. Verify workflow file is at `.github/workflows/update.yml`
2. Check that Actions are enabled (Settings → Actions)
3. Verify permissions are set (see Step 6)
4. Check Actions tab for error messages

### FFmpeg errors in GitHub Actions

This shouldn't happen with the provided workflow, but if it does:
1. Check the "Install ffmpeg" step in workflow logs
2. Verify `ffmpeg -version` step succeeds
3. The workflow uses Ubuntu which has ffmpeg in apt repositories

### Script fails with "No module named X"

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Different upstream URL

To use a different source (not the default Overflight feed):

```bash
# Edit scripts/build_night_json.py
# Change DEFAULT_UPSTREAM_URL at the top

# Or pass as argument
python build_night_json.py --upstream-url https://your-custom-url.com/videos.json
```

## Customization Tips

### Adjust darkness thresholds

Edit `scripts/media_probe.py`:

```python
# Make more restrictive (fewer items accepted)
NIGHT_MEDIAN_THRESHOLD = 0.18  # Lower = darker required

# Make more permissive (more items accepted)
NIGHT_MEDIAN_THRESHOLD = 0.25  # Higher = lighter allowed
```

### Change update frequency

Edit `.github/workflows/update.yml`:

```yaml
# Change from daily to every 6 hours
schedule:
  - cron: '0 */6 * * *'

# Or weekly on Monday at 3 AM
schedule:
  - cron: '0 3 * * 1'
```

### Add webhook notifications

Add a step to the workflow to notify you:

```yaml
- name: Notify on update
  if: steps.check_changes.outputs.changed == 'true'
  run: |
    curl -X POST YOUR_WEBHOOK_URL \
      -H 'Content-Type: application/json' \
      -d '{"text":"Night feed updated!"}'
```

## Next Steps

- ⭐ Star the repository to keep track of updates
- 📊 Review analysis reports to tune thresholds
- 🐛 Report issues on GitHub Issues page
- 🤝 Contribute improvements via Pull Requests

Enjoy your night-time aerial wallpapers! 🌙
