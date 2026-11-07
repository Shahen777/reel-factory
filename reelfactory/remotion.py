"""Beautiful animated text with Remotion (React): kinetic titles, word-by-word captions, title cards, lists.

  reel remotion list
  reel remotion KineticTitle --set 'lines=["BIG","*IDEA*"]' --music track.mp3 --out out/title.mp4
  reel remotion Captions --video talk.mp4 --words out/talk.mp4.words.json --set style=pill --out out/caps.mp4
  reel remotion Captions --video talk.mp4 --transcribe --lang ru          (runs Whisper first)
  reel remotion TextReveal --set title="AUTUMN 26" --set subtitle="From Friday" --transparent --out out/card.mov
  reel remotion studio                                                     (live editor in the browser)

Needs Node.js 18+ (first run installs the Remotion packages in ./remotion).
Remotion is free for individuals and companies up to 3 people; bigger companies need a Remotion company licence.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

from .motion import parse_set

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.join(os.path.dirname(HERE), "remotion")
COMPS = {
    "KineticTitle": "letters spring in line by line; lines[], perLine, size, y, accent, gradient",
    "Captions": "word-by-word captions over a video; words[], style pill|pop|clean, wordsPerPhrase, y, size",
    "TextReveal": "premium title card with mask reveal; kicker, title, subtitle, accent",
    "ListStack": "title + items stacking one by one; title, items[], perItem, numbered",
}
FILE_PROPS = ("video", "music")
# example texts in Root.tsx defaultProps must not leak into a user's render
BLANK_IF_MISSING = {"TextReveal": ("kicker", "subtitle"), "ListStack": ("title",)}


def _need_project():
    if not os.path.exists(os.path.join(PROJECT, "package.json")):
        raise SystemExit("[reel] remotion/ folder not found. Use a git clone of reel-factory (not a pip wheel).")
    if not shutil.which("npx"):
        raise SystemExit("[reel] Node.js is missing. macOS: brew install node | Ubuntu: sudo apt install nodejs npm | "
                         "Windows: winget install OpenJS.NodeJS.LTS")
    if not os.path.isdir(os.path.join(PROJECT, "node_modules")):
        print("[reel] first run: installing Remotion packages (npm install)...", flush=True)
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=PROJECT, check=True)


def _stage(path):
    """Copy a local file into remotion/public/_in/ and return its public name."""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise SystemExit(f"[reel] file not found: {path}")
    h = hashlib.md5((path + str(os.path.getmtime(path))).encode()).hexdigest()[:10]
    name = f"_in/{h}{os.path.splitext(path)[1].lower()}"
    dest = os.path.join(PROJECT, "public", name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(path, dest)
    return name


def load_words(path):
    """Accept words.json from `reel watch` ({w,s,e}) or `reel subtitles` ({word,start,end})."""
    raw = json.load(open(path, encoding="utf-8"))
    out = []
    for x in raw:
        w = x.get("w", x.get("word", "")).strip()
        if w:
            out.append({"w": w, "s": float(x.get("s", x.get("start", 0))), "e": float(x.get("e", x.get("end", 0)))})
    return out


def render(comp, out, props, transparent=False, quiet=False):
    _need_project()
    for k in FILE_PROPS:
        if props.get(k):
            props[k] = _stage(props[k])
    if transparent:
        props["background"] = "transparent"
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pfile = os.path.join(PROJECT, "public", "_in", "props_%s.json" % hashlib.md5(out.encode()).hexdigest()[:8])
    os.makedirs(os.path.dirname(pfile), exist_ok=True)
    json.dump(props, open(pfile, "w", encoding="utf-8"), ensure_ascii=False)
    cmd = ["npx", "remotion", "render", "src/index.ts", comp, out, f"--props={pfile}"]
    if transparent:
        cmd += ["--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png"]
    else:
        cmd += ["--codec=h264", "--crf=16"]
    if quiet:
        cmd.append("--log=error")
    r = subprocess.run(cmd, cwd=PROJECT)
    if r.returncode != 0:
        raise SystemExit("[reel] remotion render failed")
    print(f"[reel] OUT {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel remotion", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comp", help="composition name, `list` or `studio`")
    ap.add_argument("--out")
    ap.add_argument("--props", help="JSON file with props")
    ap.add_argument("--set", action="append", metavar="KEY=VALUE", help="one prop (repeatable, JSON values allowed)")
    ap.add_argument("--video", help="background video")
    ap.add_argument("--music", help="music track")
    ap.add_argument("--words", help="words.json for Captions")
    ap.add_argument("--transcribe", action="store_true", help="Captions: transcribe --video with Whisper first")
    ap.add_argument("--lang", help="speech language for --transcribe")
    ap.add_argument("--duration", type=float, help="seconds (default: from the content)")
    ap.add_argument("--transparent", action="store_true", help="alpha channel, ProRes 4444 .mov")
    a = ap.parse_args(argv)
    if a.comp == "list":
        for k, v in COMPS.items():
            print(f"  {k:<13} {v}")
        return
    if a.comp == "studio":
        _need_project()
        subprocess.run(["npx", "remotion", "studio", "src/index.ts"], cwd=PROJECT)
        return
    if a.comp not in COMPS:
        raise SystemExit(f"[reel] unknown composition {a.comp}; see `reel remotion list`")
    props = json.load(open(a.props, encoding="utf-8")) if a.props else {}
    props.update(parse_set(a.set))
    if a.video:
        props["video"] = a.video
    if a.music:
        props["music"] = a.music
    if a.duration:
        props["durationInSeconds"] = a.duration
    if a.comp == "Captions":
        if a.transcribe and not a.words:
            if not a.video:
                raise SystemExit("[reel] --transcribe needs --video")
            from .subtitles import main as subs
            base = os.path.join("out", os.path.splitext(os.path.basename(a.video))[0] + "_words")
            subs([a.video, "--srt-only", "--out", base + ".mp4"] + (["--lang", a.lang] if a.lang else []))
            a.words = base + ".mp4.words.json"
        if a.words:
            props["words"] = load_words(a.words)
        if a.video and not a.duration:
            from .ffutil import probe
            props["durationInSeconds"] = round(probe(a.video)["duration"], 3)
    if props:
        for k in BLANK_IF_MISSING.get(a.comp, ()):
            props.setdefault(k, "")
    out = a.out or os.path.join("out", a.comp + (".mov" if a.transparent else ".mp4"))
    render(a.comp, out, props, a.transparent)


if __name__ == "__main__":
    main(sys.argv[1:])
