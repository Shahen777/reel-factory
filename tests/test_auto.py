import os
import subprocess
import wave

import numpy as np
from PIL import Image

from reelfactory.auto import build_edl
from reelfactory.beats import grid
from reelfactory.montage import render_edl


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _video(path, size):
    _run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
        "testsrc2=size=%s:rate=12:duration=3" % size,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ])


def _click_track(path, seconds=6.0, bpm=120):
    rate = 22050
    audio = np.zeros(int(rate * seconds), dtype=np.float32)
    for start in np.arange(0.0, seconds, 60.0 / bpm):
        i = int(start * rate)
        n = min(int(rate * 0.035), len(audio) - i)
        t = np.arange(n, dtype=np.float32) / rate
        audio[i:i + n] = 0.8 * np.sin(2 * np.pi * 1200 * t) * np.exp(-55 * t)
    pcm = np.clip(audio * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


def _media(tmp_path):
    folder = tmp_path / "media"
    folder.mkdir()
    landscape = folder / "landscape.mp4"
    portrait = folder / "portrait.mp4"
    _video(landscape, "640x360")
    _video(portrait, "360x640")
    Image.new("RGB", (640, 800), (35, 120, 210)).save(folder / "photo.jpg")
    music = tmp_path / "clicks.wav"
    _click_track(music)
    return folder, landscape, portrait, music


def test_build_edl_chooses_valid_unique_moments_and_hook(tmp_path):
    folder, hook, _portrait, music = _media(tmp_path)
    edl = build_edl(
        str(folder), str(music), 5.0, "punchy", "A TITLE", "A SUBTITLE",
        str(hook), seed=7,
    )

    assert edl["segments"][0]["src"] == os.path.abspath(str(hook))
    assert edl["segments"][0]["beats"] == 2
    assert edl["segments"][0]["flash"] == 0.08
    assert all(os.path.exists(segment["src"]) for segment in edl["segments"])

    moments = [
        (segment["src"], round(float(segment.get("in", 0.0)), 3))
        for segment in edl["segments"]
    ]
    assert len(moments) == len(set(moments))

    _tempo, beat_grid = grid(str(music))
    total_beats = int(sum(segment["beats"] for segment in edl["segments"]))
    actual_duration = beat_grid[total_beats] - beat_grid[0]
    assert actual_duration <= 5.05
    assert actual_duration >= 3.0
    assert edl["titles"][0]["sub"] == "A SUBTITLE"
    assert edl["segments"][-1]["fade_out"] == 0.4


def test_preview_render_small_frame(tmp_path):
    folder, _landscape, portrait, music = _media(tmp_path)
    edl = build_edl(
        str(folder), str(music), 2.0, "punchy", None, None,
        str(portrait), seed=0, w=360, h=640, fps=12,
    )
    out = tmp_path / "preview.mp4"

    render_edl(edl, base_dir=str(tmp_path), preview=True, out=str(out))

    assert out.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(out)],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    assert probe.stdout.strip() == "360x640"
