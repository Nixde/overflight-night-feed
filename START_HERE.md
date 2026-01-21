# 👋 START HERE

Welcome! This is a complete, production-ready pipeline that generates a night-only aerial video feed for Projectivy Overflight.

## 🚦 Quick Navigation

**Never used this before?** → Read below (5 minutes)  
**Ready to set up?** → [SETUP.md](SETUP.md)  
**Need commands?** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)  
**Want details?** → [README.md](README.md)  
**Deploy checklist?** → [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

---

## ⚡ 3-Minute Overview

### What This Does
Takes a video feed (like Overflight's aerial videos) and filters it to **only include night/dark videos** using actual image analysis—not just keywords.

### Why It's Special
- **Real darkness measurement**: Uses professional luminance calculations
- **Smart filtering**: Includes dark sunsets, rejects bright ones
- **Auto-updates**: GitHub Actions regenerates feed daily
- **No manual work**: Set it and forget it

### What You Get
A URL like this:
```
https://raw.githubusercontent.com/YOUR_USERNAME/overflight-night-feed/main/night.json
```

Paste it into Projectivy Overflight → enjoy night-only wallpapers!

---

## 🎯 Choose Your Path

### Path A: Quick Test (Recommended First)
**Time: 5 minutes**

1. Install prerequisites:
   ```bash
   # Windows
   winget install Python.Python.3.11
   winget install FFmpeg
   ```

2. Install dependencies:
   ```bash
   cd overflight-night-feed
   pip install -r requirements.txt
   ```

3. Run test:
   ```bash
   python test_pipeline.py
   ```

4. Check output:
   - `test_night.json` (filtered videos)
   - `reports/analysis_report.csv` (details)

**✅ If test passes, you're ready for Path B!**

---

### Path B: Full Setup & Deploy
**Time: 20-30 minutes**

**Follow the step-by-step guide:** [SETUP.md](SETUP.md)

Quick overview:
1. ✅ Prerequisites installed (Python, FFmpeg)
2. ✅ Test run successful
3. 🔄 Create GitHub repository
4. 🔄 Push code to GitHub
5. 🔄 Configure GitHub Actions
6. 🔄 Get raw URL
7. 🔄 Use in Overflight

**Result:** Auto-updating night feed on GitHub!

---

### Path C: Just Read the Docs
**Time: 10 minutes**

Want to understand before diving in?

1. **[README.md](README.md)** - How it works, features, configuration
2. **[ASSUMPTIONS.md](ASSUMPTIONS.md)** - Design decisions, why things work this way
3. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Architecture, performance, quality

---

## 🆘 Common Questions

### Q: Do I need to be a programmer?
**A:** Not really! Follow SETUP.md step-by-step. Copy-paste the commands.

### Q: What if I get stuck?
**A:** Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for troubleshooting. Most issues are:
- FFmpeg not installed → `winget install FFmpeg`
- Dependencies missing → `pip install -r requirements.txt`

### Q: Can I customize which videos are included?
**A:** Yes! Edit thresholds in `scripts/media_probe.py`. Details in README.md.

### Q: How often does it update?
**A:** Daily at 3 AM UTC (configurable in `.github/workflows/update.yml`).

### Q: Is it free?
**A:** Yes! GitHub Actions is free for public repositories.

### Q: What if the upstream feed changes?
**A:** The pipeline adapts automatically. Handles different JSON structures.

---

## 📚 Document Guide

| Document | What's Inside | When to Read |
|----------|---------------|--------------|
| **START_HERE.md** | This file - orientation | First |
| **README.md** | Features, usage, how it works | Before setup |
| **SETUP.md** | Step-by-step deployment | During setup |
| **QUICK_REFERENCE.md** | Commands, troubleshooting | Keep handy |
| **DEPLOYMENT_CHECKLIST.md** | Verify everything works | During deploy |
| **ASSUMPTIONS.md** | Why things work this way | If curious |
| **PROJECT_SUMMARY.md** | Architecture, quality | For developers |
| **DELIVERABLES.md** | What was built | For overview |

---

## 🎓 What You Need to Know

### Prerequisites
- **Python 3.11+**: Programming language
- **FFmpeg**: Video processing tool
- **Git**: Version control
- **GitHub account**: For hosting the feed

### Skills Needed
- Basic command line (copy-paste commands)
- GitHub account creation
- Text editor for config (optional)

### Time Investment
- **Test run**: 5 minutes
- **Full setup**: 20-30 minutes
- **Maintenance**: ~5 minutes/month (check if it's working)

---

## 🚀 Ready to Start?

### Immediate Next Steps:

1. **Install Python 3.11+**
   ```bash
   python --version  # Check if installed
   ```

2. **Install FFmpeg**
   ```bash
   ffmpeg -version  # Check if installed
   ```

3. **Run Quick Test**
   ```bash
   cd overflight-night-feed
   pip install -r requirements.txt
   python test_pipeline.py
   ```

4. **If test passes → Follow [SETUP.md](SETUP.md)**

---

## 💡 Pro Tips

1. **Start with the test** - Don't skip `test_pipeline.py`
2. **Read the output** - Logs tell you what's happening
3. **Check reports** - `analysis_report.csv` explains decisions
4. **Use dry-run** - Add `--dry-run` to preview without writing
5. **Keep QUICK_REFERENCE.md handy** - Has all commands

---

## 🎯 Success Looks Like

After setup, you'll have:

✅ GitHub repository with your code  
✅ Workflow running daily automatically  
✅ `night.json` file updating daily  
✅ Raw URL to use in Overflight  
✅ Night-only videos on your TV  

---

## 🎉 You're Ready!

**Next action:** 

```bash
# If not done already
cd overflight-night-feed
python test_pipeline.py
```

**Then:** Open [SETUP.md](SETUP.md) and follow step-by-step.

---

## 📞 Need Help?

- **Commands not working?** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md) → Troubleshooting
- **Setup unclear?** → [SETUP.md](SETUP.md) has step-by-step screenshots
- **Errors in logs?** → Copy error message, check README.md troubleshooting
- **Want to customize?** → [README.md](README.md) → Configuration section

---

**Let's get started! 🚀**

Open your terminal and run: `python test_pipeline.py`
