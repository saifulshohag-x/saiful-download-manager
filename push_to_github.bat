@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo ====================================================
echo   Saiful Download Manager v2.0 - GitHub Push Helper
echo ====================================================
echo.
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git is not installed.
    echo Please install Git for Windows from: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK] Git found:
git --version
echo.
set /p GITHUB_USER="Enter your GitHub username: "
if "!GITHUB_USER!"=="" (
    echo ERROR: username is required.
    pause
    exit /b 1
)
set /p REPO_NAME="Enter repository name (default: saiful-download-manager): "
if "!REPO_NAME!"=="" set REPO_NAME=saiful-download-manager
set REMOTE_URL=https://github.com/!GITHUB_USER!/!REPO_NAME!.git
echo.
echo Repository URL: !REMOTE_URL!
echo.
echo Make sure you have ALREADY created this empty repository on GitHub:
echo   https://github.com/new
echo (Set to Private, do NOT initialize with README)
echo.
pause
if not exist ".git" (
    git init
    git branch -M main
)
git add .
git add .github 2>nul
git status --short
git commit -m "Saiful Download Manager v2.0 - IDM clone with video overlay"
git remote remove origin 2>nul
git remote add origin !REMOTE_URL!
echo.
echo === Pushing to GitHub ===
echo When prompted for password, paste your Personal Access Token (PAT).
echo.
git push -u origin main
if errorlevel 1 (
    echo.
    echo ERROR: push failed.
    pause
    exit /b 1
)
echo.
echo SUCCESS! Code pushed.
echo.
echo Next steps:
echo   1. Open: https://github.com/!GITHUB_USER!/!REPO_NAME!/actions
echo   2. Wait 5-10 minutes for the build
echo   3. Click the latest build, scroll to Artifacts
echo   4. Download SaifulDownloadManager-windows-exe
echo.
start https://github.com/!GITHUB_USER!/!REPO_NAME!/actions
pause
