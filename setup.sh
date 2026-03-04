#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup.sh — One-command setup for Ubuntu, Debian, WSL, and macOS
# ─────────────────────────────────────────────────────────────────────────────
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# What this script does:
#   1. Installs python3-venv + python3-pip (often missing on fresh Ubuntu)
#   2. Installs ffmpeg          — merges video+audio streams for 1080p+
#   3. Installs Node.js 20 LTS  — yt-dlp needs it to bypass speed throttle
#   4. Creates a Python virtual environment (.venv)
#   5. Installs Python packages (yt-dlp, rich)
#   6. Adds a 'ytdl' alias to your shell
# ─────────────────────────────────────────────────────────────────────────────

# Do NOT use set -e (exit on error) globally — it causes spurious failures
# in many places (grep returning 1 when no match, NodeSource warnings, etc.).
# Instead we check exit codes explicitly where it matters.

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}  →${NC} $1"; }
success() { echo -e "${GREEN}  ✓${NC} $1"; }
warn()    { echo -e "${YELLOW}  !${NC} $1"; }
error()   { echo -e "${RED}  ✗${NC} $1"; }
header()  { echo -e "\n${BOLD}${CYAN}── $1 ──${NC}"; }
die()     { error "$1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BOLD}YouTube Downloader — Setup Script${NC}"
echo -e "Location: ${CYAN}${SCRIPT_DIR}${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# DETECT OS
# ─────────────────────────────────────────────────────────────────────────────
IS_WSL=false
IS_MACOS=false
IS_LINUX=false

if grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL=true
    info "Detected: WSL"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    IS_MACOS=true
    info "Detected: macOS"
else
    IS_LINUX=true
    info "Detected: Linux"
fi

# Determine if we need sudo (root doesn't need it)
SUDO=""
if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Check Python
# ─────────────────────────────────────────────────────────────────────────────
header "Checking Python"

PYTHON=""
for cmd in python3 python python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    die "Python 3.8+ not found. Install it: sudo apt install python3"
fi

PY_VER=$("$PYTHON" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')")
success "Found Python ${PY_VER}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Install System Dependencies (apt / brew)
# ─────────────────────────────────────────────────────────────────────────────
header "Installing System Dependencies"

install_apt() {
    info "Updating package list..."
    $SUDO apt-get update -qq || warn "apt-get update had warnings (continuing)"

    # ── python3-venv and python3-pip ─────────────────────────────────────────
    # On Ubuntu, 'python3' is installed but these are separate packages.
    # Without python3-venv, `python3 -m venv` fails silently or with a
    # confusing error about "ensurepip not available".
    info "Installing python3-venv and python3-pip..."
    $SUDO apt-get install -y python3-venv python3-pip 2>/dev/null \
        || warn "Could not install python3-venv via apt (may already be present)"

    # ── ffmpeg ──────────────────────────────────────────────────────────────
    if command -v ffmpeg &>/dev/null; then
        success "ffmpeg already installed"
    else
        info "Installing ffmpeg..."
        $SUDO apt-get install -y ffmpeg \
            || die "Failed to install ffmpeg. Try: sudo apt install ffmpeg"
        success "ffmpeg installed"
    fi

    # ── Node.js ─────────────────────────────────────────────────────────────
    # yt-dlp needs Node.js to solve YouTube's n-parameter JS challenge.
    # Without it, downloads are throttled to ~50 KB/s regardless of internet speed.
    #
    # We try three methods in order:
    #   1. Already installed and recent enough (>=18)?  Done.
    #   2. System nodejs package  (Ubuntu 24.04+ ships Node 18 — good enough)
    #   3. NodeSource LTS         (fallback for older distros like Ubuntu 22.04)

    _node_version_ok() {
        # Returns 0 if `node` is installed and version >= 18
        if ! command -v node &>/dev/null; then return 1; fi
        local major
        major=$(node --version 2>/dev/null | tr -d 'v' | cut -d. -f1)
        [[ "${major:-0}" -ge 18 ]]
    }

    if _node_version_ok; then
        success "Node.js already installed: $(node --version)"
        return
    fi

    info "Installing Node.js..."

    # Method 1: system package (fast, works on Ubuntu 24.04+ which ships Node 18)
    $SUDO apt-get install -y nodejs 2>/dev/null
    if _node_version_ok; then
        success "Node.js installed via apt: $(node --version)"
        return
    fi

    # Method 2: NodeSource LTS (works on Ubuntu 20.04, 22.04, Debian 11/12)
    # NodeSource changed their install method in 2023. The old setup_20.x URL
    # still redirects but may have issues. We use the current recommended method.
    warn "System nodejs is too old. Trying NodeSource LTS..."

    if command -v curl &>/dev/null; then
        # Download the NodeSource setup script and run it
        # 'nodesource_setup.sh' auto-detects your distro and adds the right repo
        curl -fsSL https://deb.nodesource.com/setup_lts.x -o /tmp/nodesource_setup.sh 2>/dev/null \
            && $SUDO bash /tmp/nodesource_setup.sh 2>/dev/null \
            && $SUDO apt-get install -y nodejs 2>/dev/null \
            && rm -f /tmp/nodesource_setup.sh \
            || true  # don't die — we'll check below and warn if still missing
    fi

    if _node_version_ok; then
        success "Node.js installed via NodeSource: $(node --version)"
    else
        warn "Could not install Node.js automatically."
        warn "Install it manually: https://nodejs.org/en/download"
        warn "Without Node.js, downloads will be throttled to ~50 KB/s."
    fi
}

install_brew() {
    if ! command -v brew &>/dev/null; then
        die "Homebrew not found. Install it first: https://brew.sh"
    fi

    if command -v ffmpeg &>/dev/null; then
        success "ffmpeg already installed"
    else
        info "Installing ffmpeg via brew..."
        brew install ffmpeg || die "brew install ffmpeg failed"
        success "ffmpeg installed"
    fi

    if command -v node &>/dev/null; then
        success "Node.js already installed: $(node --version)"
    else
        info "Installing Node.js via brew..."
        brew install node || warn "brew install node failed — install manually from nodejs.org"
        command -v node &>/dev/null && success "Node.js installed: $(node --version)"
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

# A virtual environment isolates this project's Python packages from the
# rest of the system. Each user has their own, and it never conflicts with
# packages installed via apt or pip at the system level.

VENV_DIR="${SCRIPT_DIR}/.venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at .venv ..."
    "$PYTHON" -m venv "$VENV_DIR" \
        || die "Failed to create virtual environment. Try: sudo apt install python3-venv"
    success "Virtual environment created"
else
    success "Virtual environment already exists"
fi

# Activate the venv for the rest of this script
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate" \
    || die "Could not activate virtual environment"

# Upgrade pip inside the venv (the venv's pip may be older than the system pip)
info "Upgrading pip..."
pip install --upgrade pip --quiet 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Install Python Packages
# ─────────────────────────────────────────────────────────────────────────────
header "Installing Python Packages"

info "Installing yt-dlp and rich..."
pip install -r "${SCRIPT_DIR}/requirements.txt" \
    || die "Failed to install Python packages. Check your internet connection."

YTDLP_VER=$(python -c "import yt_dlp; print(yt_dlp.version.__version__)" 2>/dev/null || echo "unknown")
success "yt-dlp ${YTDLP_VER}"
success "Python packages installed"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Shell Alias
# ─────────────────────────────────────────────────────────────────────────────
header "Setting Up Shell Alias"

ALIAS_CMD="alias ytdl='${VENV_DIR}/bin/python ${SCRIPT_DIR}/ytdl.py'"

# Find the right shell config file
SHELL_CONFIG=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
fi

if [ -n "$SHELL_CONFIG" ]; then
    # Remove old ytdl alias (grep -v returns 1 if no lines matched — that's fine,
    # so we use '|| true' to prevent the script from dying on a clean install)
    grep -v "alias ytdl=" "$SHELL_CONFIG" > "${SHELL_CONFIG}.tmp" 2>/dev/null || true
    mv "${SHELL_CONFIG}.tmp" "$SHELL_CONFIG"

    echo "" >> "$SHELL_CONFIG"
    echo "# YouTube Downloader alias (added by setup.sh)" >> "$SHELL_CONFIG"
    echo "$ALIAS_CMD" >> "$SHELL_CONFIG"

    success "Alias added to $SHELL_CONFIG"
    warn "Run: source ${SHELL_CONFIG}  (or open a new terminal)"
else
    warn "Could not find .bashrc or .zshrc. Add this alias manually:"
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
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\"${NC}           # 1080p (default)"
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\" -q 1440p${NC}  # 1440p"
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\" --info${NC}    # show formats"
echo -e "  ${CYAN}ytdl \"https://youtube.com/watch?v=VIDEO_ID\" -q audio${NC}  # audio only"
echo ""
echo -e "${BOLD}Trouble with slow downloads?${NC}"
echo -e "  Check Node.js is installed: ${CYAN}node --version${NC}"
echo ""
echo -e "${BOLD}Video requires login?${NC}"
echo -e "  ${CYAN}ytdl URL --cookies firefox${NC}"
echo ""
