import json
import subprocess

from reelfactory.ffutil import probe
from reelfactory.subtitles import group_words, main


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_group_words_breaks_on_count_punctuation_and_gaps():
    words = [
        {"word": "one", "start": 0.0, "end": 0.2},
        {"word": "two", "start": 0.21, "end": 0.4},
        {"word": "three", "start": 0.45, "end": 0.6},
        {"word": "stop!", "start": 0.61, "end": 0.8},
        {"word": "again", "start": 1.6, "end": 1.8},
    ]

    phrases = group_words(words, max_words=2)

    assert [phrase["text"] for phrase in phrases] == ["one two", "three stop!", "again"]
    assert all(phrase["end"] - phrase["start"] >= 0.6 for phrase in phrases)
    assert all(a["end"] <= b["start"] for a, b in zip(phrases, phrases[1:]))


def test_burn_existing_srt_end_to_end(tmp_path):
    source = tmp_path / "source.mp4"
    _run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=12:duration=3",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=3",
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(source),
    ])
    srt = tmp_path / "captions.srt"
    srt.write_text(
        "1\n00:00:00,200 --> 00:00:01,200\nFirst caption\n\n"
        "2\n00:00:01,500 --> 00:00:02,700\nSecond caption\n",
        encoding="utf-8",
    )
    out = tmp_path / "burned.mp4"

    main([
        str(source), "--out", str(out), "--srt", str(srt),
        "--style", "clean", "--size", "36",
    ])

    assert out.exists()
    assert (tmp_path / "burned.mp4.srt").exists()
    words_path = tmp_path / "burned.mp4.words.json"
    assert words_path.exists()
    assert len(json.loads(words_path.read_text(encoding="utf-8"))) == 4
    assert abs(probe(str(out))["duration"] - 3.0) < 0.2
