"""Remove black bars and reframe any video to vertical 9:16 (or another aspect).

Modes:
  auto   detect bars with cropdetect, crop them, then fit to the target aspect
  crop   fill the frame by cropping (centre at --cx/--cy)
  blur   keep the whole picture, fill the rest with a blurred copy
  bars   only remove the black bars, keep the remaining size
"""
import argparse
import collections
import os
import re
import subprocess
import sys

from .ffutil import probe, require, run


def detect_bars(path, samples=12, limit=24):
    """Return (w, h, x, y) of the picture area without black bars, or None."""
    info = probe(path)
    dur = max(info["duration"], 0.1)
    votes = collections.Counter()
    for i in range(samples):
        t = dur * (i + 0.5) / samples
        r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "6",
                            "-vf", f"cropdetect=limit={limit}:round=2:reset=0", "-f", "null", "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        found = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
        if found:
            votes[tuple(int(v) for v in found[-1])] += 1
    if not votes:
        return None
    w, h, x, y = votes.most_common(1)[0][0]
    if w >= info["w"] - 4 and h >= info["h"] - 4:
        return None
    return w, h, x, y


def build_filter(src_w, src_h, W, H, mode, cx=0.5, cy=0.5, bars=None):
    pre = []
    if bars:
        bw, bh, bx, by = bars
        pre.append(f"crop={bw}:{bh}:{bx}:{by}")
        src_w, src_h = bw, bh
    pre_s = (",".join(pre) + ",") if pre else ""
    if mode == "bars":
        return f"[0:v]{pre_s}setsar=1[v]", (src_w // 2 * 2, src_h // 2 * 2)
    if mode == "auto":
        # close to the target aspect -> crop; very different (e.g. 16:9 into 9:16) -> blur fill
        mode = "crop" if abs((src_w / src_h) / (W / H) - 1) < 0.35 else "blur"
    if mode == "crop":
        if src_w / src_h > W / H:
            ch, cw = src_h, int(src_h * W / H) // 2 * 2
        else:
            cw, ch = src_w, int(src_w * H / W) // 2 * 2
        x = int(min(max(cx * src_w - cw / 2, 0), src_w - cw))
        y = int(min(max(cy * src_h - ch / 2, 0), src_h - ch))
        return f"[0:v]{pre_s}crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos,setsar=1[v]", (W, H)
    # blur
    return (f"[0:v]{pre_s}split=2[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40,"
            f"eq=brightness=-0.2:saturation=0.85[bg];"
            f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"), (W, H)


def reframe(src, out, aspect="9:16", width=1080, mode="auto", cx=0.5, cy=0.5, keep_bars=False):
    require("ffmpeg")
    info = probe(src)
    aw, ah = (int(v) for v in aspect.split(":"))
    W = width // 2 * 2
    H = int(round(W * ah / aw / 2)) * 2
    bars = None if keep_bars else detect_bars(src)
    if bars:
        print(f"[reel] black bars found, picture area {bars[0]}x{bars[1]} at {bars[2]},{bars[3]}")
    else:
        print("[reel] no black bars found")
    fc, size = build_filter(info["w"], info["h"], W, H, mode, cx, cy, bars)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]"]
    if info["has_audio"]:
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    run(cmd)
    print(f"[reel] OUT {out} {size[0]}x{size[1]}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel reframe", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out")
    ap.add_argument("--aspect", default="9:16", help="target aspect, e.g. 9:16, 4:5, 1:1, 16:9")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--mode", default="auto", choices=["auto", "crop", "blur", "bars"])
    ap.add_argument("--cx", type=float, default=0.5, help="crop centre x (0..1)")
    ap.add_argument("--cy", type=float, default=0.5, help="crop centre y (0..1)")
    ap.add_argument("--keep-bars", action="store_true", help="do not detect/remove black bars")
    a = ap.parse_args(argv)
    out = a.out or os.path.splitext(a.video)[0] + f"_{a.aspect.replace(':', 'x')}.mp4"
    reframe(a.video, out, a.aspect, a.width, a.mode, a.cx, a.cy, a.keep_bars)


if __name__ == "__main__":
    main(sys.argv[1:])
