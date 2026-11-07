"""Small helpers around ffmpeg / ffprobe shared by every command."""
import json
import os
import shutil
import subprocess
import sys

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

FONT_ALIASES = {
    "display": os.path.join(ASSETS, "fonts", "RussoOne-Regular.ttf"),
    "sans": os.path.join(ASSETS, "fonts", "PTSans-Bold.ttf"),
    # common system fonts, used only if present
    "Impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
    "ArialBlack": "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "Futura": "/System/Library/Fonts/Supplemental/Futura.ttc",
    "DIN": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
    "DejaVu": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def font_path(name):
    """Resolve a font alias or a path. Falls back to the bundled display font."""
    if not name:
        return FONT_ALIASES["display"]
    p = FONT_ALIASES.get(name, name)
    p = os.path.expanduser(p)
    if os.path.exists(p):
        return p
    print(f"[reel] font '{name}' not found, using bundled display font", file=sys.stderr)
    return FONT_ALIASES["display"]


def require(tool):
    if shutil.which(tool) is None:
        raise SystemExit(f"[reel] '{tool}' is not installed. See README: Installation.")


def run(cmd, quiet=True):
    """Run a command; on failure print the tail of stderr and exit."""
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        print(" ".join(str(c) for c in cmd), file=sys.stderr)
        print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"[reel] {os.path.basename(str(cmd[0]))} failed ({r.returncode})")
    return r


def probe(path):
    """Return dict: w, h (after rotation side data), duration, fps, has_audio, rotation."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate:stream_side_data=rotation:format=duration",
         "-of", "json", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    j = json.loads(r.stdout or "{}")
    streams = j.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    w, h = int(v.get("width", 0) or 0), int(v.get("height", 0) or 0)
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    if abs(rot) % 180 == 90:
        w, h = h, w
    fps = 30.0
    rf = v.get("r_frame_rate", "30/1")
    try:
        a, b = rf.split("/")
        fps = float(a) / float(b) if float(b) else 30.0
    except ValueError:
        pass
    return {
        "w": w, "h": h, "rotation": rot, "fps": fps,
        "duration": float(j.get("format", {}).get("duration", 0) or 0),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in PHOTO_EXT:
        return "photo"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def load_env(path=".env"):
    """Minimal .env loader (KEY=VALUE lines) so users need no extra package."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
