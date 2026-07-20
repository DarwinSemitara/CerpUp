# Git Commands for Deployment

## Quick Deploy (Run the batch file)
```bash
git_deploy_commands.bat
```

---

## Manual Commands (Step by Step)

### 1. Check Current Status
```bash
cd c:\Users\PC\Documents\CERP2.0
git status
```

### 2. Stage All Changes
```bash
git add .
```

### 3. Verify Staged Files
```bash
git status
```

### 4. Commit Changes
```bash
git commit -m "feat: Add Extensions admin page, FSR generation system, and UI improvements

- Add Extensions admin page with table and filters
- Implement FSR (Faculty Service Record) generation system
  - Analyze and replicate SAMPLE FSR.xlsx template
  - Create FSR generator service with Excel export
  - Add FSR admin UI with bulk and individual download
  - Add API endpoints for FSR generation
- Rename 'Data' to 'FSR' in admin sidebar
- Standardize logout modal design across all admin pages
- Remove 'Generate Report' button from Research page
- Add openpyxl dependency for Excel file generation
- Update requirements.txt with openpyxl==3.1.5"
```

### 5. Push to GitHub
```bash
git push origin main
```

---

## What Gets Committed

### New Files:
- `services/fsr_generator.py`
- `templates/partials/fsr.html`
- `templates/partials/extensions.html`
- `static/reference/SAMPLE FSR.xlsx`
- `FSR_IMPLEMENTATION_SUMMARY.md`
- `CHANGES_SUMMARY.md`
- `examine_fsr.py`
- `examine_fsr_detailed.py`
- `git_deploy_commands.bat`
- `GIT_COMMANDS.md`

### Modified Files:
- `app.py`
- `requirements.txt`
- `templates/admin.html`
- `templates/admin_base.html`
- `templates/partials/research.html`
- `static/css/admin.css`
- `static/js/admin.js`

---

## After Pushing to GitHub

### Option 1: Auto-Deploy (if enabled in Render)
1. Push completes
2. Render detects the changes
3. Automatically starts deployment
4. Wait 2-5 minutes for deployment to complete

### Option 2: Manual Deploy in Render
1. Go to https://dashboard.render.com
2. Select your CERP2.0 app
3. Click "Manual Deploy" dropdown
4. Click "Deploy latest commit"
5. Wait for deployment to complete

---

## Verify Deployment

After deployment completes:

1. **Check Build Logs**
   - Verify `openpyxl==3.1.5` was installed
   - Look for "Build successful" message

2. **Test the App**
   - Navigate to Extensions page ✓
   - Navigate to FSR page ✓
   - Test logout modal on different pages ✓
   - Try generating an FSR ✓

3. **Check for Errors**
   - Open browser console (F12)
   - Check for any JavaScript errors
   - Check Render logs for Python errors

---

## Troubleshooting

### If build fails:
```bash
# Check requirements.txt syntax
cat requirements.txt

# Verify Python version
python --version

# Test openpyxl installation locally
pip install openpyxl==3.1.5
```

### If openpyxl import fails:
- Render might need to clear build cache
- Go to Render dashboard → Settings → Clear build cache & redeploy

### If SAMPLE FSR.xlsx not found:
- Verify file was committed: `git ls-files static/reference/`
- Check file size (should be under 100MB for GitHub)

---

## Alternative: Quick One-Liner

If you're already in the project directory:

```bash
git add . && git commit -m "feat: Extensions, FSR system, UI improvements" && git push origin main
```

---

## Git Configuration Check

Before committing, verify your Git config:

```bash
git config user.name
git config user.email
```

If not set:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## Branch Information

Current branch: `main`
Remote: `origin`

To check:
```bash
git branch
git remote -v
```

---

**Ready to deploy! 🚀**
