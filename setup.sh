#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup.sh — One-command setup for WSL (Ubuntu/Debian) and macOS
# ─────────────────────────────────────────────────────────────────────────────
# Run this script once to install all dependencies.
# Usage:
#   chmod +x setup.sh   (make it executable — only needed once)
#   ./setup.sh
#
# What this script does:
#   1. Installs ffmpeg    — needed to merge video+audio streams
#   2. Installs Node.js   — needed by yt-dlp to solve YouTube's speed throttle
#   3. Creates a Python virtual environment (.venv)
#   4. Installs Python dependencies (yt-dlp, rich)
#   5. Adds a 'ytdl' alias to your shell so you can run it from anywhere
# ─────────────────────────────────────────────────────────────────────────────

set -e  # Exit immediately if any command fails

# Terminal colors for friendly output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # No Color (reset)

info()    { echo -e "${CYAN}  →${NC} $1"; }
success() { echo -e "${GREEN}  ✓${NC} $1"; }
warn()    { echo -e "${YELLOW}  ⚠${NC} $1"; }
error()   { echo -e "${RED}  ✗${NC} $1"; }
header()  { echo -e "\n${BOLD}${CYAN}── $1 ──${NC}"; }

# Get the directory where THIS script lives (even if run from elsewhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BOLD}YouTube Downloader — Setup Script${NC}"
echo -e "Setting up in: ${CYAN}${SCRIPT_DIR}${NC}"
echo ""


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Check Python
# ─────────────────────────────────────────────────────────────────────────────
header "Checking Python"

# We need Python 3.8 or newer. The f-string improvements and walrus operator
# in 3.8 are used by yt-dlp internally.
PYTHON=""
for cmd in python3 python python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" -c "import sys; print(sys.version_info[:2])" 2>/dev/null)
        if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.8+ not found."
    if [[ "$OSTYPE" == "linux-gnu"* ]] || grep -qi microsoft /proc/version 2>/dev/null; then
        info "Install with: sudo apt install python3 python3-pip python3-venv"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        info "Install with: brew install python3"
    fi
    exit 1
fi

PY_VER=$("$PYTHON" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')")
success "Found Python ${PY_VER} at $(which $PYTHON)"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Install System Dependencies
# ─────────────────────────────────────────────────────────────────────────────
header "Installing System Dependencies"

# Detect OS
IS_WSL=false
IS_MACOS=false
IS_LINUX=false

if grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL=true
    info "Detected: WSL (Windows Subsystem for Linux)"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    IS_MACOS=true
    info "Detected: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    IS_LINUX=true
    info "Detected: Linux"
else
    warn "Unknown OS type: $OSTYPE. Attempting Linux-style install."
    IS_LINUX=true
fi

install_apt() {
    # Install ffmpeg and nodejs via apt (Ubuntu/Debian/WSL)
    info "Updating package list..."
    sudo apt-get update -qq

    if ! command -v ffmpeg &>/dev/null; then
        info "Installing ffmpeg..."
        sudo apt-get install -y ffmpeg
        success "ffmpeg installed"
    else
        success "ffmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
    fi

    if ! command -v node &>/dev/null; then
        info "Installing Node.js..."
        # Install Node.js 20 LTS via NodeSource for a recent version
        # (Ubuntu's default may be outdated)
        if command -v curl &>/dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
            sudo apt-get install -y nodejs
        else
            sudo apt-get install -y nodejs
        fi
        success "Node.js installed: $(node --version)"
    else
        success "Node.js already installed: $(node --version)"
    fi
}

install_brew() {
    # Install ffmpeg and nodejs via Homebrew (macOS)
    if ! command -v brew &>/dev/null; then
        error "Homebrew not found. Install it first: https://brew.sh"
        exit 1
    fi

    if ! command -v ffmpeg &>/dev/null; then
        info "Installing ffmpeg via brew..."
        brew install ffmpeg
        success "ffmpeg installed"
    else
        success "ffmpeg already installed"
    fi

    if ! command -v node &>/dev/null; then
        info "Installing Node.js via brew..."
        brew install node
        success "Node.js installed: $(node --version)"
    else
        success "Node.js already installed: $(node --version)"
    fi
}

if $IS_WSL || $IS_LINUX; then
    install_apt
elif $IS_MACOS; then
    install_brew
fi


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Python Virtual Environment
# ─────────────────────────────────────────────────────────────────────────────
header "Setting Up Python Virtual Environment"

# A virtual environment is an isolated Python installation just for this
# project. It keeps this project's dependencies separate from system Python,
# preventing version conflicts.

VENV_DIR="${SCRIPT_DIR}/.venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at .venv ..."
    "$PYTHON" -m venv "$VENV_DIR"
    success "Virtual environment created"
else
    success "Virtual environment already exists"
fi

# Activate the venv for this script session
source "${VENV_DIR}/bin/activate"

# Upgrade pip (the Python package installer) to latest version
info "Upgrading pip..."
pip install --upgrade pip --quiet
success "pip up to date"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Install Python Packages
# ─────────────────────────────────────────────────────────────────────────────
header "Installing Python Packages"

info "Installing yt-dlp and rich..."
pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet
success "Python packages installed"

# Confirm yt-dlp version
YTDLP_VER=$(python -c "import yt_dlp; print(yt_dlp.version.__version__)")
success "yt-dlp version: ${YTDLP_VER}"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Create Shell Alias
# ─────────────────────────────────────────────────────────────────────────────
header "Setting Up Shell Alias"

# The alias makes it so you can type 'ytdl URL' from any directory
# instead of the full path with python3.

ALIAS_CMD="alias ytdl='${VENV_DIR}/bin/python ${SCRIPT_DIR}/ytdl.py'"

# Detect which shell config file to use
SHELL_CONFIG=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
fi

if [ -n "$SHELL_CONFIG" ]; then
    # Remove any old ytdl alias to avoid duplicates
    grep -v "alias ytdl=" "$SHELL_CONFIG" > "${SHELL_CONFIG}.tmp" && mv "${SHELL_CONFIG}.tmp" "$SHELL_CONFIG"

    # Add the new alias
    echo "" >> "$SHELL_CONFIG"
    echo "# YouTube Downloader alias (added by setup.sh)" >> "$SHELL_CONFIG"
    echo "$ALIAS_CMD" >> "$SHELL_CONFIG"

    success "Alias added to $SHELL_CONFIG"
    warn "Run 'source ${SHELL_CONFIG}' or open a new terminal to activate it."
else
    warn "Could not find .bashrc or .zshrc. Add this manually:"
    echo ""
    echo "    $ALIAS_CMD"
    echo ""
fi


# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${GREEN}Setup complete!${NC}"
echo ""
echo -e "${BOLD}Quick start:${NC}"
echo ""
echo -e "  ${CYAN}source ~/.bashrc${NC}   (or open a new terminal)"
echo ""
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\"${NC}          # 1080p (default)"
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\" -q 1440p${NC} # 1440p"
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\" --info${NC}   # show formats"
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\" -q audio${NC} # audio only"
echo ""
echo -e "${BOLD}If downloads are slow:${NC}"
echo -e "  Make sure Node.js is installed: ${CYAN}node --version${NC}"
echo -e "  yt-dlp needs it to bypass YouTube's speed throttle."
echo ""
echo -e "${BOLD}If a video requires login:${NC}"
echo -e "  ${CYAN}ytdl URL --cookies chrome${NC}"
echo ""
