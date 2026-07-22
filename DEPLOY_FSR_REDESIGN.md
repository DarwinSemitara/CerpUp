# FSR Redesign Deployment Checklist

## Files Changed in This Update

### New Files Created
✅ `templates/partials/fsr.html` - Complete FSR page with preview functionality

### Modified Files
✅ `app.py` - Added member_id filtering to research and extensions endpoints

### Documentation Created
✅ `FSR_PAGE_REDESIGN_COMPLETE.md` - Complete implementation documentation
✅ `DEPLOY_FSR_REDESIGN.md` - This deployment checklist

## Pre-Deployment Verification

### 1. Check File Syntax
```bash
python -m py_compile app.py
```
✅ Status: Passed

### 2. Verify Required Dependencies
Check `requirements.txt` includes:
- `openpyxl==3.1.5` ✅

### 3. Verify Required Files Exist
- ✅ `templates/partials/fsr.html`
- ✅ `static/reference/SAMPLE FSR.xlsx`
- ✅ `services/fsr_generator.py`

### 4. Verify Database Collections
Required Firestore collections:
- ✅ `members`
- ✅ `research`
- ✅ `extensions`
- ✅ `users` (for admin authentication)

## Deployment Steps

### Option 1: Git Deployment (Recommended)

#### Step 1: Stage Files
```bash
git add templates/partials/fsr.html
git add app.py
git add FSR_PAGE_REDESIGN_COMPLETE.md
git add DEPLOY_FSR_REDESIGN.md
```

#### Step 2: Commit Changes
```bash
git commit -m "feat: Complete FSR page redesign with preview functionality

- Added member selection dropdown with auto-preview
- Implemented live spreadsheet preview for research and extensions
- Added Download Excel and Download All (ZIP) functionality
- Updated research and extensions APIs to support member_id filtering
- Created comprehensive FSR preview with faculty information header
- Added empty, loading, and error states
- Implemented responsive design with maroon color scheme
- Created detailed documentation

Features:
- Member selection with semester/year controls
- Live FSR preview with calculated credit totals
- Individual FSR Excel download
- Bulk ZIP download for all members
- Auto-loading preview on member selection
- Real-time preview updates on config changes

Backend Changes:
- /api/research now accepts ?member_id parameter for admin filtering
- /api/extensions now accepts ?member_id parameter for admin filtering
- Both endpoints maintain backward compatibility

Testing Required:
- Verify member dropdown loads correctly
- Test FSR preview rendering
- Test Excel file generation
- Test ZIP file generation for all members
- Verify credit totals calculate correctly"
```

#### Step 3: Push to GitHub
```bash
git push origin main
```

#### Step 4: Deploy on Render
1. Log in to Render dashboard
2. Go to your CERP2.0 service
3. Click "Manual Deploy" → "Deploy latest commit"
4. Wait for deployment to complete (usually 2-5 minutes)
5. Check deployment logs for any errors

### Option 2: Manual Deployment

If using manual file upload:
1. Upload `templates/partials/fsr.html` to production
2. Upload modified `app.py` to production
3. Restart the application server
4. Verify `generated_fsr` directory exists and is writable

## Post-Deployment Testing

### 1. Access FSR Page
- URL: `https://your-domain.com/fsr/`
- Expected: Page loads with generator section and empty preview

### 2. Test Member Selection
- Select a member from dropdown
- Expected: Buttons enable, preview loads automatically

### 3. Test Preview Display
- Expected: Faculty info header displays correctly
- Expected: Research table shows data (if member has research)
- Expected: Extensions table shows data (if member has extensions)
- Expected: Credit totals calculate correctly

### 4. Test Download Excel
- Click "Download Excel" button
- Expected: Excel file downloads with correct filename
- Expected: Open Excel file to verify format matches SAMPLE FSR.xlsx
- Expected: Verify all data populated correctly

### 5. Test Download All
- Click "Download All (ZIP)" button
- Expected: ZIP file downloads
- Expected: ZIP contains Excel files for all members
- Expected: Each Excel file is properly formatted

### 6. Test Semester/Year Changes
- Change semester or year
- Expected: Preview reloads with updated information
- Expected: Downloads use new semester/year

### 7. Test Error Handling
- Check browser console for JavaScript errors
- Test with member who has no data
- Test with invalid selections

## Rollback Plan

If issues are detected:

### Rollback Git Deployment
```bash
git revert HEAD
git push origin main
```

### Rollback Manual Deployment
1. Restore previous version of `app.py`
2. Remove `templates/partials/fsr.html` (will show placeholder)
3. Restart application

## Monitoring

### Things to Monitor After Deployment

1. **Server Logs**: Check for Python errors related to FSR generation
2. **Response Times**: Monitor `/api/research` and `/api/extensions` performance
3. **Disk Space**: The `generated_fsr` directory should auto-clean, but monitor it
4. **User Feedback**: Test with actual users and gather feedback

### Expected Log Entries (Normal)
```
📚 Fetching research for member: {uid} (admin view)...
✅ Found {n} research items
```

### Error Log Entries to Watch For
```
❌ Error fetching research: ...
Error generating FSR: ...
Error generating FSR for member {id}: ...
```

## Known Issues & Solutions

### Issue: "Generated_fsr directory not found"
**Solution**: Create the directory manually:
```bash
mkdir generated_fsr
```

### Issue: "Permission denied" when creating FSR
**Solution**: Check directory permissions:
```bash
chmod 755 generated_fsr
```

### Issue: "Module 'openpyxl' not found"
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Preview shows no data but member has data
**Solution**: 
1. Check member's `uid` matches data in `research` and `extensions` collections
2. Verify Firestore indexes are built
3. Check browser console for API errors

## Success Criteria

✅ FSR page loads without errors
✅ Member dropdown populates with all faculty
✅ Preview displays correctly for selected member
✅ Excel download works for individual member
✅ ZIP download works for all members
✅ Semester/year changes work correctly
✅ No console errors in browser
✅ No Python errors in server logs
✅ Response times are acceptable (<2s for preview, <5s for download)

## Support Contacts

- **Technical Issues**: Check server logs and browser console
- **Data Issues**: Verify Firestore collections and data structure
- **Feature Requests**: Document in project issues/backlog

---

## Quick Command Reference

### Check deployment status (Render)
Visit: https://dashboard.render.com

### View server logs (Render)
Click on service → Logs tab

### Test locally
```bash
python app.py
```
Then visit: http://localhost:5000/fsr/

### Clear generated FSR files
```bash
rm -rf generated_fsr/*
```
(Files auto-delete after ZIP creation, but manual cleanup may be needed)

---

**Deployment Date**: _________________
**Deployed By**: _________________
**Status**: _________________
**Issues Found**: _________________
**Resolution**: _________________
