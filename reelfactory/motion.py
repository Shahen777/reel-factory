"""Motion design from code: render an HTML/CSS/JS animation frame by frame to video.

Claude Code or Codex writes the animation as a web page; this renders it deterministically
(no real-time playback, every frame is computed from t), so the result is smooth and repeatable.

Page contract:
  window.renderFrame = (t, frame) => { ...draw the state at t seconds... }   // may return a Promise
  window.MOTION = {duration: 6, fps: 30, width: 1080, height: 1920}          // optional defaults
Injected before your code runs: window.DATA (from --data JSON or --set key=value),
window.BEATS (beat times of --music), fonts "Display" and "Sans" (bundled OFL fonts).

  reel motion list                                  built-in templates
  reel motion kinetic --set text="BIG IDEA" --out out/title.mp4
  reel motion my_scene.html --duration 8 --music track.mp3 --out out/scene.mp4
  reel motion lower_third --transparent --out out/overlay.mov   (alpha, for overlays)
Needs: pip install playwright, then `playwright install chromium` (or an installed Google Chrome).
"""
import argparse
import json
import os
import subprocess
import sys

from .ffutil import ASSETS, require

TEMPLATES = os.path.join(ASSETS, "motion")


def list_templates():
    for f in sorted(os.listdir(TEMPLATES)):
        if f.endswith(".html"):
            first = open(os.path.join(TEMPLATES, f), encoding="utf-8").read().split("-->")[0]
            desc = first.replace("<!--", "").strip().splitlines()[0] if "<!--" in first else ""
            print(f"  {f[:-5]:<14} {desc}")


def resolve(scene):
    if os.path.exists(scene):
        return os.path.abspath(scene)
    p = os.path.join(TEMPLATES, scene if scene.endswith(".html") else scene + ".html")
    if os.path.exists(p):
        return p
    raise SystemExit(f"[reel] scene not found: {scene} (see `reel motion list`)")


def _launch(p):
    try:
        return p.chromium.launch()
    except Exception:
        try:
            return p.chromium.launch(channel="chrome")
        except Exception:
            raise SystemExit("[reel] no browser for Playwright: run `playwright install chromium` "
                             "or install Google Chrome")


def font_css():
    fd = os.path.join(ASSETS, "fonts")
    return ("@font-face{font-family:'Display';src:url('file://%s/RussoOne-Regular.ttf');}"
            "@font-face{font-family:'Sans';src:url('file://%s/PTSans-Bold.ttf');}") % (fd, fd)


def render(scene, out, duration=None, fps=None, width=None, height=None, data=None, music=None,
           transparent=False, music_offset=0.0):
    require("ffmpeg")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("[reel] motion needs Playwright: pip install playwright && playwright install chromium")
    path = resolve(scene)
    beats = []
    if music:
        from .beats import beats_for
        beats = [b - music_offset for b in beats_for(music)["beats"] if b >= music_offset]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        init = "window.DATA=%s;window.BEATS=%s;" % (json.dumps(data or {}, ensure_ascii=False), json.dumps(beats))
        page.add_init_script(init)
        page.goto("file://" + path)
        page.add_style_tag(content=font_css())
        meta = page.evaluate("() => window.MOTION || {}")
        D = float(duration or meta.get("duration", 6))
        F = int(fps or meta.get("fps", 30))
        W = int(width or meta.get("width", 1080))
        H = int(height or meta.get("height", 1920))
        page.set_viewport_size({"width": W, "height": H})
        page.evaluate("async () => { await document.fonts.load('100px Display'); await document.fonts.load('100px Sans'); await document.fonts.ready; }")
        if not page.evaluate("() => typeof window.renderFrame === 'function'"):
            raise SystemExit("[reel] the page must define window.renderFrame = (t, frame) => {...}")
        n = int(round(D * F))
        enc = (["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"] if transparent else
               ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"])
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(F), "-i", "-"]
        if music:
            cmd += ["-ss", f"{music_offset:.3f}", "-t", f"{D:.3f}", "-i", music, "-map", "0:v", "-map", "1:a",
                    "-c:a", "aac" if not transparent else "pcm_s16le", "-af", f"afade=t=out:st={max(0, D - 1):.2f}:d=1"]
        cmd += enc + (["-movflags", "+faststart"] if not transparent else []) + ["-t", f"{D:.3f}", out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(n):
                t = i / F
                page.evaluate("([t, i]) => window.renderFrame(t, i)", [t, i])
                ff.stdin.write(page.screenshot(type="png", omit_background=transparent,
                                               clip={"x": 0, "y": 0, "width": W, "height": H}))
                if i % F == 0:
                    print(f"  frame {i}/{n}", flush=True)
        finally:
            ff.stdin.close()
            ff.wait()
            browser.close()
    if ff.returncode != 0:
        raise SystemExit("[reel] ffmpeg failed while encoding frames")
    print(f"[reel] OUT {out} ({W}x{H}, {D:.1f}s, {F} fps{', alpha' if transparent else ''})")
    return out


def parse_set(pairs):
    d = {}
    for kv in pairs or []:
        k, _, v = kv.partition("=")
        try:
            d[k] = json.loads(v)
        except ValueError:
            d[k] = v
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel motion", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", help="template name, path to .html, or `list`")
    ap.add_argument("--out")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--fps", type=int)
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--data", help="JSON file passed to the page as window.DATA")
    ap.add_argument("--set", action="append", metavar="KEY=VALUE", help="set one DATA value (repeatable)")
    ap.add_argument("--music", help="audio to mux; its beats go to window.BEATS")
    ap.add_argument("--music-offset", type=float, default=0.0)
    ap.add_argument("--transparent", action="store_true", help="alpha channel, ProRes 4444 .mov")
    a = ap.parse_args(argv)
    if a.scene == "list":
        return list_templates()
    data = json.load(open(a.data, encoding="utf-8")) if a.data else {}
    data.update(parse_set(a.set))
    name = os.path.splitext(os.path.basename(a.scene))[0]
    out = a.out or os.path.join("out", name + (".mov" if a.transparent else ".mp4"))
    render(a.scene, out, a.duration, a.fps, a.width, a.height, data, a.music, a.transparent, a.music_offset)


if __name__ == "__main__":
    main(sys.argv[1:])
