"""Beat-locked montage builder: an EDL (JSON) of clips/photos measured in beats -> finished video.

EDL keys (all optional except segments):
  out, music, music_offset, beat_source, bpm (used when there is no music), start_beat,
  fps, w, h, look{contrast,saturation,brightness,grain,sharpen,vignette},
  segments[{type: video|photo|black, src, in, beats, fit: full|4x5, cx, cy, zoom, push,
            speed, rotate, flash, shake, fade_in, fade_out}],
  titles[{text, at_beat, beats, y, size, font, color, stroke, anim: rise|pop|none, scrim, sub, ...}],
  audio{fade_in, fade_out, gain_db, voice, voice_at, voice_gain_db, duck_db}
Paths are relative to the EDL file (or to `base_dir`).
See docs/EDL.md for the full reference.
"""
import json
import math
import os
import sys

from PIL import Image

from . import beats as beatlib
from .ffutil import probe, require, run
from .titles import text_png


class Ctx:
    def __init__(self, base_dir, W, H, fps, tmp):
        self.base_dir, self.W, self.H, self.fps, self.tmp = base_dir, W, H, fps, tmp

    def path(self, p):
        if p is None:
            return None
        p = os.path.expanduser(p)
        if os.path.isabs(p):
            return p
        for base in (self.base_dir, os.getcwd()):
            cand = os.path.join(base, p)
            if os.path.exists(cand):
                return cand
        raise SystemExit(f"[reel] source not found: {p}")


def seg_filter(seg, W, H, fps, dur, sw, sh):
    """Filter chain for a video/photo segment -> WxH @ fps.
    Static aspect crop around (cx, cy) + zoompan for zoom/push-in (time-varying crop breaks ffmpeg)."""
    f = []
    rot = int(seg.get("rotate", 0))
    if rot == 1:
        f.append("transpose=1"); sw, sh = sh, sw
    elif rot == 2:
        f.append("transpose=2"); sw, sh = sh, sw
    speed = float(seg.get("speed", 1.0))
    if speed < 0.999:
        f.append("minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" % int(round(fps / speed)))
        f.append("setpts=PTS/%.4f" % speed)
    elif speed > 1.001:
        f.append("setpts=PTS/%.4f" % speed)
    f.append(f"fps={fps}")
    cx, cy = float(seg.get("cx", 0.5)), float(seg.get("cy", 0.5))
    zoom, push = float(seg.get("zoom", 1.0)), float(seg.get("push", 0.0))
    nfr = max(1.0, fps * dur)
    zexpr = f"{zoom:.4f}*(1+{push:.4f}*min(in/{nfr:.2f},1))"

    def window(aspect):
        if sw / sh > aspect:
            bh, bw = sh, sh * aspect
        else:
            bw, bh = sw, sw / aspect
        bw, bh = int(bw) // 2 * 2, int(bh) // 2 * 2
        x0 = int(min(max(cx * sw - bw / 2, 0), sw - bw))
        y0 = int(min(max(cy * sh - bh / 2, 0), sh - bh))
        return bw, bh, x0, y0

    def zp(ow, oh):
        return f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={ow}x{oh}:fps={fps}"

    if seg.get("fit", "full") == "full":
        bw, bh, x0, y0 = window(W / H)
        f.append(f"crop={bw}:{bh}:{x0}:{y0}")
        f.append(zp(W, H))
        return f"[0:v]{','.join(f)},setsar=1[v]"
    # "4x5" (or "fit"): sharp window over a blurred full-bleed copy, for horizontal sources
    aspect = 0.8 if seg.get("fit") == "4x5" else min(sw / sh, W / H * 2)
    FH = min(H, int(round(W / aspect / 2)) * 2)
    bw, bh, x0, y0 = window(W / FH)
    pre = ",".join(f) + ","
    return (f"[0:v]{pre}split=2[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40,"
            f"eq=brightness=-0.25:saturation=0.8[bg];"
            f"[b]crop={bw}:{bh}:{x0}:{y0},{zp(W, FH)}[fg];"
            f"[bg][fg]overlay=x=0:y={(H - FH) // 2}:format=auto,setsar=1[v]")


def extra_post(seg, dur, W, H):
    parts = []
    fl = float(seg.get("flash", 0))
    if fl > 0:
        parts.append(f"fade=t=in:st=0:d={fl:.3f}:color=white")
    fi, fo = float(seg.get("fade_in", 0)), float(seg.get("fade_out", 0))
    if fi > 0:
        parts.append(f"fade=t=in:st=0:d={fi:.3f}")
    if fo > 0:
        parts.append(f"fade=t=out:st={max(0, dur - fo):.3f}:d={fo:.3f}")
    if seg.get("shake"):
        a = float(seg["shake"])
        parts.append(f"crop=w=iw-{int(a * 2)}:h=ih-{int(a * 2)}:x='{a}+{a}*sin(t*97)':y='{a}+{a}*cos(t*83)',scale={W}:{H}")
    return ",".join(parts)


def add_titles(fc, titles, dur, fps):
    """Overlay title PNGs on a graph ending in [v]. Each PNG is a looped input starting at t=0
    (no PTS shift: shifted looped overlays deadlock some ffmpeg builds); visibility via alpha fades."""
    if not titles:
        return fc, []
    extra = []
    fc = fc.replace("[v]", "[v0]")
    cur = "[v0]"
    for j, (png, ls, le, spec) in enumerate(titles):
        i = 1 + j
        extra += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.4f}", "-i", png]
        fi, fo = float(spec.get("fade_in", 0.08)), float(spec.get("fade_out", 0.12))
        cont = ls < 0.0
        ls_c, le_c = max(ls, 0.0), min(le, dur)
        anim = spec.get("anim", "rise")
        chain = f"[{i}:v]format=rgba"
        if not cont:
            chain += f",fade=t=in:st={ls_c:.3f}:d={max(fi, 0.02):.3f}:alpha=1"
        if le <= dur + 0.01:
            chain += f",fade=t=out:st={max(0.0, le_c - fo):.3f}:d={max(fo, 0.02):.3f}:alpha=1"
        chain += f"[t{i}]"
        fc += ";" + chain
        if anim == "rise" and not cont:
            y = f"-22*(1-min(max(t-{ls_c:.3f},0)/0.22,1))"
            x = "0"
        elif anim == "pop" and not cont:
            # fast snap from below with a small overshoot
            y = f"48*(1-min(max(t-{ls_c:.3f},0)/0.12,1))-8*sin(min(max(t-{ls_c:.3f}-0.12,0)/0.16,1)*PI)"
            x = "0"
        else:
            x, y = "0", "0"
        fc += f";{cur}[t{i}]overlay=x='{x}':y='{y}':eof_action=pass:enable='between(t,{ls_c:.3f},{le_c:.3f})'[v{i}]"
        cur = f"[v{i}]"
    fc = fc[: fc.rfind(cur)] + "[v]" + fc[fc.rfind(cur) + len(cur):]
    return fc, extra


def render_segment(seg, idx, ctx, dur, titles=()):
    W, H, fps = ctx.W, ctx.H, ctx.fps
    out = os.path.join(ctx.tmp, f"seg_{idx:03d}.mp4")
    enc = ["-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", "-an", "-r", str(fps)]
    t = seg.get("type", "video")
    if t == "black":
        color = seg.get("color", "black")
        fc, extra = add_titles("[0:v]null[v]", titles, dur, fps)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={W}x{H}:r={fps}",
             "-t", f"{dur:.4f}"] + extra + ["-filter_complex", fc, "-map", "[v]", "-t", f"{dur:.4f}"] + enc + [out])
        return out
    p = ctx.path(seg["src"])
    if t == "photo":
        with Image.open(p) as im:
            sw, sh = im.size
        seg = dict(seg)
        seg.setdefault("push", 0.12)
        inp = ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.4f}", "-i", p]
    else:
        info = probe(p)
        sw, sh, sdur = info["w"], info["h"], info["duration"]
        speed = float(seg.get("speed", 1.0))
        need = dur * speed + 0.25
        tin = float(seg.get("in", 0.0))
        if tin + need > sdur:
            tin = max(0.0, sdur - need)
        inp = ["-ss", f"{tin:.3f}", "-t", f"{need:.3f}", "-i", p]
    fc = seg_filter(seg, W, H, fps, dur, sw, sh)
    post = extra_post(seg, dur, W, H)
    if post:
        fc = fc.replace("[v]", f",{post}[v]")
    fc, extra = add_titles(fc, titles, dur, fps)
    run(["ffmpeg", "-v", "error", "-y"] + inp + extra +
        ["-filter_complex", fc, "-map", "[v]", "-t", f"{dur:.4f}"] + enc + [out])
    return out


def timeline(segments, beats, k):
    """Map segment lengths in beats (fractions allowed) onto the beat grid."""
    t0 = beats[k]
    cuts, pos = [], float(k)

    def at(x):
        i = int(math.floor(x + 1e-9))
        return beats[i] + (beats[i + 1] - beats[i]) * (x - i)

    for seg in segments:
        n = float(seg.get("beats", 1))
        s, e = at(pos), at(pos + n)
        cuts.append((s - t0, e - t0, seg))
        pos += n
    return t0, cuts


def look_chain(look):
    lk = []
    if look.get("sharpen"):
        lk.append(f"unsharp=5:5:{float(look['sharpen']):.2f}")
    if any(look.get(x) for x in ("contrast", "saturation", "brightness")):
        lk.append(f"eq=contrast={look.get('contrast', 1.0)}:saturation={look.get('saturation', 1.0)}"
                  f":brightness={look.get('brightness', 0.0)}")
    if look.get("vignette"):
        lk.append("vignette=PI/5")
    if look.get("grain"):
        lk.append(f"noise=alls={int(look['grain'])}:allf=t")
    return ",".join(lk)


def render_edl(edl, base_dir=".", preview=False, out=None):
    require("ffmpeg"); require("ffprobe")
    W, H, fps = int(edl.get("w", 1080)), int(edl.get("h", 1920)), int(edl.get("fps", 30))
    out = out or edl.get("out", "out/montage.mp4")
    if not os.path.isabs(out):
        out = os.path.join(base_dir, out)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), ".tmp_" + os.path.splitext(os.path.basename(out))[0])
    os.makedirs(tmp, exist_ok=True)
    ctx = Ctx(base_dir, W, H, fps, tmp)

    music = ctx.path(edl["music"]) if edl.get("music") else None
    off = float(edl.get("music_offset", 0.0))
    if music:
        tempo, beats = beatlib.grid(music, off, beat_source=ctx.path(edl.get("beat_source")))
    else:
        tempo = float(edl.get("bpm", 120))
        beats = [i * 60.0 / tempo for i in range(800)]
    k = int(edl.get("start_beat", 0))
    t0, cuts = timeline(edl["segments"], beats, k)
    total = cuts[-1][1]
    print(f"[reel] tempo {tempo:.1f} BPM, {len(cuts)} segments, {total:.2f}s", flush=True)

    twins = []
    for ts in edl.get("titles", []):
        png = text_png(ts, W, H, tmp)
        ab, nb = float(ts.get("at_beat", 0)), float(ts.get("beats", 2))
        _, tc = timeline([{"beats": ab}, {"beats": nb}], beats, k)
        twins.append((png, tc[1][0], tc[1][1], ts))

    parts = []
    for i, (s, e, seg) in enumerate(cuts):
        dur = e - s
        if preview and seg.get("type", "video") == "video":
            seg = dict(seg); seg["speed"] = max(float(seg.get("speed", 1.0)), 1.0)
        tl = [(png, st - s, en - s, sp) for (png, st, en, sp) in twins if st < e - 0.01 and en > s + 0.01]
        parts.append(render_segment(seg, i, ctx, dur, tl))
        print(f"  [{i:02d}] {s:6.2f}-{e:6.2f} ({dur:.2f}s) {seg.get('type', 'video')} {seg.get('src', '')}"
              + (f"  +{len(tl)} title" if tl else ""), flush=True)

    lst = os.path.join(tmp, "concat.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    base = os.path.join(tmp, "base.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])

    inputs, fchain = ["-i", base], []
    vlabel = "0:v"
    lk = look_chain(edl.get("look", {}))
    if lk:
        fchain.append(f"[0:v]{lk}[lk]"); vlabel = "[lk]"
    au = edl.get("audio", {})
    afi, afo = float(au.get("fade_in", 0.2)), float(au.get("fade_out", 1.5))
    gain = float(au.get("gain_db", 0))
    if music:
        inputs += ["-ss", f"{off + t0:.4f}", "-t", f"{total:.4f}", "-i", music]
    else:
        inputs += ["-f", "lavfi", "-t", f"{total:.4f}", "-i", "anullsrc=r=48000:cl=stereo"]
    fchain.append(f"[1:a]afade=t=in:st=0:d={afi:.2f},afade=t=out:st={max(0, total - afo):.3f}:d={afo:.2f},"
                  f"volume={gain:.1f}dB,aresample=48000[mus]")
    alabel = "[mus]"
    if au.get("voice"):
        vat = float(au.get("voice_at", 0.0))
        inputs += ["-i", ctx.path(au["voice"])]
        ms = int(vat * 1000)
        fchain.append(f"[2:a]aresample=48000,volume={float(au.get('voice_gain_db', 0)):.1f}dB,"
                      f"adelay={ms}|{ms},apad[vo]")
        fchain.append("[vo]asplit=2[vo1][vo2]")
        duck = float(au.get("duck_db", -12))
        ratio = max(2.0, min(20.0, abs(duck)))
        fchain.append(f"[mus][vo1]sidechaincompress=threshold=0.03:ratio={ratio:.1f}:attack=20:release=300[ducked]")
        fchain.append("[ducked][vo2]amix=inputs=2:duration=first:normalize=0[a]")
        alabel = "[a]"
    run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fchain),
         "-map", vlabel, "-map", alabel,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.4f}", out])
    print(f"[reel] OUT {out} ({total:.2f}s)", flush=True)
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="reel montage", description="Render a beat-locked montage from an EDL JSON file.")
    ap.add_argument("edl", help="path to EDL .json")
    ap.add_argument("--out", help="override output path")
    ap.add_argument("--preview", action="store_true", help="fast render: skip slow-motion interpolation")
    a = ap.parse_args(argv)
    edl = json.load(open(a.edl, encoding="utf-8"))
    out = os.path.abspath(a.out) if a.out else None  # --out is relative to the current folder, EDL "out" to the EDL
    render_edl(edl, base_dir=os.path.dirname(os.path.abspath(a.edl)), preview=a.preview, out=out)


if __name__ == "__main__":
    main(sys.argv[1:])
