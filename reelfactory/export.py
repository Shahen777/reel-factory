"""Export a finished video with platform presets (size, bitrate, loudness -14 LUFS, faststart)."""
import argparse
import os
import sys

from .ffutil import probe, require, run

PRESETS = {
    # name: (width, height, fps, max video bitrate, max seconds, note)
    "reels":   (1080, 1920, 30, "12M", 180, "Instagram Reels"),
    "tiktok":  (1080, 1920, 30, "12M", 600, "TikTok"),
    "shorts":  (1080, 1920, 30, "12M", 180, "YouTube Shorts"),
    "feed45":  (1080, 1350, 30, "10M", 3600, "Instagram/Facebook feed 4:5"),
    "square":  (1080, 1080, 30, "10M", 3600, "Square 1:1"),
    "youtube": (1920, 1080, 30, "16M", 43200, "YouTube 16:9"),
    "telegram": (720, 1280, 30, "4M", 3600, "Light file for messengers"),
}


def export(src, out, preset="reels", lufs=-14.0, crf=19, fit="pad"):
    require("ffmpeg")
    W, H, fps, maxrate, max_s, note = PRESETS[preset]
    info = probe(src)
    if info["duration"] > max_s:
        print(f"[reel] warning: {info['duration']:.0f}s is longer than the {note} limit ({max_s}s)")
    if fit == "crop":
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
    else:
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
    vf += f",fps={fps},setsar=1,format=yuv420p"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf,
           "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-maxrate", maxrate,
           "-bufsize", str(int(maxrate[:-1]) * 2) + "M", "-profile:v", "high", "-level", "4.1"]
    if info["has_audio"]:
        cmd += ["-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    cmd += ["-movflags", "+faststart", out]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    run(cmd)
    print(f"[reel] OUT {out} ({note}, {W}x{H}, {fps} fps, {lufs} LUFS)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel export", description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--preset", default="reels", choices=sorted(PRESETS))
    ap.add_argument("--out")
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--fit", default="pad", choices=["pad", "crop"])
    ap.add_argument("--all", action="store_true", help="export reels, tiktok and shorts at once")
    a = ap.parse_args(argv)
    presets = ["reels", "tiktok", "shorts"] if a.all else [a.preset]
    for p in presets:
        out = a.out if (a.out and not a.all) else os.path.splitext(a.video)[0] + f"_{p}.mp4"
        export(a.video, out, p, a.lufs, a.crf, a.fit)


if __name__ == "__main__":
    main(sys.argv[1:])
