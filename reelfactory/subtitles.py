"""Transcribe or import speech subtitles and burn them into a video."""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

from .ffutil import font_path, probe, require, run
from .titles import SAFE_BOTTOM, SAFE_TOP, text_png


PUNCTUATION = (".", "!", "?", ",", ";", ":", "…")


def _word_dict(word):
    if isinstance(word, dict):
        text = word.get("word", word.get("text", ""))
        start = word.get("start")
        end = word.get("end")
    else:
        text = getattr(word, "word", "")
        start = getattr(word, "start", None)
        end = getattr(word, "end", None)
    if start is None or end is None or not str(text).strip():
        return None
    return {
        "word": str(text).strip(),
        "start": float(start),
        "end": float(end),
    }


def group_words(words, max_words=3):
    """Group timestamped words by count, punctuation, and pauses.

    Returned phrases last at least 0.6 seconds. If short neighboring phrases
    would overlap after that extension, the later phrase is moved forward.
    """
    if max_words < 1:
        raise ValueError("max_words must be at least 1")
    normalized = [item for item in (_word_dict(word) for word in words) if item]
    raw = []
    current = []
    for word in normalized:
        if current and (len(current) >= max_words or word["start"] - current[-1]["end"] > 0.6):
            raw.append(current)
            current = []
        current.append(word)
        if word["word"].endswith(PUNCTUATION):
            raw.append(current)
            current = []
    if current:
        raw.append(current)

    phrases = []
    previous_end = 0.0
    for phrase_words in raw:
        start = max(float(phrase_words[0]["start"]), previous_end)
        end = max(float(phrase_words[-1]["end"]), start + 0.6)
        phrase = {
            "text": " ".join(word["word"] for word in phrase_words),
            "start": start,
            "end": end,
            "words": [dict(word) for word in phrase_words],
        }
        phrases.append(phrase)
        previous_end = end
    return phrases


def _transcribe(video, language, model_name, max_words):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit(
            "[reel] speech transcription needs faster-whisper; "
            "install it with: pip install faster-whisper"
        )
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        video, language=language, word_timestamps=True,
    )
    words = []
    for segment in segments:
        for word in segment.words or []:
            item = _word_dict(word)
            if item:
                words.append(item)
    return group_words(words, max_words=max_words)


def _seconds(value):
    match = re.match(r"^(\d+):(\d{2}):(\d{2})[,.](\d{3})$", value.strip())
    if not match:
        raise ValueError("invalid SRT timestamp: %s" % value)
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def _cue_words(text, start, end):
    tokens = text.split()
    if not tokens:
        return []
    step = max(end - start, 0.001) / len(tokens)
    return [
        {"word": token, "start": start + index * step,
         "end": start + (index + 1) * step}
        for index, token in enumerate(tokens)
    ]


def read_srt(path):
    """Read an SRT file, treating every cue as one subtitle phrase."""
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    phrases = []
    previous_end = 0.0
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            raise ValueError("SRT cue has no timing line")
        left, right = [part.strip() for part in lines[timing_index].split("-->", 1)]
        raw_start, raw_end = _seconds(left), _seconds(right)
        start = max(raw_start, previous_end)
        end = max(raw_end, start + 0.6)
        cue_text = " ".join(lines[timing_index + 1:])
        if not cue_text:
            continue
        phrases.append({
            "text": cue_text,
            "start": start,
            "end": end,
            "words": _cue_words(cue_text, start, end),
        })
        previous_end = end
    return phrases


def _srt_time(seconds):
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, secs, millis)


def _write_sidecars(out, phrases):
    srt_path = out + ".srt"
    words_path = out + ".words.json"
    with open(srt_path, "w", encoding="utf-8") as handle:
        for index, phrase in enumerate(phrases, 1):
            handle.write("%d\n%s --> %s\n%s\n\n" % (
                index, _srt_time(phrase["start"]), _srt_time(phrase["end"]),
                phrase["text"],
            ))
    words = [dict(word) for phrase in phrases for word in phrase.get("words", [])]
    with open(words_path, "w", encoding="utf-8") as handle:
        json.dump(words, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return srt_path, words_path


def _karaoke_png(phrase, phrase_index, active, width, height, outdir, font, size, y):
    """Draw a simple centered karaoke line with one highlighted word."""
    face = ImageFont.truetype(font_path(font or "display"), int(size))
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    words = [word["word"].upper() for word in phrase["words"]]
    space = draw.textlength(" ", font=face)
    widths = [draw.textlength(word, font=face) for word in words]
    total_width = sum(widths) + space * max(0, len(words) - 1)
    bbox = draw.textbbox((0, 0), "Ag", font=face, stroke_width=max(2, int(size) // 28))
    line_height = bbox[3] - bbox[1]
    centre = max(SAFE_TOP * height + line_height / 2,
                 min(float(y) * height, SAFE_BOTTOM * height - line_height / 2))
    x = (width - total_width) / 2
    top = centre - line_height / 2 - bbox[1]
    for index, word in enumerate(words):
        color = "#FFD400" if index == active else "#FFFFFF"
        draw.text(
            (x, top), word, font=face, fill=color,
            stroke_width=max(2, int(size) // 28), stroke_fill="#000000",
        )
        x += widths[index] + space
    path = os.path.join(outdir, "karaoke_%04d_%02d.png" % (phrase_index, active))
    image.save(path)
    return path


def _render_states(phrases, style, width, height, outdir, y, font, size):
    states = []
    for phrase_index, phrase in enumerate(phrases):
        if style == "karaoke":
            words = phrase.get("words") or _cue_words(
                phrase["text"], phrase["start"], phrase["end"],
            )
            phrase = dict(phrase)
            phrase["words"] = words
            for word_index, word in enumerate(words):
                start = phrase["start"] if word_index == 0 else max(phrase["start"], word["start"])
                if word_index + 1 < len(words):
                    end = min(phrase["end"], max(start + 0.01, words[word_index + 1]["start"]))
                else:
                    end = phrase["end"]
                png = _karaoke_png(
                    phrase, phrase_index, word_index, width, height, outdir, font, size, y,
                )
                states.append((png, start, end))
            continue
        spec = {
            "text": phrase["text"].upper() if style == "bold" else phrase["text"],
            "font": font or ("display" if style == "bold" else "sans"),
            "size": int(size),
            "y": float(y),
            "max_width": 0.9,
        }
        if style == "bold":
            spec.update({"stroke": "#000000", "color": "#FFFFFF"})
        else:
            spec.update({"scrim": True, "color": "#FFFFFF", "shadow": False})
        png = text_png(spec, width, height, outdir)
        states.append((png, phrase["start"], phrase["end"]))
    return states


def _burn(video, out, states, duration, fps, temp_dir):
    if not states:
        run(["ffmpeg", "-v", "error", "-y", "-i", video,
             "-map", "0", "-c", "copy", out])
        return
    current = video
    batches = [states[index:index + 40] for index in range(0, len(states), 40)]
    for batch_index, batch in enumerate(batches):
        target = out if batch_index == len(batches) - 1 else os.path.join(
            temp_dir, "pass_%03d.mp4" % batch_index,
        )
        inputs = ["-i", current]
        graph = []
        previous = "[0:v]"
        for index, (png, start, end) in enumerate(batch, 1):
            inputs.extend([
                "-loop", "1", "-framerate", str(fps), "-t", "%.4f" % duration,
                "-i", png,
            ])
            output = "[v%d]" % index
            graph.append(
                "%s[%d:v]overlay=x=0:y=0:eof_action=pass:enable='between(t,%.3f,%.3f)'%s"
                % (previous, index, start, end, output)
            )
            previous = output
        run([
            "ffmpeg", "-v", "error", "-y",
        ] + inputs + [
            "-filter_complex", ";".join(graph), "-map", previous, "-map", "0:a?",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-t", "%.4f" % duration,
            out if target == out else target,
        ])
        current = target


def _default_out(video):
    root, _extension = os.path.splitext(video)
    return root + ".subtitled.mp4"


def main(argv=None):
    """CLI entry point for subtitle transcription and burning."""
    parser = argparse.ArgumentParser(prog="reel subtitles", description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--out")
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--model", default="small")
    parser.add_argument("--words", type=int, default=3)
    parser.add_argument("--style", choices=("bold", "clean", "karaoke"), default="bold")
    parser.add_argument("--y", type=float, default=0.70)
    parser.add_argument("--font")
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--srt-only", action="store_true")
    parser.add_argument("--srt")
    args = parser.parse_args(argv)

    require("ffmpeg")
    require("ffprobe")
    video = os.path.abspath(os.path.expanduser(args.video))
    if not os.path.isfile(video):
        raise SystemExit("[reel] video not found: %s" % video)
    out = os.path.abspath(os.path.expanduser(args.out or _default_out(video)))
    if out == video and not args.srt_only:
        raise SystemExit("[reel] --out must differ from the source video")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if args.srt:
        phrases = read_srt(os.path.abspath(os.path.expanduser(args.srt)))
    else:
        phrases = _transcribe(video, args.lang, args.model, args.words)
    srt_path, words_path = _write_sidecars(out, phrases)
    print("[reel] SRT %s" % srt_path)
    print("[reel] words %s" % words_path)
    if args.srt_only:
        return out

    info = probe(video)
    temp_dir = tempfile.mkdtemp(prefix=".subtitles_", dir=os.path.dirname(out))
    try:
        states = _render_states(
            phrases, args.style, info["w"], info["h"], temp_dir,
            args.y, args.font, args.size,
        )
        _burn(video, out, states, info["duration"], info["fps"], temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    print("[reel] OUT %s" % out)
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
