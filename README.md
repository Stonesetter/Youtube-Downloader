# YouTube Downloader (`ytdl`)

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/github/license/Stonesetter/Youtube-Downloader)](LICENSE)
[![Build and Release](https://github.com/Stonesetter/Youtube-Downloader/actions/workflows/release.yml/badge.svg)](https://github.com/Stonesetter/Youtube-Downloader/actions/workflows/release.yml)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](#installation)

Robust command-line YouTube downloader focused on learning, reliability, and practical defaults.

- Handles 1080p, 1440p, and 4K correctly (video + audio merge with `ffmpeg`)
- Works with long videos and playlists (resume + retries + parallel fragments)
- Includes auth/cookie support for age-restricted or login-required content
- Ships with setup scripts and cross-platform standalone binary build scripts

## Contents

- [What this project does](#what-this-project-does)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Quality profiles](#quality-profiles)
- [Config file](#config-file)
- [Troubleshooting](#troubleshooting)
- [Build standalone binaries](#build-standalone-binaries)
- [Release workflow](#release-workflow)
- [Project layout](#project-layout)
- [Legal and license](#legal-and-license)

## What this project does

`ytdl.py` is a wrapper around `yt-dlp` with:

- Safer defaults for high-quality downloads
- Friendly terminal output with `rich` progress bars
- Auto-detection of `ffmpeg` on common install paths
- Optional browser cookies or `cookies.txt` for protected videos
- Local config persistence (quality/output/container defaults)
- Optional background GitHub update check

## Requirements

This tool needs both Python packages and system tools.

| Dependency | Why it is needed | Required |
| --- | --- | --- |
| Python 3.8+ | Runs `ytdl.py` | Yes |
| `yt-dlp` | Core extraction/download engine | Yes |
| `rich` | Colored logs and progress display | Yes |
| `ffmpeg` | Merges separate video/audio streams (common for 1080p+) | Yes for most HD modes |
| Node.js (18+ recommended) | Solves YouTube JS challenge (`n` parameter) for normal speeds | Strongly recommended |

## Installation

### Option A: One-command setup script (recommended)

#### Windows

```powershell
git clone https://github.com/Stonesetter/Youtube-Downloader.git
cd Youtube-Downloader
.\setup.bat
```

Then run:

```powershell
.\ytdl.bat "https://youtu.be/VIDEO_ID"
```

#### Linux / WSL / macOS

```bash
git clone https://github.com/Stonesetter/Youtube-Downloader.git
cd Youtube-Downloader
chmod +x setup.sh
./setup.sh
```

The script adds a shell alias. Open a new terminal (or source your shell config), then run:

```bash
ytdl "https://youtu.be/VIDEO_ID"
```

### Option B: Install as a Python package

```bash
pip install git+https://github.com/Stonesetter/Youtube-Downloader.git
```

Then run:

```bash
ytdl --help
```

Note: You still need `ffmpeg` and Node.js installed on your system.

## Quick start

```bash
ytdl "https://youtu.be/VIDEO_ID"                  # default: 1080p MP4
ytdl "https://youtu.be/VIDEO_ID" -q 1440p         # 1440p
ytdl "https://youtu.be/VIDEO_ID" -q 4k --mkv      # 4K in MKV container
ytdl "https://youtu.be/VIDEO_ID" -q audio         # audio only (M4A)
ytdl "https://youtu.be/VIDEO_ID" --info           # inspect available streams
ytdl "https://youtu.be/PLAYLIST_ID" --playlist-end 5
```

## CLI reference

```text
usage: ytdl [-h] [-q QUALITY] [-o DIR] [--mkv] [--info] [--cookies BROWSER]
            [--cookies-file FILE] [--playlist-start N] [--playlist-end N]
            [--no-update-check] [--version] [--config]
            [url]
```

Key flags:

- `-q, --quality`: `360p|480p|720p|1080p|1440p|4k|best|audio`
- `-o, --output`: output directory
- `--mkv`: use MKV container instead of MP4
- `--info`: print metadata + formats without downloading
- `--cookies BROWSER`: import cookies from browser profile
- `--cookies-file FILE`: use Netscape-format `cookies.txt`
- `--playlist-start N`, `--playlist-end N`: partial playlist download
- `--config`: print config path and effective config values
- `--no-update-check`: skip background GitHub release check

## Quality profiles

| Quality | Selection strategy | Notes |
| --- | --- | --- |
| `360p`, `480p`, `720p` | Prefer muxed `video+audio`, fallback to separate streams | Most compatible |
| `1080p`, `1440p`, `4k`, `best` | Use `bestvideo+bestaudio` merge flow | Requires `ffmpeg` |
| `audio` | Extract best audio and convert to `m4a` | Uses `ffmpeg` |

## Config file

On first run, the tool creates a config file:

- Windows: `%APPDATA%\ytdl\config.json`
- Linux/macOS: `~/.config/ytdl/config.json`

View it any time:

```bash
ytdl --config
```

Default values:

```json
{
  "quality": "1080p",
  "output": ".",
  "container": "mp4",
  "concurrent_fragments": 4,
  "check_updates": true,
  "github_repo": "Stonesetter/Youtube-Downloader"
}
```

## Troubleshooting

### Slow downloads

- Check Node.js: `node --version`
- If missing, install Node.js and retry
- Without Node.js, YouTube may throttle heavily

### 1080p+ has no audio or merge fails

- Check `ffmpeg`: `ffmpeg -version`
- Install `ffmpeg`, then retry

### "Sign in" / bot check / private video errors

- Try browser cookies (Firefox recommended on Windows):
  - `ytdl URL --cookies firefox`
- If browser import fails, export and use cookies file:
  - `ytdl URL --cookies-file cookies.txt`

### Cookie extraction fails on Chrome (Windows)

Chrome can lock or encrypt its cookie database. Use Firefox cookie import or a manual `cookies.txt` export.

### Rate limiting (`429`) or regional restrictions

- `429`: wait a bit and retry
- Region-locked video: requires an allowed region/network

## Build standalone binaries

Use PyInstaller wrappers in this repo:

- Windows: `build.bat` -> `dist\ytdl-windows.exe`
- Linux/macOS: `build.sh` -> `dist/ytdl-linux` or `dist/ytdl-macos`

Binaries include Python + packages, but still require system `ffmpeg` and Node.js.

## Release workflow

This repository includes GitHub Actions release automation in `.github/workflows/release.yml`.

Typical release flow:

1. Bump `__version__` in `ytdl.py`
2. Commit
3. Tag: `git tag vX.Y.Z`
4. Push tags: `git push --tags`

The workflow builds Windows/Linux/macOS binaries and publishes a GitHub Release.

## Project layout

```text
ytdl.py              Main CLI program
setup.bat/.sh        One-command environment setup
build.bat/.sh        Standalone binary builders (PyInstaller)
pyproject.toml       Package metadata + console script entry point
requirements.txt     Python dependencies
.github/workflows/   Automated release pipeline
```

## Legal and license

- License: MIT (see `LICENSE`)
- Use responsibly and comply with local law and platform Terms of Service
- Intended for personal and educational use
