"""Download video or audio from YouTube, TikTok, Instagram, VK, X and 1000+ sites (yt-dlp).

  reel download URL                       best mp4 up to 1080p into media/downloads/
  reel download URL --section 0:12-0:27   only that part (fast, good for references)
  reel download URL --audio               audio only (mp3)
  reel download URL1 URL2 --out media/refs
  reel download --list urls.txt

Download only what you have the right to use: your own videos, clips you licensed, or references
for analysis. Do not re-upload other people's videos as your own.
If a site asks to sign in or to prove you are not a bot, download the file in your browser instead.
"""
import argparse
import os
import shutil
import subprocess
import sys


def _ytdlp():
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        raise SystemExit("[reel] needs yt-dlp: pip install yt-dlp (or brew install yt-dlp)")


def download(url, out="media/downloads", audio=False, max_height=1080, section=None, name=None):
    os.makedirs(out, exist_ok=True)
    tpl = os.path.join(out, (name or "%(uploader|unknown)s_%(id)s") + ".%(ext)s")
    cmd = _ytdlp() + ["--no-playlist", "--restrict-filenames", "-o", tpl, "--print", "after_move:filepath",
                      "--no-simulate", "--no-warnings"]
    if audio:
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        cmd += ["-f", f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/bv*[height<={max_height}]+ba/b[height<={max_height}]/b",
                "--merge-output-format", "mp4"]
    if section:
        a, _, b = section.partition("-")
        cmd += ["--download-sections", f"*{a}-{b}", "--force-keyframes-at-cuts"]
    cmd.append(url)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    err = r.stderr.strip()
    if r.returncode != 0:
        low = err.lower()
        if "sign in" in low or "not a bot" in low or "login" in low or "cookies" in low:
            raise SystemExit(f"[reel] {url}: the site wants a sign-in or a bot check. "
                             "Open it in your browser, save the file and pass its path instead.")
        raise SystemExit(f"[reel] download failed for {url}:\n{err[-600:]}")
    path = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1:]
    p = path[0] if path else out
    print(f"[reel] OUT {p}")
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel download", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--list", help="text file with one URL per line")
    ap.add_argument("--out", default="media/downloads")
    ap.add_argument("--audio", action="store_true", help="audio only, mp3")
    ap.add_argument("--max-height", type=int, default=1080)
    ap.add_argument("--section", help="only a part, e.g. 0:12-0:27 or 75-90")
    ap.add_argument("--name", help="file name without extension (single URL)")
    a = ap.parse_args(argv)
    urls = list(a.urls)
    if a.list:
        urls += [u.strip() for u in open(a.list, encoding="utf-8") if u.strip() and not u.startswith("#")]
    if not urls:
        ap.error("give at least one URL")
    failed = 0
    for u in urls:
        try:
            download(u, a.out, a.audio, a.max_height, a.section, a.name if len(urls) == 1 else None)
        except SystemExit as e:
            print(e, file=sys.stderr)
            failed += 1
    if failed:
        raise SystemExit(f"[reel] {failed} of {len(urls)} downloads failed")


if __name__ == "__main__":
    main(sys.argv[1:])
