@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: build.bat — Build a standalone ytdl.exe for Windows
:: ─────────────────────────────────────────────────────────────────────────────
:: Usage: Double-click build.bat, or run from Command Prompt.
::
:: Output: dist\ytdl-windows.exe
::
:: HOW PYINSTALLER WORKS:
::   PyInstaller bundles Python + your script + all installed packages into
::   a single .exe file. Users don't need Python installed to run it.
::   They still need ffmpeg and Node.js (too platform-specific to bundle).
::
:: SIZE: The .exe will be ~30-60 MB. This is normal — it contains Python.
:: ─────────────────────────────────────────────────────────────────────────────

setlocal
title ytdl — Build Standalone EXE

set "SCRIPT_DIR=%~dp0"
set "VENV=%SCRIPT_DIR%.venv"

echo.
echo === ytdl -- Standalone EXE Builder ===
echo.

:: Use venv Python if available
if exist "%VENV%\Scripts\python.exe" (
    set "PYTHON=%VENV%\Scripts\python.exe"
    set "PIP=%VENV%\Scripts\pip.exe"
    echo   Using: .venv Python
) else (
    set "PYTHON=python"
    set "PIP=pip"
    echo   WARNING: .venv not found. Run setup.bat first for best results.
)

:: Install PyInstaller
echo   Installing PyInstaller...
"%PIP%" install pyinstaller --quiet

echo   Building: dist\ytdl-windows.exe
echo.

:: yt-dlp uses dynamic imports that PyInstaller can't detect automatically.
:: --hidden-import tells PyInstaller about them explicitly.
:: --collect-submodules yt_dlp bundles the entire yt_dlp package.
:: --onefile bundles everything into a single .exe (vs a folder of DLLs).
"%PYTHON%" -m PyInstaller ^
    --onefile ^
    --console ^
    --name ytdl-windows ^
    --hidden-import "yt_dlp.extractor" ^
    --hidden-import "yt_dlp.postprocessor" ^
    --hidden-import "yt_dlp.downloader" ^
    --collect-submodules yt_dlp ^
    --clean ^
    "%SCRIPT_DIR%ytdl.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Build failed. See output above.
    pause
    exit /b 1
)

echo.
echo === Build complete! ===
echo.
echo   Binary: dist\ytdl-windows.exe
echo.
echo   Test it:
echo     dist\ytdl-windows.exe --version
echo     dist\ytdl-windows.exe --info "https://youtube.com/watch?v=dQw4w9WgXcQ"
echo.
echo   To distribute: share dist\ytdl-windows.exe
echo   Users still need ffmpeg + Node.js installed separately.
echo.
pause
