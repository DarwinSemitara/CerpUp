@echo off
echo ========================================
echo Git Commit and Push Script
echo ========================================
echo.

REM Navigate to project directory
cd /d "c:\Users\PC\Documents\CERP2.0"

REM Check git status
echo Checking current status...
git status
echo.

REM Stage all changes
echo Staging all changes...
git add .
echo.

REM Show what will be committed
echo Files to be committed:
git status --short
echo.

REM Commit with descriptive message
echo Committing changes...
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
echo.

REM Push to GitHub
echo Pushing to GitHub...
git push origin main
echo.

echo ========================================
echo Done! Changes pushed to GitHub
echo ========================================
echo.
echo Next steps:
echo 1. Go to render.com dashboard
echo 2. Your app should auto-deploy (if auto-deploy is enabled)
echo 3. OR manually trigger deploy from Render dashboard
echo.
pause
