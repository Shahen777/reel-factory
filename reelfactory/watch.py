"""Let an AI agent "watch" a video: timestamped contact sheets + word-level transcript.

Claude Code and Codex cannot play video. This turns a file (or a public URL via yt-dlp) into
JPEG sheets with a timecode on every frame, a transcript with phrase timings and words.json.
Output folder: REPORT.md, info.txt, sheet_NN.jpg, dense_NN.jpg (optional), transcript.txt, words.json
"""
import argparse
import glob
import json
import math
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ffutil import font_path, probe, require, run


def grab(path, tmp, fps, start=None, end=None, w=240):
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(f"{tmp}/*.jpg"):
        os.remove(f)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(path)]
    if end is not None:
        cmd += ["-t", str(end - (start or 0))]
    cmd += ["-vf", f"fps={fps},scale={w}:-2", "-q:v", "3", f"{tmp}/f_%05d.jpg"]
    run(cmd)
    return sorted(glob.glob(f"{tmp}/f_*.jpg"))


def sheets(frames, t0, step, out_prefix, cols=6, rows=4):
    font = ImageFont.truetype(font_path("sans"), 18)
    outs, per = [], cols * rows
    for k in range(0, len(frames), per):
        ims = [Image.open(f).convert("RGB") for f in frames[k:k + per]]
        w, h = ims[0].size
        sheet = Image.new("RGB", (cols * (w + 4), math.ceil(len(ims) / cols) * (h + 4)), "white")
        for i, im in enumerate(ims):
            t = t0 + (k + i) * step
            d = ImageDraw.Draw(im)
            label = f"{int(t // 60)}:{t % 60:05.2f}"
            d.rectangle([0, 0, 8 + 11 * len(label), 24], fill="black")
            d.text((4, 2), label, font=font, fill="white")
            sheet.paste(im, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
        p = f"{out_prefix}_{k // per + 1:02d}.jpg"
        sheet.save(p, quality=85)
        outs.append(p)
    return outs


def transcribe(path, out, lang=None, model="small"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("[reel] speech needs faster-whisper: pip install faster-whisper (or use --no-audio)")
    wav = out / "audio.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-ar", "16000", str(wav)])
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, info = m.transcribe(str(wav), language=lang, word_timestamps=True, vad_filter=True)
    lines, words = [], []
    for s in segs:
        lines.append(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text.strip()}")
        words += [{"w": x.word.strip(), "s": round(x.start, 2), "e": round(x.end, 2)} for x in (s.words or [])]
    (out / "transcript.txt").write_text("\n".join(lines) or "(no speech found)", encoding="utf-8")
    json.dump(words, open(out / "words.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    wav.unlink()
    return info.language, len(words)


def download(url, folder):
    require("yt-dlp")
    folder.mkdir(parents=True, exist_ok=True)
    import subprocess
    r = subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                        "-o", str(folder / "video.%(ext)s"), url], capture_output=True, text=True)
    files = sorted(folder.glob("video.*"))
    if not files:
        raise SystemExit(f"[reel] could not download: {r.stderr.strip()[:300]}\n"
                         "Download the file yourself and pass its path.")
    return str(files[0])


def watch(src, out=None, fps=None, dense=None, lang=None, no_audio=False, model="small"):
    require("ffmpeg")
    if re.match(r"https?://", src):
        src = download(src, Path(out or "watch_download"))
    path = Path(src).expanduser().resolve()
    out = Path(out or f"watch_{path.stem}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    info = probe(str(path))
    dur = info["duration"]
    fps = fps or (2 if dur <= 20 else 1 if dur <= 90 else 0.5 if dur <= 300 else 0.2)
    (out / "info.txt").write_text(
        f"file: {path}\nduration: {dur:.2f} s\nsize: {info['w']}x{info['h']}\nfps: {info['fps']:.2f}\n"
        f"audio: {'yes' if info['has_audio'] else 'no'}\nsheet frames per second: {fps}\n", encoding="utf-8")
    sh = sheets(grab(path, out / "_frames", fps), 0.0, 1 / fps, str(out / "sheet"))
    dn = []
    if dense:
        s0, s1 = (float(x) for x in dense.split("-"))
        dn = sheets(grab(path, out / "_dense", 5, s0, s1, w=200), s0, 0.2, str(out / "dense"), cols=8, rows=5)
    lang_found, nw = None, 0
    if info["has_audio"] and not no_audio:
        lang_found, nw = transcribe(path, out, lang, model)
    for d in ("_frames", "_dense"):
        for f in glob.glob(str(out / d / "*.jpg")):
            os.remove(f)
        if (out / d).exists():
            (out / d).rmdir()
    rep = [f"# Watch: {path.name}", "", (out / "info.txt").read_text(encoding="utf-8"),
           "## Contact sheets (read in order)"] + [f"- {p}" for p in sh]
    if dn:
        rep += ["", f"## Dense frames {dense} s"] + [f"- {p}" for p in dn]
    rep += ["", f"## Speech (language: {lang_found or '-'}, words: {nw})",
            f"- {out / 'transcript.txt'}", f"- {out / 'words.json'}"]
    (out / "REPORT.md").write_text("\n".join(rep), encoding="utf-8")
    print("\n".join(rep))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel watch", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="video file or public URL")
    ap.add_argument("--out")
    ap.add_argument("--fps", type=float, help="sheet frames per second (default depends on length)")
    ap.add_argument("--dense", help="range for 5 fps frames, e.g. 3-6.5")
    ap.add_argument("--lang", help="speech language, e.g. ru, en, hy (auto by default)")
    ap.add_argument("--model", default="small", help="whisper model: tiny, base, small, medium, large-v3")
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args(argv)
    watch(a.src, a.out, a.fps, a.dense, a.lang, a.no_audio, a.model)


if __name__ == "__main__":
    main(sys.argv[1:])
