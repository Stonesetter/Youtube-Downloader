#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — Build a standalone ytdl binary for Linux/macOS/WSL
# ─────────────────────────────────────────────────────────────────────────────
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# Output: dist/ytdl-linux (or dist/ytdl-macos on macOS)
#
# HOW PYINSTALLER WORKS:
#   PyInstaller analyzes your Python script, follows all imports, and packages
#   everything — your code, yt-dlp, rich, and the Python interpreter itself —
#   into a single self-contained binary.
#
#   Users can run the binary without having Python installed.
#   They still need ffmpeg and Node.js (too large to bundle, and need to be
#   the right version for the OS they're on).
#
# SIZE NOTE:
#   The resulting binary is typically 30–60 MB because it includes Python.
#   This is normal for PyInstaller binaries.
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${SCRIPT_DIR}/.venv"

echo ""
echo "=== ytdl — Standalone Binary Builder ==="
echo ""

# Activate venv if it exists, otherwise use system Python
if [ -f "${VENV}/bin/activate" ]; then
    source "${VENV}/bin/activate"
    echo "  Using: .venv Python"
else
    echo "  WARNING: .venv not found. Run setup.sh first, or use system Python."
fi

# Install PyInstaller if not already installed
pip install pyinstaller --quiet
echo "  PyInstaller: ready"

# Determine output name
if [[ "$OSTYPE" == "darwin"* ]]; then
    BINARY_NAME="ytdl-macos"
else
    BINARY_NAME="ytdl-linux"
fi

echo "  Building: dist/${BINARY_NAME}"
echo ""

# yt-dlp uses dynamic imports that PyInstaller can't detect automatically.
# We tell PyInstaller about them explicitly with --hidden-import.
# --collect-submodules yt_dlp grabs everything in the yt_dlp package.
pyinstaller \
    --onefile \
    --console \
    --name "${BINARY_NAME}" \
    --hidden-import "yt_dlp.extractor" \
    --hidden-import "yt_dlp.postprocessor" \
    --hidden-import "yt_dlp.downloader" \
    --collect-submodules yt_dlp \
    --clean \
    "${SCRIPT_DIR}/ytdl.py"

echo ""
echo "=== Build complete ==="
echo ""
echo "Binary: dist/${BINARY_NAME}"
echo "Size:   $(du -sh "dist/${BINARY_NAME}" | cut -f1)"
echo ""
echo "Test it:"
echo "  ./dist/${BINARY_NAME} --version"
echo "  ./dist/${BINARY_NAME} --info 'https://youtube.com/watch?v=dQw4w9WgXcQ'"
echo ""
echo "To install system-wide (optional):"
echo "  sudo cp dist/${BINARY_NAME} /usr/local/bin/ytdl"
echo "  sudo chmod +x /usr/local/bin/ytdl"
echo ""
