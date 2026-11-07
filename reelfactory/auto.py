"""Build a beat-locked montage automatically from a folder of media."""
import argparse
import copy
import json
import math
import os
import random
import subprocess
import sys
import tempfile

import numpy as np

from . import beats as beatlib
from .ffutil import kind, probe, require
from .montage import render_edl


PATTERNS = {
    "punchy": [2, 2, 1, 1, 2, 1, 1, 4],
    "smooth": [4, 4, 2, 4],
    "cinematic": [4, 8, 4, 2, 2, 8],
}
DEFAULT_LOOK = {
    "contrast": 1.05,
    "saturation": 1.1,
    "sharpen": 0.4,
    "grain": 3,
    "vignette": True,
}
FRAME_SIDE = 96
SAMPLE_FPS = 2.0


def _media_files(folder):
    """Return supported, non-hidden video and photo files in name order."""
    folder = os.path.abspath(os.path.expanduser(folder))
    if not os.path.isdir(folder):
        raise SystemExit("[reel] media folder not found: %s" % folder)
    found = []
    for name in sorted(os.listdir(folder), key=lambda value: value.lower()):
        if name.startswith("."):
            continue
        path = os.path.join(folder, name)
        media_kind = kind(path)
        if os.path.isfile(path) and media_kind in ("video", "photo"):
            found.append((path, media_kind))
    if not found:
        raise SystemExit("[reel] no videos or photos found in: %s" % folder)
    return found


def _analyze_video(path):
    """Extract one small raw frame stream and score its frames."""
    info = probe(path)
    vf = (
        "fps=2,scale=%d:%d:force_original_aspect_ratio=decrease,"
        "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,format=gray"
        % (FRAME_SIDE, FRAME_SIDE, FRAME_SIDE, FRAME_SIDE)
    )
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", vf,
         "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace")[-2000:]
        raise SystemExit("[reel] could not analyze %s\n%s" % (path, detail))
    frame_bytes = FRAME_SIDE * FRAME_SIDE
    count = len(result.stdout) // frame_bytes
    if not count:
        raise SystemExit("[reel] no frames decoded from: %s" % path)
    frames = np.frombuffer(result.stdout[:count * frame_bytes], dtype=np.uint8)
    frames = frames.reshape(count, FRAME_SIDE, FRAME_SIDE).astype(np.float32)
    samples = []
    previous = None
    for index, frame in enumerate(frames):
        motion = 0.0 if previous is None else float(np.mean(np.abs(frame - previous)))
        centre = frame[1:-1, 1:-1]
        lap = (
            frame[:-2, 1:-1] + frame[2:, 1:-1] +
            frame[1:-1, :-2] + frame[1:-1, 2:] - 4.0 * centre
        )
        sharpness = float(np.var(lap))
        brightness = float(np.mean(frame))
        penalty = max(0.0, 25.0 - brightness) + max(0.0, brightness - 235.0)
        # motion counts only when the frame is sharp: shaky, blurred camera moves score low
        sharp = math.sqrt(max(sharpness, 0.0))
        sharp_factor = min(1.3, max(0.3, sharp / 12.0))
        flat = max(0.0, 18.0 - float(np.std(frame)))  # blank wall, window, lens cap
        score = min(motion, 25.0) * sharp_factor + 0.15 * sharp - 1.5 * penalty - 1.0 * flat
        samples.append({
            "time": index / SAMPLE_FPS,
            "score": score,
            "motion": motion,
        })
        previous = frame
    return {"info": info, "samples": samples, "used": []}


def _overlaps(start, end, windows):
    return any(start < old_end - 1e-6 and end > old_start + 1e-6
               for old_start, old_end in windows)


def _best_window(analysis, seconds, rng):
    """Find the best sampled window not overlapping prior choices."""
    duration = float(analysis["info"]["duration"])
    candidates = []
    for sample in analysis["samples"]:
        start = float(sample["time"])
        end = start + seconds
        if start < 0.3 or end > duration - 0.3 + 1e-6:
            continue
        if _overlaps(start, end, analysis["used"]):
            continue
        inside = [item for item in analysis["samples"]
                  if start <= item["time"] < end]
        if not inside:
            continue
        score = sum(item["score"] for item in inside) / len(inside)
        motion = sum(item["motion"] for item in inside) / len(inside)
        candidates.append((score + rng.random() * 1e-7, motion, start, end))
    if not candidates:
        return None
    score, motion, start, end = max(candidates, key=lambda item: item[0])
    return {"in": start, "end": end, "score": score, "motion": motion}


def _beat_time(beat_grid, position):
    whole = int(math.floor(position + 1e-9))
    fraction = position - whole
    return beat_grid[whole] + (beat_grid[whole + 1] - beat_grid[whole]) * fraction


def _segment_seconds(beat_grid, start_beat, length):
    return _beat_time(beat_grid, start_beat + length) - _beat_time(beat_grid, start_beat)


def _asset(path, media_kind, analyses):
    if media_kind == "video":
        analysis = analyses[path]
        info = analysis["info"]
    else:
        from PIL import Image
        with Image.open(path) as image:
            width, height = image.size
        analysis = None
        info = {"w": width, "h": height}
    return {"path": path, "type": media_kind, "analysis": analysis, "info": info}


def _make_segment(asset, beats, candidate=None, photo_index=0):
    segment = {
        "type": asset["type"],
        "src": asset["path"],
        "beats": beats,
        "fit": "full" if asset["info"]["h"] > asset["info"]["w"] else "4x5",
    }
    if asset["type"] == "video":
        segment.update({
            "in": round(float(candidate["in"]), 3),
            "score": round(float(candidate["score"]), 3),
            "motion": round(float(candidate["motion"]), 3),
        })
    else:
        segment["push"] = 0.12
        segment["cy"] = 0.42 if photo_index % 2 == 0 else 0.5
    return segment


def build_edl(folder, music, duration=30, style="punchy", title=None, sub=None,
              hook=None, seed=0, w=1080, h=1920, fps=30):
    """Analyze ``folder`` and return a montage EDL dictionary.

    ``w``, ``h`` and ``fps`` are optional render overrides, useful for previews
    and tests. Source paths in the returned dictionary are absolute; the CLI
    makes them relative when it writes the editable EDL file.
    """
    if style not in PATTERNS:
        raise ValueError("unknown montage style: %s" % style)
    require("ffmpeg")
    require("ffprobe")
    music = os.path.abspath(os.path.expanduser(music))
    if not os.path.isfile(music):
        raise SystemExit("[reel] music file not found: %s" % music)
    media = _media_files(folder)
    hook_path = os.path.abspath(os.path.expanduser(hook)) if hook else None
    if hook_path and (not os.path.isfile(hook_path) or kind(hook_path) not in ("video", "photo")):
        raise SystemExit("[reel] hook must be a video or photo: %s" % hook_path)

    video_paths = {path for path, media_kind in media if media_kind == "video"}
    if hook_path and kind(hook_path) == "video":
        video_paths.add(hook_path)
    analyses = {path: _analyze_video(path) for path in sorted(video_paths)}
    assets = [_asset(path, media_kind, analyses) for path, media_kind in media]
    by_path = {asset["path"]: asset for asset in assets}
    if hook_path and hook_path not in by_path:
        by_path[hook_path] = _asset(hook_path, kind(hook_path), analyses)

    # Some read-only Python installations leave numba without a cache locator.
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(tempfile.gettempdir(), "reelfactory-numba"))
    _tempo, beat_grid = beatlib.grid(music)
    rng = random.Random(seed)
    first_seconds = _segment_seconds(beat_grid, 0, 2)
    if first_seconds > float(duration) + 1e-6:
        raise SystemExit("[reel] duration is shorter than the required two-beat hook")

    first_asset = by_path.get(hook_path) if hook_path else None
    first_candidate = None
    if first_asset and first_asset["type"] == "video":
        first_candidate = _best_window(first_asset["analysis"], first_seconds, rng)
        if first_candidate is None:
            raise SystemExit("[reel] hook video is too short for a two-beat window")
    elif first_asset is None:
        ranked = []
        for asset in assets:
            if asset["type"] != "video":
                continue
            candidate = _best_window(asset["analysis"], first_seconds, rng)
            if candidate:
                ranked.append((candidate["score"], asset, candidate))
        if ranked:
            _score, first_asset, first_candidate = max(ranked, key=lambda item: item[0])
        else:
            first_asset = assets[0]
    if first_asset["type"] == "video":
        first_asset["analysis"]["used"].append((first_candidate["in"], first_candidate["end"]))
    first = _make_segment(first_asset, 2, first_candidate)
    first["flash"] = 0.08
    segments = [first]

    position = 2.0
    pattern_index = 0
    photo_index = 0
    used_photos = set()
    since_photo = 3
    rr = 0
    for index, asset in enumerate(assets):
        if asset["path"] == first_asset["path"]:
            rr = (index + 1) % len(assets)
            break

    while True:
        length = PATTERNS[style][pattern_index % len(PATTERNS[style])]
        seconds = _segment_seconds(beat_grid, position, length)
        total = _beat_time(beat_grid, position + length) - beat_grid[0]
        if total > float(duration) + 1e-6:
            break
        chosen = None
        candidate = None
        deferred_photo = None
        # spread photos evenly: one every few cuts when the segment length suits a photo
        free_photos = [(i, a) for i, a in enumerate(assets) if a["type"] == "photo" and a["path"] not in used_photos]
        if free_photos and 2 <= length <= 4 and since_photo >= 3:
            chosen = free_photos[0]
        for step in ([] if chosen else range(len(assets))):
            asset_index = (rr + step) % len(assets)
            asset = assets[asset_index]
            if asset["type"] == "photo":
                if not 2 <= length <= 4:
                    continue
                if asset["path"] in used_photos:
                    deferred_photo = deferred_photo or (asset_index, asset)
                    continue
                chosen = (asset_index, asset)
                break
            possible = _best_window(asset["analysis"], seconds, rng)
            if possible is not None:
                chosen = (asset_index, asset)
                candidate = possible
                break
        if chosen is None and deferred_photo is not None:
            chosen = deferred_photo
        if chosen is None:
            break
        asset_index, asset = chosen
        if asset["type"] == "video":
            rr = (asset_index + 1) % len(assets)
        if asset["type"] == "video":
            asset["analysis"]["used"].append((candidate["in"], candidate["end"]))
        else:
            used_photos.add(asset["path"])
        segment = _make_segment(asset, length, candidate, photo_index)
        if asset["type"] == "photo":
            photo_index += 1
            since_photo = 0
        else:
            since_photo += 1
        segments.append(segment)
        position += length
        pattern_index += 1

    if style == "punchy":
        for index, segment in enumerate(segments):
            if (index + 1) % 4 == 0:
                segment["flash"] = 0.06
            if segment["beats"] == 1:
                segment["shake"] = 5
    elif style == "cinematic":
        videos = [segment for segment in segments if segment["type"] == "video"]
        for segment in sorted(videos, key=lambda item: item.get("motion", 0), reverse=True)[:2]:
            segment["speed"] = 0.6

    segments[-1]["fade_out"] = 0.4
    edl = {
        "music": music,
        "w": int(w),
        "h": int(h),
        "fps": int(fps),
        "segments": segments,
        "look": copy.deepcopy(DEFAULT_LOOK),
        "audio": {"fade_out": 1.2},
    }
    if title:
        edl["titles"] = [{
            "text": title,
            "sub": sub,
            "at_beat": 0,
            "beats": 4,
            "anim": "pop",
            "y": 0.32,
            "stroke": "#000000",
        }]
    return edl


def _editable_edl(edl, edl_path, out):
    result = copy.deepcopy(edl)
    base = os.path.dirname(os.path.abspath(edl_path))
    result["music"] = os.path.relpath(result["music"], base)
    result["out"] = os.path.relpath(os.path.abspath(out), base)
    for segment in result["segments"]:
        segment["src"] = os.path.relpath(segment["src"], base)
    return result


def _print_choices(edl):
    print("clip\tin\tbeats\tscore")
    for segment in edl["segments"]:
        print("%s\t%s\t%s\t%s" % (
            os.path.basename(segment["src"]),
            "%.2f" % segment["in"] if "in" in segment else "-",
            segment["beats"],
            "%.2f" % segment["score"] if "score" in segment else "-",
        ))


def main(argv=None):
    """CLI entry point for automatic montage generation."""
    parser = argparse.ArgumentParser(prog="reel auto", description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--music", required=True)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--title")
    parser.add_argument("--sub")
    parser.add_argument("--style", choices=sorted(PATTERNS), default="punchy")
    parser.add_argument("--hook")
    parser.add_argument("--out", default="out/auto.mp4")
    parser.add_argument("--edl-only", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    out = os.path.abspath(os.path.expanduser(args.out))
    edl_path = out + ".edl.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    edl = build_edl(
        args.folder, args.music, args.duration, args.style, args.title,
        args.sub, args.hook, args.seed,
    )
    _print_choices(edl)
    editable = _editable_edl(edl, edl_path, out)
    with open(edl_path, "w", encoding="utf-8") as handle:
        json.dump(editable, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print("[reel] EDL %s" % edl_path)
    if not args.edl_only:
        render_edl(editable, base_dir=os.path.dirname(edl_path),
                   preview=args.preview, out=out)
    return editable


if __name__ == "__main__":
    main(sys.argv[1:])
