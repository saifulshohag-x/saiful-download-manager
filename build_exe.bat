@echo off
REM ============================================================
REM  build_exe.bat - Saiful Download Manager v2.0
REM  Builds a standalone SaifulDownloadManager.exe for Windows.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo ====================================================
echo   Saiful Download Manager v2.0 - Windows .exe Builder
echo ====================================================
echo.

echo === Step 1/3: Installing dependencies ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo ERROR: dependency install failed.
    pause
    exit /b 1
)

echo.
echo === Step 2/3: Building SaifulDownloadManager.exe ===
echo (this takes 3-5 minutes, please wait...)
echo.

python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "SaifulDownloadManager" ^
    --collect-all customtkinter ^
    --collect-all yt_dlp ^
    --collect-submodules yt_dlp ^
    --hidden-import "tkinter" ^
    --hidden-import "darkdetect" ^
    --hidden-import "winreg" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --add-data "extension;extension" ^
    --add-data "firefox_extension;firefox_extension" ^
    --icon "extension\saiful_ext\icons\icon128.png;NONE" ^
    main.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo === Step 3/3: Build complete ===
echo.
echo   Your standalone executable is at:
echo.
echo       dist\SaifulDownloadManager.exe
echo.
echo   Copy this file anywhere on your PC and double-click to run.
echo   No Python installation needed.
echo.
echo   First launch will:
echo     - Start browser-integration server on port 9527
echo     - Auto-install extension into Chrome, Edge, Brave, Opera, Firefox
echo     - Show video overlay button on every video in your browser
echo     - Show download button next to direct download links
echo     - Monitor clipboard for download URLs
echo     - Show system tray icon
echo.
pause
