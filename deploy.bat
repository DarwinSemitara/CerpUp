@echo off
echo ========================================
echo CerpUp - Quick Deploy to GitHub
echo ========================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo Initializing Git repository...
    git init
    git branch -M main
    git remote add origin https://github.com/DarwinSemitara/CerpUp.git
    echo.
)

REM Add all changes
echo Adding all changes...
git add .
echo.

REM Prompt for commit message
set /p commit_msg="Enter commit message: "
if "%commit_msg%"=="" set commit_msg=Update from local

REM Commit changes
echo Committing changes...
git commit -m "%commit_msg%"
echo.

REM Push to GitHub
echo Pushing to GitHub...
git push -u origin main
echo.

echo ========================================
echo ✅ Deploy complete!
echo.
echo Render will automatically deploy your changes.
echo Check status at: https://dashboard.render.com/
echo ========================================
pause
