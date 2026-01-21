# Deployment Checklist ✅

Use this checklist when setting up your own instance of the night feed.

## Pre-Deployment

- [ ] Python 3.11+ installed (`python --version`)
- [ ] FFmpeg installed (`ffmpeg -version`)
- [ ] Git installed (`git --version`)
- [ ] GitHub account created
- [ ] Repository plan confirmed (must be public for raw URL access)

## Local Setup

- [ ] Clone or download repository
- [ ] Navigate to project directory
- [ ] Install Python dependencies (`pip install -r requirements.txt`)
- [ ] Verify installation (`pip list | grep -E "(requests|Pillow|numpy|tqdm)"`)

## Testing

- [ ] Run quick test (`python test_pipeline.py`)
- [ ] Check `test_night.json` created
- [ ] Review `reports/analysis_report.csv`
- [ ] Verify classification accuracy acceptable
- [ ] Adjust thresholds in `media_probe.py` if needed

## Full Pipeline Test

- [ ] Run with limited items (`cd scripts && python build_night_json.py --max-items 20 --write-report`)
- [ ] Verify `night.json` created in parent directory
- [ ] Check item count matches expectations
- [ ] Review reports for any errors
- [ ] Test with more items if first test passes

## GitHub Repository Setup

- [ ] Create new public repository on GitHub
- [ ] Repository name: `overflight-night-feed`
- [ ] Add description: "Night-only aerial video feed for Projectivy Overflight"
- [ ] Don't initialize with README/LICENSE/gitignore (we have them)

## Git Configuration

- [ ] Initialize git (`git init`)
- [ ] Add all files (`git add .`)
- [ ] Create initial commit (`git commit -m "Initial commit"`)
- [ ] Set branch to main (`git branch -M main`)
- [ ] Add remote (`git remote add origin https://github.com/YOUR_USERNAME/overflight-night-feed.git`)
- [ ] Push to GitHub (`git push -u origin main`)

## GitHub Actions Setup

- [ ] Go to repository Settings
- [ ] Navigate to Actions → General
- [ ] Set "Workflow permissions" to "Read and write permissions"
- [ ] Check "Allow GitHub Actions to create and approve pull requests"
- [ ] Save changes

## First Workflow Run

- [ ] Go to Actions tab
- [ ] Select "Update Night Feed" workflow
- [ ] Click "Run workflow" → "Run workflow"
- [ ] Wait for workflow to complete
- [ ] Check for green checkmark ✅
- [ ] Verify `night.json` was committed
- [ ] Download analysis-report artifact
- [ ] Review report for accuracy

## Get Raw URL

- [ ] Navigate to `night.json` file on GitHub
- [ ] Click "Raw" button
- [ ] Copy URL (format: `https://raw.githubusercontent.com/YOUR_USERNAME/overflight-night-feed/main/night.json`)
- [ ] Save URL for Overflight configuration

## Overflight Configuration

- [ ] Open Projectivy Launcher on Android TV
- [ ] Go to Settings
- [ ] Find Overflight wallpaper settings
- [ ] Locate custom JSON feed URL option
- [ ] Paste raw GitHub URL
- [ ] Save settings
- [ ] Test wallpaper display

## Verification

- [ ] Wallpaper displays night-only videos
- [ ] Videos rotate correctly
- [ ] No bright/daytime videos appear
- [ ] Quality is acceptable (1080p or better)

## Monitoring Setup

- [ ] Star your own repository (to keep track)
- [ ] Enable email notifications for Actions failures (Settings → Notifications)
- [ ] Set calendar reminder to check feed monthly
- [ ] Bookmark Actions page for quick status check

## Customization (Optional)

- [ ] Review `config.example.py` for customization options
- [ ] Adjust darkness thresholds if needed
- [ ] Modify workflow schedule if desired
- [ ] Add webhook notifications (Slack, Discord, etc.)

## Documentation

- [ ] Update README.md with your username in URLs
- [ ] Add any custom configuration notes
- [ ] Document threshold changes (if made)
- [ ] Update SETUP.md if you found better instructions

## Maintenance Plan

- [ ] Add to calendar: Monthly review of Actions success rate
- [ ] Plan: Quarterly threshold review based on reports
- [ ] Decide: Keep or archive old reports
- [ ] Monitor: GitHub Actions quota (should be unlimited for public repos)

## Troubleshooting Preparation

- [ ] Bookmark GitHub Actions documentation
- [ ] Bookmark FFmpeg documentation  
- [ ] Join Projectivy community/forum for Overflight support
- [ ] Save link to this repository's Issues page

## Success Criteria

Your deployment is successful when:

- ✅ GitHub Actions runs daily without failures
- ✅ `night.json` updates automatically
- ✅ Overflight displays only night videos
- ✅ No manual intervention needed for normal operation
- ✅ Analysis reports show accurate classification

## Post-Deployment

- [ ] Share your feed URL (if desired)
- [ ] Contribute improvements back to original repository
- [ ] Write blog post about your experience (optional)
- [ ] Help others in community forums

---

**Date Completed:** _____________

**Your Feed URL:** 
```
https://raw.githubusercontent.com/___________/overflight-night-feed/main/night.json
```

**Notes:**
