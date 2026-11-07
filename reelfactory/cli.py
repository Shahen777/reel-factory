"""`reel` command line: one entry point for every tool."""
import importlib
import shutil
import sys

from . import __version__

COMMANDS = {
    "montage": ("reelfactory.montage", "render a beat-locked montage from an EDL JSON"),
    "auto": ("reelfactory.auto", "automatic montage from a folder of clips/photos + a music track"),
    "subtitles": ("reelfactory.subtitles", "transcribe speech and burn phrase subtitles"),
    "reframe": ("reelfactory.reframe", "remove black bars, convert to 9:16 / 4:5 / 1:1"),
    "export": ("reelfactory.export", "export for Reels / TikTok / Shorts (size, bitrate, -14 LUFS)"),
    "watch": ("reelfactory.watch", "contact sheets + transcript so an agent can review a video"),
    "motion": ("reelfactory.motion", "motion design from HTML/JS (written by Claude or Codex) to video"),
    "remotion": ("reelfactory.remotion", "beautiful animated text with Remotion: titles, captions, cards, lists"),
    "download": ("reelfactory.download", "download video/audio from YouTube, TikTok, Instagram... (yt-dlp)"),
    "batch": ("reelfactory.batch", "run many reel commands in parallel, with dependencies"),
    "crew": ("reelfactory.crew", "agent mode: many Claude Code / Codex agents work at once on one project"),
    "beats": ("reelfactory.cli", "print tempo and beat times of a track"),
    "voice": ("reelfactory.voice", "ElevenLabs voice-over (your API key)"),
    "kie": ("reelfactory.kie", "kie.ai images and video, price shown first (your API key)"),
    "doctor": ("reelfactory.cli", "check that ffmpeg and Python packages are installed"),
}


def doctor():
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        found = shutil.which(tool)
        print(f"{'ok ' if found else 'MISSING'} {tool:<16} {found or 'install: brew install ffmpeg / apt install ffmpeg'}")
        ok = ok and bool(found)
    print(f"{'ok ' if shutil.which('node') else 'opt'} {'node':<16} optional: reel remotion (Node.js 18+)")
    print(f"{'ok ' if shutil.which('yt-dlp') else 'opt'} {'yt-dlp':<16} optional: reel download, reel watch <url>")
    for mod, why in (("PIL", "required"), ("numpy", "required"), ("librosa", "required: beat detection"),
                     ("faster_whisper", "optional: subtitles, watch transcript"),
                     ("playwright", "optional: reel motion (then: playwright install chromium)")):
        try:
            importlib.import_module(mod)
            print(f"ok  {mod:<16} {why}")
        except ImportError:
            print(f"{'MISSING' if why.startswith('required') else 'opt'} {mod:<16} {why}")
            ok = ok and not why.startswith("required")
    print("all good" if ok else "fix the MISSING lines above (see README)")
    return 0 if ok else 1


def beats_cmd(argv):
    import argparse
    from .beats import beats_for
    ap = argparse.ArgumentParser(prog="reel beats")
    ap.add_argument("music")
    ap.add_argument("--first", type=int, default=32, help="how many beat times to print")
    a = ap.parse_args(argv)
    d = beats_for(a.music)
    print(f"tempo {d['tempo']:.1f} BPM, {len(d['beats'])} beats, track {d['duration']:.1f} s")
    print(" ".join(f"{b:.2f}" for b in d["beats"][:a.first]))


def usage():
    print(f"reel-factory {__version__}\n\nusage: reel <command> [options]   (reel <command> -h for help)\n")
    for k, (_, h) in COMMANDS.items():
        print(f"  {k:<10} {h}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help"):
        usage(); return 0
    if argv[0] in ("-V", "--version"):
        print(__version__); return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "doctor":
        return doctor()
    if cmd == "beats":
        return beats_cmd(rest)
    if cmd not in COMMANDS:
        usage(); return 2
    mod = importlib.import_module(COMMANDS[cmd][0])
    rc = mod.main(rest)
    return rc if isinstance(rc, int) else 0


if __name__ == "__main__":
    sys.exit(main() or 0)
