@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: setup.bat — One-command setup for Windows
:: ─────────────────────────────────────────────────────────────────────────────
:: Run this file once to install all dependencies.
:: Double-click it, or run it from Command Prompt / PowerShell.
::
:: What this script does:
::   1. Checks for Python 3.8+
::   2. Installs ffmpeg via winget (needed to merge video+audio)
::   3. Installs Node.js via winget (needed to bypass YouTube speed throttle)
::   4. Creates a Python virtual environment (.venv)
::   5. Installs Python packages (yt-dlp, rich)
::   6. Shows usage examples
:: ─────────────────────────────────────────────────────────────────────────────

setlocal EnableDelayedExpansion
title YouTube Downloader — Setup

:: Get the directory where this .bat file lives
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo.
echo ============================================================
echo  YouTube Downloader -- Windows Setup
echo  Location: %SCRIPT_DIR%
echo ============================================================
echo.


:: ─────────────────────────────────────────────────────────────────────────────
:: STEP 1: Check Python
:: ─────────────────────────────────────────────────────────────────────────────
echo [1/5] Checking Python...

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Python not found.
    echo.
    echo   Install Python 3.8+ from: https://www.python.org/downloads/
    echo   During installation, CHECK "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo   OK  Python %PY_VER% found


:: ─────────────────────────────────────────────────────────────────────────────
:: STEP 2: Install ffmpeg
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo [2/5] Checking ffmpeg...

ffmpeg -version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   OK  ffmpeg already installed
) else (
    echo   ffmpeg not found. Attempting to install via winget...
    echo   (If prompted, allow the installer to run)
    echo.

    winget --version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo   WARNING: winget not available.
        echo   Please install ffmpeg manually:
        echo     1. Go to: https://ffmpeg.org/download.html
        echo     2. Download the Windows build
        echo     3. Extract and add the 'bin' folder to your PATH
        echo.
        echo   Without ffmpeg, 1080p+ downloads will not have audio.
        echo   Press any key to continue setup anyway...
        pause >nul
    ) else (
        winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        if %ERRORLEVEL% equ 0 (
            echo   OK  ffmpeg installed
            echo   NOTE: You may need to restart this window for ffmpeg to be recognized.
        ) else (
            echo   WARNING: ffmpeg installation may have failed.
            echo   Try installing manually from: https://ffmpeg.org/download.html
        )
    )
)


:: ─────────────────────────────────────────────────────────────────────────────
:: STEP 3: Install Node.js
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo [3/5] Checking Node.js...
echo   WHY: yt-dlp needs Node.js to solve YouTube's n-parameter challenge.
echo   Without it, all downloads are throttled to ~50KB/s.
echo.

node --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f %%v in ('node --version 2^>^&1') do set "NODE_VER=%%v"
    echo   OK  Node.js !NODE_VER! already installed
) else (
    echo   Node.js not found. Attempting to install via winget...

    winget --version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo   WARNING: winget not available.
        echo   Please install Node.js manually from: https://nodejs.org
        echo   Press any key to continue...
        pause >nul
    ) else (
        winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
        if %ERRORLEVEL% equ 0 (
            echo   OK  Node.js installed
            echo   NOTE: You may need to restart this window for node to be recognized.
        ) else (
            echo   WARNING: Node.js installation may have failed.
            echo   Install manually from: https://nodejs.org
        )
    )
)


:: ─────────────────────────────────────────────────────────────────────────────
:: STEP 4: Create Virtual Environment
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo [4/5] Setting up Python virtual environment...
echo   A virtual environment keeps this project's packages isolated
echo   from the rest of your system Python.

set "VENV_DIR=%SCRIPT_DIR%\.venv"

if not exist "%VENV_DIR%" (
    echo   Creating .venv ...
    python -m venv "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo   ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   OK  Virtual environment created at .venv
) else (
    echo   OK  Virtual environment already exists
)

:: Upgrade pip
echo   Upgrading pip...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip --quiet
echo   OK  pip up to date


:: ─────────────────────────────────────────────────────────────────────────────
:: STEP 5: Install Python Packages
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo [5/5] Installing Python packages (yt-dlp, rich)...

"%VENV_DIR%\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt" --quiet
if %ERRORLEVEL% neq 0 (
    echo   ERROR: Package installation failed.
    pause
    exit /b 1
)

:: Show installed yt-dlp version
for /f %%v in ('"%VENV_DIR%\Scripts\python.exe" -c "import yt_dlp; print(yt_dlp.version.__version__)"') do set "YTDLP_VER=%%v"
echo   OK  yt-dlp version: %YTDLP_VER%


:: ─────────────────────────────────────────────────────────────────────────────
:: CREATE HELPER BATCH FILE
:: ─────────────────────────────────────────────────────────────────────────────
:: We create a small ytdl.bat launcher so you can call "ytdl URL" from any
:: Command Prompt window (after adding it to PATH or using it directly).

set "LAUNCHER=%SCRIPT_DIR%\ytdl.bat"
echo @echo off > "%LAUNCHER%"
echo "%VENV_DIR%\Scripts\python.exe" "%SCRIPT_DIR%\ytdl.py" %%* >> "%LAUNCHER%"

echo.
echo   OK  Created launcher: ytdl.bat


:: ─────────────────────────────────────────────────────────────────────────────
:: DONE
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo  Setup complete!
echo ============================================================
echo.
echo  HOW TO USE:
echo.
echo  Option A — use ytdl.bat directly from this folder:
echo    ytdl.bat "https://youtube.com/watch?v=VIDEO_ID"
echo.
echo  Option B — run with full Python path (always works):
echo    "%VENV_DIR%\Scripts\python.exe" "%SCRIPT_DIR%\ytdl.py" URL
echo.
echo  EXAMPLES:
echo    ytdl.bat "https://youtu.be/VIDEO_ID"                    1080p (default)
echo    ytdl.bat "https://youtu.be/VIDEO_ID" -q 1440p           1440p video
echo    ytdl.bat "https://youtu.be/VIDEO_ID" -q audio           audio only
echo    ytdl.bat "https://youtu.be/VIDEO_ID" --info             show formats
echo    ytdl.bat "https://youtu.be/VIDEO_ID" --cookies chrome   use login cookies
echo.
echo  IF DOWNLOADS ARE SLOW:
echo    Make sure Node.js is working: open a NEW Command Prompt and run:
echo      node --version
echo    If missing, install from: https://nodejs.org
echo.
echo ============================================================
echo.
pause
