"""Core tests: titles, beat timeline, montage render, reframe, export, CLI. No network."""
import json
import math
import os
import struct
import subprocess
import sys
import wave

import pytest
from PIL import Image

from reelfactory import cli, montage, reframe, export, titles
from reelfactory.ffutil import probe


def _clip(path, size="640x360", dur=3, audio=False):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={size}:r=30:d={dur}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=f=440:d={dur}", "-shortest", "-c:a", "aac"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return str(path)


def _clicks(path, bpm=120, seconds=8, sr=22050):
    step = 60.0 / bpm
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        data = bytearray()
        for i in range(int(seconds * sr)):
            ph = (i / sr) % step
            v = math.sin(2 * math.pi * 80 * ph) * math.exp(-ph * 25)
            data += struct.pack("<h", int(v * 28000))
        w.writeframes(bytes(data))
    return str(path)


def test_title_png_is_full_frame_and_wraps(tmp_path):
    p = titles.text_png({"text": "очень длинный заголовок для проверки переноса", "size": 120}, 540, 960, str(tmp_path))
    im = Image.open(p)
    assert im.size == (540, 960) and im.mode == "RGBA"
    assert im.getbbox() is not None
    lines = titles.wrap("one two three four five six", __import__("PIL.ImageFont", fromlist=["x"]).truetype(
        __import__("reelfactory.ffutil", fromlist=["x"]).font_path("display"), 80), 300)
    assert len(lines) > 1


def test_timeline_fractional_beats():
    beats = [i * 0.5 for i in range(50)]
    t0, cuts = montage.timeline([{"beats": 2}, {"beats": 0.5}, {"beats": 1.5}], beats, 2)
    assert t0 == 1.0
    assert [round(c[1] - c[0], 3) for c in cuts] == [1.0, 0.25, 0.75]
    assert cuts[-1][1] == pytest.approx(2.0)


def test_montage_renders_on_beats(tmp_path):
    v = _clip(tmp_path / "wide.mp4")
    v2 = _clip(tmp_path / "tall.mp4", "360x640")
    Image.new("RGB", (400, 500), (200, 80, 40)).save(tmp_path / "p.jpg")
    music = _clicks(tmp_path / "beat.wav")
    edl = {"out": "out/t.mp4", "music": "beat.wav", "w": 360, "h": 640, "fps": 24,
           "look": {"contrast": 1.05, "grain": 2},
           "segments": [{"type": "video", "src": "wide.mp4", "beats": 2, "fit": "4x5", "flash": 0.05},
                        {"type": "photo", "src": "p.jpg", "beats": 2},
                        {"type": "video", "src": "tall.mp4", "beats": 1, "shake": 3},
                        {"type": "black", "beats": 1}],
           "titles": [{"text": "TEST", "at_beat": 0, "beats": 2, "anim": "pop", "size": 60}]}
    out = montage.render_edl(edl, base_dir=str(tmp_path), preview=True)
    info = probe(out)
    assert (info["w"], info["h"]) == (360, 640)
    assert info["has_audio"]
    assert 2.6 < info["duration"] < 3.4  # 6 beats at ~120 BPM


def test_reframe_removes_bars(tmp_path):
    src = tmp_path / "bars.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=360x640:r=30:d=2",
                    "-vf", "scale=260:640,pad=360:640:50:0:black", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(src)], check=True)
    bars = reframe.detect_bars(str(src))
    assert bars is not None and abs(bars[0] - 260) <= 8
    out = reframe.reframe(str(src), str(tmp_path / "o.mp4"), "9:16", 360, "blur")
    info = probe(out)
    assert (info["w"], info["h"]) == (360, 640)


def test_export_preset(tmp_path):
    src = _clip(tmp_path / "a.mp4", audio=True)
    out = export.export(src, str(tmp_path / "e.mp4"), "telegram")
    info = probe(out)
    assert (info["w"], info["h"]) == (720, 1280) and info["has_audio"]


def test_cli_help_and_doctor(capsys):
    assert cli.main([]) == 0
    assert "montage" in capsys.readouterr().out
    assert cli.main(["nope"]) == 2


def test_motion_templates_have_contract():
    d = os.path.join(os.path.dirname(cli.__file__), "assets", "motion")
    files = [f for f in os.listdir(d) if f.endswith(".html")]
    assert len(files) >= 3
    for f in files:
        src = open(os.path.join(d, f), encoding="utf-8").read()
        assert "window.renderFrame" in src and "window.MOTION" in src
        assert "http://" not in src and "https://" not in src  # must render offline


def test_skills_have_frontmatter():
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(cli.__file__))), ".claude", "skills")
    names = os.listdir(root)
    assert len(names) >= 10
    for n in names:
        txt = open(os.path.join(root, n, "SKILL.md"), encoding="utf-8").read()
        assert txt.startswith("---\nname: " + n + "\ndescription: ")


def test_remotion_project_registered():
    root = os.path.dirname(os.path.dirname(os.path.abspath(cli.__file__)))
    rootx = open(os.path.join(root, "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    from reelfactory import remotion as rm
    for comp in rm.COMPS:
        assert f'id="{comp}"' in rootx
    assert os.path.exists(os.path.join(root, "remotion", "public", "fonts", "RussoOne-Regular.ttf"))


def test_remotion_words_formats(tmp_path):
    from reelfactory.remotion import load_words
    a = tmp_path / "a.json"; a.write_text('[{"w":"hi","s":0.1,"e":0.4}]', encoding="utf-8")
    b = tmp_path / "b.json"; b.write_text('[{"word":"hi","start":0.1,"end":0.4}]', encoding="utf-8")
    assert load_words(str(a)) == load_words(str(b)) == [{"w": "hi", "s": 0.1, "e": 0.4}]
