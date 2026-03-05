#!/usr/bin/env python3
"""
ytdl.py — A YouTube Downloader built for learning
===================================================
A free, open-source tool for downloading YouTube videos for personal and
educational use. Built to be understood, not just used.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW YOUTUBE VIDEO ACTUALLY WORKS — READ THIS FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. MPEG-DASH (Dynamic Adaptive Streaming over HTTP)
  ─────────────────────────────────────────────────
  YouTube does NOT serve your video as one big file. Instead, it uses a system
  called MPEG-DASH. The video is cut into small segments (a few seconds each)
  and stored at multiple quality levels on YouTube's CDN servers. As you
  watch, your browser monitors your internet speed and continuously picks the
  best quality segment it can receive without buffering. This is called
  Adaptive Bitrate (ABR) streaming.

  Why does this matter for downloading?
  Because you can't just "right-click → Save As" on a video URL. The URL
  points to a *manifest* (a list of segments), not a single video file.
  A downloader must fetch the manifest, collect all segment URLs, download
  them in order, and reassemble them into one file.

  2. SEPARATE VIDEO AND AUDIO STREAMS (above 720p)
  ─────────────────────────────────────────────────
  For resolutions of 1080p and above, YouTube stores video and audio in
  COMPLETELY SEPARATE FILES. This is the #1 reason most simple downloaders
  fail or produce silent videos at high quality.

    - Below 720p: One "muxed" file containing both video + audio (easy)
    - 1080p, 1440p, 4K: Two separate streams — you must download BOTH and
      then MERGE them using a tool called FFmpeg

  YouTube does this because it's more efficient — the audio track is tiny
  (~128 kbps), so why re-upload it 6 times just to pair it with each video
  quality level? Separate streams let YouTube serve one audio track to
  all users regardless of video quality choice.

  3. ITAG FORMAT CODES
  ─────────────────────────────────────────────────
  Every stream YouTube serves has an "itag" number identifying its format:
    Video only (DASH):
      137 = 1080p H.264 MP4     248 = 1080p VP9 WebM
      271 = 1440p VP9 WebM      313 = 2160p (4K) VP9 WebM
      401 = 2160p AV1 WebM      (AV1 = best compression, newest codec)
    Audio only (DASH):
      140 = 128 kbps AAC MP4    251 = 160 kbps Opus WebM (best quality)
    Muxed (video+audio, max 720p):
      22  = 720p H.264 MP4      18  = 360p H.264 MP4

  When we say "bestvideo+bestaudio", we're telling yt-dlp to find the best
  video-only itag AND the best audio-only itag, download both, and merge them.

  4. THE N-PARAMETER CHALLENGE (why you need Node.js)
  ─────────────────────────────────────────────────
  Since 2021, YouTube adds an "n" parameter to every stream URL. This is a
  JavaScript puzzle embedded in YouTube's player script (base.js). If your
  downloader requests a stream URL WITHOUT solving this puzzle, YouTube
  throttles the download to ~50 KB/s — slow enough to make a 1-hour 1080p
  video take 4+ hours to download. With the puzzle solved, you get full speed.

  The puzzle algorithm changes every week as YouTube updates base.js.
  yt-dlp downloads the current base.js, extracts the function, and runs it
  using an external JavaScript engine (Node.js by default in this tool).
  This is why setup.sh/setup.bat installs Node.js — it is not optional.

  5. THE SIGNATURE CIPHER (URL decryption)
  ─────────────────────────────────────────────────
  YouTube also encrypts stream URLs with a signature cipher. The decryption
  key is stored in base.js alongside the n-parameter function. yt-dlp
  extracts and applies both automatically. Without this, stream URLs return
  errors. This is invisible to the user but fundamental to how it works.

  6. PO TOKEN — YouTube's Newest Defense (2024)
  ─────────────────────────────────────────────────
  In 2024, YouTube added "Proof of Origin Tokens" (PoToken / BotGuard). This
  is a cryptographic challenge requiring browser JavaScript to prove the
  client is a real browser, not a bot. Some videos now require a valid PoToken
  or they cut off after only ~2MB of data.

  Workaround: pass --cookies with your browser name. yt-dlp extracts cookies
  from your browser's session, which include valid authentication tokens.

  IMPORTANT: Chrome on Windows often fails because Chrome locks its cookie
  database while running AND encrypts cookies with App-Bound Encryption
  (since Chrome 127, mid-2024). Firefox does NOT have this problem.

  Recommended:  python ytdl.py URL --cookies firefox
  Alternative:  Export cookies to a file with a browser extension like
                "Get cookies.txt LOCALLY", then:
                python ytdl.py URL --cookies-file cookies.txt

  7. WHY LONG VIDEOS FAIL IN OTHER TOOLS
  ─────────────────────────────────────────────────
  - N-parameter not solved → throttled to 50KB/s → timeouts on large files
  - Sequential segment downloads → slow with no retry on failure
  - Stream URLs expire after ~6 hours → must be refreshed mid-download
  - Memory-buffering entire video → crashes on files over a few hundred MB
  - Missing ffmpeg → cannot merge video+audio → silent or incomplete file
  - No resume support → network blips restart the whole download

  This tool uses yt-dlp which handles all of the above correctly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
License: MIT — free to use, modify, and distribute.
Project: https://github.com/Stonesetter/Youtube-Downloader
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ─────────────────────────────────────────────────────────────────────────────
# VERSION — update this when you make a release, then tag the commit in git:
#   git tag v1.0.1 && git push origin v1.0.1
# GitHub Actions will automatically build and publish the release binaries.
# ─────────────────────────────────────────────────────────────────────────────
__version__ = "1.0.0"

# When you create a GitHub repo, set this to "YourUsername/ytdl".
# The update checker pings the GitHub Releases API to compare versions.
# Leave as-is if you haven't published to GitHub yet.
UPDATE_REPO = "Stonesetter/Youtube-Downloader"

import argparse
import glob
import json
import os
import platform
import sys
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

# Force UTF-8 output on Windows so special characters (arrows, checkmarks, etc.)
# don't crash on legacy cp1252 terminals.  Must happen before any print calls.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# yt-dlp is the library doing all the heavy lifting. It's a fork of youtube-dl,
# actively maintained, and updated frequently to keep up with YouTube's changes.
try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp is not installed.")
    print("Run: pip install yt-dlp")
    sys.exit(1)

# rich gives us pretty terminal output — colored text and live progress bars.
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import (
        Progress,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
        TextColumn,
    )
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


# ─────────────────────────────────────────────────────────────────────────────
# QUALITY PROFILES
# ─────────────────────────────────────────────────────────────────────────────
#
# These are yt-dlp "format selector" strings. The syntax is:
#
#   bestvideo[height<=1080]+bestaudio/best[height<=1080]
#   │         │              │         │
#   │         │              │         └─ fallback: best combined stream ≤ height
#   │         │              └─────────── OR (try left side first, then right)
#   │         └────────────────────────── filter: only streams up to this height
#   └──────────────────────────────────── get the best video-only DASH stream
#
# The "+" means: download video-only + audio-only separately, merge with ffmpeg.
# The "/" means: if the left side fails, try the right side (fallback).

QUALITY_PROFILES = {
    # Muxed streams: video+audio combined, no ffmpeg required, max 720p.
    "360p": (
        "best[height<=360][vcodec!=none][acodec!=none]"
        "/bestvideo[height<=360]+bestaudio"
    ),
    "480p": (
        "best[height<=480][vcodec!=none][acodec!=none]"
        "/bestvideo[height<=480]+bestaudio"
    ),
    # 720p: prefer muxed for compatibility, fall back to separate streams.
    "720p": (
        "best[height<=720][vcodec!=none][acodec!=none]"
        "/bestvideo[height<=720]+bestaudio"
    ),

    # 1080p and above: ALWAYS separate video+audio streams.
    # There is no muxed version above 720p — YouTube doesn't provide one.
    # yt-dlp will download both streams and ffmpeg will merge them.
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "1440p": "bestvideo[height<=1440]+bestaudio/best",

    # 4K/2160p: AV1 codec preferred (better compression), VP9 as fallback.
    # Files can be very large — a 2-hour 4K video may be 15–30 GB.
    "4k":   "bestvideo[height<=2160]+bestaudio/best",

    # No height limit — takes whatever yt-dlp decides is absolute best quality.
    "best": "bestvideo+bestaudio/best",

    # Audio only. yt-dlp picks the highest-bitrate audio stream and
    # converts it to M4A (AAC) via ffmpeg. Lossless from source quality.
    "audio": "bestaudio/best",
}

# Qualities that require separate streams (and therefore ffmpeg + disk space)
HIGH_QUALITY = {"1080p", "1440p", "4k", "best"}


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG FILE
# ─────────────────────────────────────────────────────────────────────────────
#
# We store user preferences in a JSON config file so you don't have to type
# --quality 1440p every time. The file is created on first run with defaults.
#
# Config location:
#   Windows : %APPDATA%\ytdl\config.json
#   Linux   : ~/.config/ytdl/config.json
#   macOS   : ~/.config/ytdl/config.json

def _config_path() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ytdl" / "config.json"

CONFIG_FILE = _config_path()

DEFAULT_CONFIG = {
    # Default quality level. Change to "1440p" or "4k" if you usually want higher.
    "quality": "1080p",

    # Default output directory. "." means current working directory.
    # Change to e.g. "~/Videos" or "C:/Users/You/Videos".
    "output": ".",

    # Default container format. "mp4" works everywhere; "mkv" is more flexible.
    "container": "mp4",

    # How many video segments to download in parallel.
    # Higher = faster (on good connections), but uses more memory. 4 is safe.
    "concurrent_fragments": 4,

    # Whether to check GitHub for new releases on startup.
    "check_updates": True,

    # Your GitHub repo (set this after publishing). Used for update checks.
    "github_repo": UPDATE_REPO,
}


def load_config() -> dict:
    """Load config from disk, or create it with defaults if it doesn't exist."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults so new keys added in future versions appear
            config = {**DEFAULT_CONFIG, **saved}
            return config
        except (json.JSONDecodeError, OSError):
            # Corrupted config — use defaults
            pass
    else:
        # First run — create the config file
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            _print_info(f"Created config file: {CONFIG_FILE}")
            _print_info("Edit it to change default quality, output folder, etc.")
        except OSError:
            pass  # Not fatal — we'll just use defaults in memory

    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Write config dict back to disk."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        _print_info(f"Could not save config: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE CHECKER
# ─────────────────────────────────────────────────────────────────────────────
#
# This runs in a background thread so it never blocks your download.
# It calls the GitHub Releases API and compares the latest tag with our
# __version__. If there's a newer version, it prints a one-line notice.
#
# The GitHub Releases API is free, requires no auth for public repos, and
# returns JSON like: {"tag_name": "v1.0.1", "html_url": "https://..."}

def _version_tuple(v: str) -> tuple:
    """Convert "1.2.3" or "v1.2.3" to (1, 2, 3) for comparison."""
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def check_for_updates(repo: str, current_version: str) -> None:
    """
    Check GitHub releases for a newer version. Safe to call in a background
    thread — all errors are silently caught so they never interrupt a download.
    """
    if not repo:
        return  # No repo configured

    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"ytdl/{current_version}",
                "Accept": "application/vnd.github+json",
            },
        )
        # Short timeout — we never want the update check to delay a download
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        release_url = data.get("html_url", "")

        if not latest_tag:
            return

        if _version_tuple(latest_tag) > _version_tuple(current_version):
            # Print using plain print so it works even before rich is set up
            print(f"\n  Update available: v{current_version} → {latest_tag}")
            print(f"  Download: {release_url}\n")

    except Exception:
        # Network error, rate limit, malformed JSON — all silently ignored
        pass


# ─────────────────────────────────────────────────────────────────────────────
# FFMPEG AUTO-DETECTION
# ─────────────────────────────────────────────────────────────────────────────
#
# ffmpeg is a system binary (not a Python package) that yt-dlp uses to merge
# video and audio streams. It needs to be findable either in PATH or at a
# known location.
#
# On Windows, winget installs ffmpeg to a path that isn't immediately in PATH
# until you restart your terminal. This function scans common locations so
# ytdl.py works even right after installation without restarting.

def find_ffmpeg() -> str | None:
    """
    Return the directory containing ffmpeg, or None if not found.
    yt-dlp's 'ffmpeg_location' option takes the *directory*, not the binary.
    """
    import shutil

    # First: check if it's already in PATH (fastest, most common case)
    if shutil.which("ffmpeg"):
        return None  # None = let yt-dlp find it automatically via PATH

    if platform.system() == "Windows":
        # Scan locations where common Windows package managers install ffmpeg
        appdata_local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))

        search_roots = [
            # winget (Microsoft's official package manager)
            appdata_local / "Microsoft" / "WinGet" / "Packages",
            # Chocolatey
            Path("C:/ProgramData/chocolatey/bin"),
            # Scoop
            Path.home() / "scoop" / "shims",
            # Manual install locations
            Path("C:/ffmpeg/bin"),
            Path("C:/Program Files/ffmpeg/bin"),
            Path("C:/Program Files (x86)/ffmpeg/bin"),
        ]

        for root in search_roots:
            if not root.exists():
                continue

            # winget installs into versioned subdirectories, so we glob for ffmpeg.exe
            if "WinGet" in str(root):
                matches = list(root.glob("**/ffmpeg.exe"))
                if matches:
                    return str(matches[0].parent)
            else:
                # Direct bin directory check
                if (root / "ffmpeg.exe").exists():
                    return str(root)

    elif platform.system() == "Linux":
        # Common Linux locations (mostly covered by PATH, but just in case)
        for path in ["/usr/bin", "/usr/local/bin", "/snap/bin"]:
            if Path(path + "/ffmpeg").exists():
                return path

    elif platform.system() == "Darwin":  # macOS
        # Homebrew locations
        for path in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if Path(path + "/ffmpeg").exists():
                return path

    return None  # ffmpeg not found — yt-dlp will print its own warning


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
#
# yt-dlp calls our progress_hook function repeatedly during a download,
# passing a dict "d" with information about the current state.
#
# d['status'] can be:
#   'downloading' — currently downloading; d contains bytes/speed/eta info
#   'finished'    — this file is done (but ffmpeg merge may still run after)
#   'error'       — something went wrong

def make_progress_hook():
    """
    Returns a progress hook callback for yt-dlp.
    Uses rich's live Progress bar when available, plain text otherwise.
    """
    state = {
        "progress": None,
        "task_id": None,
        "last_filename": None,
    }

    def hook(d):
        if d["status"] == "downloading":
            filename = os.path.basename(d.get("filename", "unknown"))
            if len(filename) > 55:
                filename = filename[:52] + "..."

            if state["progress"] is None or state["last_filename"] != filename:
                if state["progress"] is not None:
                    state["progress"].stop()

                if RICH_AVAILABLE:
                    state["progress"] = Progress(
                        TextColumn("[bold cyan]{task.description}"),
                        BarColumn(bar_width=28),
                        DownloadColumn(),
                        TransferSpeedColumn(),
                        TimeRemainingColumn(),
                        expand=False,
                    )
                    state["progress"].start()
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    state["task_id"] = state["progress"].add_task(
                        filename, total=total or 0
                    )
                    state["last_filename"] = filename
                else:
                    print(f"  Downloading: {filename}")

            if RICH_AVAILABLE and state["progress"]:
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                if total:
                    state["progress"].update(
                        state["task_id"], completed=downloaded, total=total
                    )
                else:
                    mb = downloaded / (1024 * 1024)
                    state["progress"].update(
                        state["task_id"],
                        description=f"{filename} [{mb:.1f} MB downloaded]",
                    )

        elif d["status"] == "finished":
            if RICH_AVAILABLE and state["progress"]:
                state["progress"].stop()
                state["progress"] = None
            filename = os.path.basename(d.get("filename", "file"))
            _print_success(f"Stream saved: {filename}")
            _print_info("Merging video + audio with ffmpeg...")

        elif d["status"] == "error":
            if RICH_AVAILABLE and state["progress"]:
                state["progress"].stop()
                state["progress"] = None
            _print_error("Download error (see message above)")

    return hook


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _print_success(msg):
    if RICH_AVAILABLE:
        rprint(f"[bold green]✓[/bold green] {msg}")
    else:
        print(f"[OK] {msg}")

def _print_info(msg):
    if RICH_AVAILABLE:
        rprint(f"[dim]  {msg}[/dim]")
    else:
        print(f"    {msg}")

def _print_error(msg):
    if RICH_AVAILABLE:
        rprint(f"[bold red]✗[/bold red] {msg}")
    else:
        print(f"[ERROR] {msg}")

def _print_warn(msg):
    if RICH_AVAILABLE:
        rprint(f"[bold yellow]![/bold yellow] {msg}")
    else:
        print(f"[WARN] {msg}")

def _print_header(msg):
    if RICH_AVAILABLE:
        console.rule(f"[bold cyan]{msg}[/bold cyan]")
    else:
        print(f"\n{'─'*60}\n  {msg}\n{'─'*60}")


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO INFO DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def print_video_info(info: dict) -> None:
    """
    Pretty-print metadata and all available stream formats for a video.
    Called when the user passes --info. Shows everything yt-dlp knows about
    the video without downloading anything.

    This is a great way to understand YouTube's stream structure — you can
    see exactly which itag numbers are available and what they contain.
    """
    title      = info.get("title", "Unknown")
    channel    = info.get("channel", info.get("uploader", "Unknown"))
    duration   = info.get("duration", 0) or 0
    view_count = info.get("view_count", 0)
    upload_date = info.get("upload_date", "")

    hours, rem = divmod(int(duration), 3600)
    minutes, seconds = divmod(rem, 60)
    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

    if upload_date and len(upload_date) == 8:
        upload_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    else:
        upload_str = upload_date

    _print_header("Video Information")

    if RICH_AVAILABLE:
        rprint(f"[bold]Title   :[/bold] {title}")
        rprint(f"[bold]Channel :[/bold] {channel}")
        rprint(f"[bold]Duration:[/bold] {duration_str}")
        if upload_str:
            rprint(f"[bold]Uploaded:[/bold] {upload_str}")
        if view_count:
            rprint(f"[bold]Views   :[/bold] {view_count:,}")
    else:
        print(f"Title   : {title}")
        print(f"Channel : {channel}")
        print(f"Duration: {duration_str}")

    formats = info.get("formats", [])

    _print_header("Available Streams")
    _print_info(
        "YouTube serves video and audio as SEPARATE streams for 1080p+.\n"
        "  'video only' streams need an 'audio only' partner — ffmpeg merges them."
    )
    print()

    if RICH_AVAILABLE:
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("itag",       style="dim",      width=7)
        table.add_column("Resolution",                   width=12)
        table.add_column("Codec",                        width=10)
        table.add_column("Type",                         width=14)
        table.add_column("Est. Size",  justify="right",  width=10)
        table.add_column("FPS",        justify="right",  width=5)
        table.add_column("Container",                    width=8)

        for fmt in sorted(formats, key=lambda f: (f.get("height") or 0, f.get("abr") or 0)):
            itag     = str(fmt.get("format_id", "?"))
            height   = fmt.get("height")
            vcodec   = fmt.get("vcodec", "none")
            acodec   = fmt.get("acodec", "none")
            fps      = fmt.get("fps")
            filesize = fmt.get("filesize") or fmt.get("filesize_approx")
            ext      = fmt.get("ext", "?")

            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"

            if has_video and has_audio:
                stream_type = "[green]video+audio[/green]"
            elif has_video:
                stream_type = "[blue]video only[/blue]"
            elif has_audio:
                stream_type = "[yellow]audio only[/yellow]"
            else:
                continue  # skip metadata/storyboard rows

            res = f"{height}p" if height else "audio"

            codec = (vcodec if has_video else acodec) or "?"
            if "." in codec:
                codec = codec.split(".")[0]

            size_str = ""
            if filesize:
                if filesize >= 1_000_000_000:
                    size_str = f"{filesize/1_000_000_000:.1f} GB"
                else:
                    size_str = f"{filesize/1_000_000:.0f} MB"

            table.add_row(
                itag, res, codec, stream_type, size_str,
                str(int(fps)) if fps else "", ext,
            )

        console.print(table)
    else:
        print(f"{'itag':<8} {'Res':<10} {'Codec':<10} {'Type':<14} {'Est.Size':<10}")
        print("─" * 56)
        for fmt in sorted(formats, key=lambda f: f.get("height") or 0):
            itag   = str(fmt.get("format_id", "?"))
            height = fmt.get("height")
            vcodec = fmt.get("vcodec", "none")
            acodec = fmt.get("acodec", "none")
            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"
            if not (has_video or has_audio):
                continue
            t    = "video+audio" if (has_video and has_audio) else ("video only" if has_video else "audio only")
            res  = f"{height}p" if height else "audio"
            fs   = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            size = f"{fs/1_000_000:.0f}MB" if fs else ""
            codec = ((vcodec if has_video else acodec) or "?").split(".")[0]
            print(f"{itag:<8} {res:<10} {codec:<10} {t:<14} {size:<10}")


# ─────────────────────────────────────────────────────────────────────────────
# YT-DLP OPTIONS BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_ydl_opts(args: argparse.Namespace, config: dict, progress_hook=None) -> dict:
    """
    Build the options dictionary that controls yt-dlp's download behaviour.

    yt-dlp's YoutubeDL class takes a single dict with all settings.
    Every option is explained in a comment so you can understand (and tweak)
    what the downloader is doing.
    """
    container  = "mkv" if args.mkv else config.get("container", "mp4")
    output_dir = args.output or config.get("output", ".")
    quality    = args.quality or config.get("quality", "1080p")
    fragments  = config.get("concurrent_fragments", 4)

    # Expand "~" in paths (e.g. "~/Videos" → "/home/user/Videos")
    output_dir = os.path.expanduser(output_dir)

    # Output filename template.
    # %(title)s   → sanitised video title
    # %(id)s      → YouTube's 11-char video ID (unique, good for deduplication)
    # %(ext)s     → final container extension (mp4, mkv, m4a, etc.)
    outtmpl = os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s")

    opts: dict = {
        # ── FORMAT SELECTION ───────────────────────────────────────────────
        # This is the most important setting. It tells yt-dlp which stream(s)
        # to download. See QUALITY_PROFILES for what these strings mean.
        "format": QUALITY_PROFILES[quality],

        # ── OUTPUT ─────────────────────────────────────────────────────────
        "outtmpl": outtmpl,
        # Container for merged output. Both streams are copied losslessly —
        # no re-encoding happens, so this step is fast.
        "merge_output_format": container,

        # ── JAVASCRIPT RUNTIME ─────────────────────────────────────────────
        # yt-dlp needs a JavaScript engine to solve YouTube's n-parameter
        # challenge (without it: ~50 KB/s throttle on all downloads).
        # We prefer Node.js (installed by setup scripts), Deno as fallback.
        "js_runtimes": {"node": {}, "deno": {}},

        # ── REMOTE CHALLENGE SOLVER ────────────────────────────────────────
        # yt-dlp's EJS (External JS Support) system can download a challenge
        # solver script from GitHub. This script is kept up to date and handles
        # YouTube's frequently changing n-parameter and signature algorithms.
        # "ejs:github" = download the solver from yt-dlp's GitHub releases.
        # This requires internet access to GitHub (separate from YouTube).
        "remote_components": ["ejs:github"],

        # ── PARALLEL FRAGMENT DOWNLOADS ────────────────────────────────────
        # Download N segments simultaneously instead of one at a time.
        # This is critical for long/large videos — it prevents timeouts and
        # dramatically increases throughput on good connections.
        "concurrent_fragment_downloads": fragments,

        # ── RETRY LOGIC ────────────────────────────────────────────────────
        # How many times to retry on failure before giving up.
        # 10 retries handles most transient network issues.
        "retries": 10,
        "fragment_retries": 10,

        # ── RESUME INTERRUPTED DOWNLOADS ──────────────────────────────────
        # If ytdl.py crashes or you press Ctrl+C, the partial download is
        # saved as a .part file. Running the same command again resumes it.
        "continuedl": True,

        # ── POST-PROCESSING ─────────────────────────────────────────────────
        # These run after all streams are downloaded and merged.
        # FFmpegMetadata: embeds title, channel, description, upload date
        # into the file's metadata (shows in VLC, File Explorer, etc.)
        "postprocessors": [
            {"key": "FFmpegMetadata", "add_metadata": True},
        ],

        # ── PROGRESS ───────────────────────────────────────────────────────
        # Our hook handles display; suppress yt-dlp's own [download] lines
        # so both don't appear at the same time and clash on screen.
        "progress_hooks": [progress_hook] if progress_hook else [],
        "quiet": True,
        "no_warnings": False,
        "noprogress": True,  # suppress yt-dlp's internal progress output

        # ── SOCKET TIMEOUT ─────────────────────────────────────────────────
        # If a server doesn't respond within 30 seconds, move on.
        # Prevents hangs on stalled connections.
        "socket_timeout": 30,
    }

    # ── FFMPEG LOCATION ────────────────────────────────────────────────────
    # On Windows, ffmpeg might not be in PATH right after installation
    # (needs a terminal restart). We scan common install locations as fallback.
    ffmpeg_dir = find_ffmpeg()
    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir
        # Show a short path (last 2 components) so it doesn't wrap on narrow terminals
        short_path = "/".join(Path(ffmpeg_dir).parts[-2:])
        _print_info(f"Using ffmpeg from: .../{short_path}")

    # ── AUDIO EXTRACTION ───────────────────────────────────────────────────
    # For audio-only mode, add a post-processor that extracts the audio
    # and converts it to M4A (AAC). Change to "mp3" if you prefer MP3,
    # but M4A has better quality at the same file size.
    if quality == "audio":
        opts["postprocessors"].append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
            "preferredquality": "0",  # "0" = highest available quality
        })

    # ── COOKIES / AUTHENTICATION ──────────────────────────────────────────
    # Some videos require you to be logged in:
    #   - Age-restricted content
    #   - Members-only videos (YouTube Memberships)
    #   - Private videos you have access to
    #   - Videos where YouTube demands bot verification ("Sign in to confirm")
    #
    # Two ways to provide cookies:
    #
    # 1. --cookies BROWSER  (extract directly from your browser's cookie DB)
    #    Firefox is recommended. Chrome often fails on Windows because:
    #      a) Chrome locks its cookie database file while running
    #      b) Chrome 127+ uses App-Bound Encryption that yt-dlp can't decrypt
    #    See: https://github.com/yt-dlp/yt-dlp/issues/7271
    #
    # 2. --cookies-file FILE  (read a Netscape-format cookies.txt)
    #    Export with a browser extension like "Get cookies.txt LOCALLY",
    #    save as cookies.txt in this folder (it's gitignored — safe).
    #    This always works regardless of browser encryption.
    #
    if args.cookies_file:
        cookie_path = os.path.expanduser(args.cookies_file)
        if not os.path.isfile(cookie_path):
            _print_error(f"Cookie file not found: {cookie_path}")
            sys.exit(1)
        opts["cookiefile"] = cookie_path
        _print_info(f"Using cookies from file: {os.path.basename(cookie_path)}")
    elif args.cookies:
        opts["cookiesfrombrowser"] = (args.cookies, None, None, None)
        _print_info(f"Extracting cookies from {args.cookies}...")

    # ── PLAYLIST RANGE ─────────────────────────────────────────────────────
    if args.playlist_start:
        opts["playliststart"] = args.playlist_start
    if args.playlist_end:
        opts["playlistend"] = args.playlist_end

    return opts


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Load user config (creates config file with defaults on first run)
    config = load_config()

    # Kick off update check in the background — it prints a notice if there's
    # a newer version on GitHub. Runs in a daemon thread so it never blocks.
    if config.get("check_updates", True):
        repo = config.get("github_repo", UPDATE_REPO)
        update_thread = threading.Thread(
            target=check_for_updates,
            args=(repo, __version__),
            daemon=True,  # daemon=True means this thread dies when main() exits
        )
        update_thread.start()

    # ── ARGUMENT PARSER ───────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        prog="ytdl",
        description=(
            f"ytdl v{__version__} — YouTube Downloader (educational, open source)\n"
            "Supports 1080p–4K, long videos, playlists, and audio extraction.\n"
            "Requires: ffmpeg (merge streams) + Node.js (solve n-parameter)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
config file: {CONFIG_FILE}
  Edit this file to change default quality, output folder, etc.

examples:
  %(prog)s "https://youtu.be/VIDEO_ID"                  1080p MP4 (default)
  %(prog)s "https://youtu.be/VIDEO_ID" -q 1440p          1440p MP4
  %(prog)s "https://youtu.be/VIDEO_ID" -q 4k --mkv       4K MKV
  %(prog)s "https://youtu.be/VIDEO_ID" -q audio          audio only (M4A)
  %(prog)s "https://youtu.be/VIDEO_ID" --info             show all formats
  %(prog)s "https://youtu.be/VIDEO_ID" --cookies firefox   use Firefox login
  %(prog)s "https://youtu.be/VIDEO_ID" --cookies-file cookies.txt
  %(prog)s "https://youtu.be/PLAYLIST" --playlist-end 5   first 5 from playlist
  %(prog)s --version                                      show version
        """,
    )

    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")

    parser.add_argument(
        "-q", "--quality",
        choices=list(QUALITY_PROFILES.keys()),
        default=None,  # None = use config default
        metavar="QUALITY",
        help=(
            f"Quality: {', '.join(QUALITY_PROFILES.keys())}. "
            f"Config default: {config.get('quality', '1080p')}. "
            "1080p and above require ffmpeg."
        ),
    )

    parser.add_argument(
        "-o", "--output",
        default=None,  # None = use config default
        metavar="DIR",
        help=f"Output directory. Config default: {config.get('output', '.')}",
    )

    parser.add_argument(
        "--mkv",
        action="store_true",
        help="Output as MKV instead of MP4. MKV handles more codecs but is less universal.",
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Show video metadata and available formats WITHOUT downloading.",
    )

    parser.add_argument(
        "--cookies",
        metavar="BROWSER",
        help=(
            "Extract cookies from BROWSER for login-required videos. "
            "Firefox is recommended (Chrome often fails on Windows due to "
            "database locking and App-Bound Encryption). "
            "Values: firefox, chrome, edge, safari, brave, opera."
        ),
    )

    parser.add_argument(
        "--cookies-file",
        metavar="FILE",
        help=(
            "Path to a Netscape-format cookies.txt file. Use this if "
            "--cookies fails. Export from your browser with an extension like "
            "'Get cookies.txt LOCALLY'. This file is gitignored automatically."
        ),
    )

    parser.add_argument(
        "--playlist-start",
        type=int,
        metavar="N",
        help="Start at item N in a playlist (1-indexed).",
    )

    parser.add_argument(
        "--playlist-end",
        type=int,
        metavar="N",
        help="Stop after item N in a playlist.",
    )

    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help="Skip the GitHub update check on startup.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ytdl {__version__}",
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help=f"Show the path to the config file and its current contents.",
    )

    args = parser.parse_args()

    # ── CONFIG DISPLAY ─────────────────────────────────────────────────────
    if args.config:
        _print_header(f"Config file: {CONFIG_FILE}")
        print(json.dumps(config, indent=2))
        return

    # ── URL REQUIRED BELOW THIS POINT ──────────────────────────────────────
    if not args.url:
        parser.print_help()
        sys.exit(0)

    # ── OUTPUT DIRECTORY ───────────────────────────────────────────────────
    output_dir = os.path.expanduser(args.output or config.get("output", "."))
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            _print_info(f"Created output directory: {output_dir}")
        except OSError as e:
            _print_error(f"Cannot create output directory '{output_dir}': {e}")
            sys.exit(1)

    # ── RESOLVE EFFECTIVE QUALITY ──────────────────────────────────────────
    effective_quality = args.quality or config.get("quality", "1080p")

    # ── INFO MODE ──────────────────────────────────────────────────────────
    if args.info:
        _print_info("Fetching video information (no download will happen)...")
        info_opts = {
            "quiet": True,
            "js_runtimes": {"node": {}, "deno": {}},
            "remote_components": ["ejs:github"],
        }
        ffmpeg_dir = find_ffmpeg()
        if ffmpeg_dir:
            info_opts["ffmpeg_location"] = ffmpeg_dir
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            try:
                info = ydl.extract_info(args.url, download=False)
                info = ydl.sanitize_info(info)
            except yt_dlp.utils.DownloadError as e:
                _print_error(f"Could not fetch info: {e}")
                sys.exit(1)
        print_video_info(info)
        return

    # ── DOWNLOAD MODE ──────────────────────────────────────────────────────
    _print_header(f"ytdl v{__version__}")

    container  = "MKV" if args.mkv else config.get("container", "MP4").upper()
    output_dir = os.path.expanduser(args.output or config.get("output", "."))
    _print_info(
        f"Quality: {effective_quality.upper()}  |  "
        f"Container: {container}  |  "
        f"Output: {output_dir}"
    )

    if effective_quality in HIGH_QUALITY:
        _print_info(
            "High-quality mode: downloading separate video+audio streams. "
            "ffmpeg will merge them — this is fast and lossless."
        )

    # Let the background update check finish printing before we start
    # (cosmetic — gives it 0.5s to run, then we continue regardless)
    time.sleep(0.5)

    print()
    progress_hook = make_progress_hook()
    opts = build_ydl_opts(args, config, progress_hook)

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            # This is where everything happens:
            # 1. Fetch video page + decrypt signature cipher
            # 2. Solve n-parameter challenge via Node.js (enables full speed)
            # 3. Select best matching streams from QUALITY_PROFILES
            # 4. Download streams in parallel fragments (resumable)
            # 5. Merge with ffmpeg (fast copy, no re-encode)
            # 6. Embed metadata (title, channel, date)
            ydl.download([args.url])

        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            print()
            _print_error(msg)

            # Provide helpful context for common errors
            if "Could not copy" in msg and "cookie" in msg.lower():
                print()
                _print_warn("Could not read browser cookies.")
                _print_info("Chrome on Windows locks its cookie database while running")
                _print_info("and uses encryption that yt-dlp often can't decrypt.")
                print()
                _print_info("Fix 1 (easiest): Use Firefox instead of Chrome:")
                _print_info("  ytdl URL --cookies firefox")
                print()
                _print_info("Fix 2: Export cookies to a file manually:")
                _print_info("  1. Install browser extension 'Get cookies.txt LOCALLY'")
                _print_info("  2. Go to youtube.com (make sure you're logged in)")
                _print_info("  3. Click the extension → Export → save as cookies.txt")
                _print_info("  4. ytdl URL --cookies-file cookies.txt")

            elif "Sign in" in msg or "login" in msg.lower() or "bot" in msg.lower():
                print()
                _print_warn("YouTube wants you to prove you're not a bot.")
                _print_info("You need to pass your browser's login cookies.")
                print()
                _print_info("Option 1 (recommended): ytdl URL --cookies firefox")
                _print_info("Option 2 (if Chrome):    ytdl URL --cookies-file cookies.txt")
                _print_info("  (export cookies.txt with the 'Get cookies.txt LOCALLY' extension)")

            elif "Private video" in msg:
                print()
                _print_warn("This video is private.")
                _print_info("Use --cookies firefox (or --cookies-file) if you have access.")

            elif "429" in msg or "Too Many Requests" in msg:
                print()
                _print_warn("YouTube is rate-limiting this IP address.")
                _print_info("Wait a few minutes, then try again.")

            elif "not available" in msg.lower() and "country" in msg.lower():
                print()
                _print_warn("This video is geo-restricted.")
                _print_info("It is not available in your region.")

            elif "throttle" in msg.lower():
                print()
                _print_warn("Download is being throttled.")
                _print_info("Make sure Node.js is installed: node --version")
                _print_info("If missing: https://nodejs.org")

            sys.exit(1)

        except KeyboardInterrupt:
            print()
            _print_info("Cancelled. Partial data saved. Run again to resume.")
            sys.exit(0)

    print()
    _print_success(f"Done! File saved to: {output_dir}")


if __name__ == "__main__":
    main()
