#!/usr/bin/env python3
"""Generate test media (no downloads) and render the demo montage to out/demo.mp4."""
import math
import os
import struct
import subprocess
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
MEDIA = os.path.join(ROOT, "media", "demo")


def click_track(path, bpm=120, seconds=20, sr=44100):
    step = 60.0 / bpm
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        frames = bytearray()
        for i in range(int(seconds * sr)):
            t = i / sr
            ph = t % step
            kick = math.sin(2 * math.pi * (55 + 90 * math.exp(-ph * 30)) * ph) * math.exp(-ph * 9)
            hat = math.sin(2 * math.pi * 6000 * t) * 0.15 * math.exp(-((t + step / 2) % step) * 60)
            frames += struct.pack("<h", int(max(-1, min(1, 0.8 * kick + hat)) * 30000))
        w.writeframes(bytes(frames))


def main():
    os.makedirs(MEDIA, exist_ok=True)
    ff = ["ffmpeg", "-v", "error", "-y"]
    subprocess.run(ff + ["-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=8", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                         os.path.join(MEDIA, "wide.mp4")], check=True)
    subprocess.run(ff + ["-f", "lavfi", "-i", "mandelbrot=s=720x1280:r=30", "-t", "8", "-c:v", "libx264", "-pix_fmt",
                         "yuv420p", os.path.join(MEDIA, "tall.mp4")], check=True)
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1200, 1600), (240, 140, 40))
    ImageDraw.Draw(im).ellipse([250, 450, 950, 1150], fill=(30, 60, 200))
    im.save(os.path.join(MEDIA, "photo.jpg"), quality=92)
    click_track(os.path.join(MEDIA, "beat.wav"))
    from reelfactory.montage import main as montage
    montage([os.path.join(ROOT, "examples", "demo_edl.json")])
    print("\nOpen", os.path.join(ROOT, "out", "demo.mp4"))


if __name__ == "__main__":
    main()
