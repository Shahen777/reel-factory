"""Voice-over with ElevenLabs (your own API key in ELEVENLABS_API_KEY or .env).

  reel voice list                         list voices on your account
  reel voice say "text" --voice ID --out vo.mp3 [--lang ru] [--model eleven_v4]
  reel voice say --file script.txt ...

Use your own, designed or library voices. Do not clone real people without their consent.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from .ffutil import load_env

API = "https://api.elevenlabs.io/v1"


def _key():
    load_env()
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        raise SystemExit("[reel] set ELEVENLABS_API_KEY (environment or .env). Get it at elevenlabs.io > Profile > API key")
    return k


def _req(method, path, body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"xi-api-key": _key(), "Content-Type": "application/json", "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[reel] ElevenLabs error {e.code}: {e.read().decode(errors='ignore')[:400]}")


def list_voices():
    j = json.loads(_req("GET", "/voices"))
    for v in j.get("voices", []):
        labels = ", ".join(f"{k}={x}" for k, x in (v.get("labels") or {}).items())
        print(f"{v['voice_id']}  {v.get('name', ''):<28} {v.get('category', ''):<10} {labels}")


def say(text, voice, out, model="eleven_v4", lang=None, stability=0.45, similarity=0.8, style=0.2, speed=1.0):
    if os.environ.get("REEL_NO_PAID"):
        raise SystemExit("[reel] paid voice-over is disabled for crew workers (REEL_NO_PAID). Ask the user first.")
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": stability, "similarity_boost": similarity, "style": style, "speed": speed}}
    if lang:
        body["language_code"] = lang
    audio = _req("POST", f"/text-to-speech/{voice}?output_format=mp3_44100_128", body, accept="audio/mpeg")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(audio)
    print(f"[reel] OUT {out} ({len(audio) // 1024} KB, {len(text)} characters billed)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel voice", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("say")
    s.add_argument("text", nargs="?")
    s.add_argument("--file", help="read the text from a file")
    s.add_argument("--voice", required=True, help="voice_id from `reel voice list`")
    s.add_argument("--out", default="out/voice.mp3")
    s.add_argument("--model", default="eleven_v4")
    s.add_argument("--lang", help="language code, e.g. ru, en, hy")
    s.add_argument("--stability", type=float, default=0.45)
    s.add_argument("--style", type=float, default=0.2)
    s.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args(argv)
    if a.cmd == "list":
        return list_voices()
    text = open(a.file, encoding="utf-8").read().strip() if a.file else a.text
    if not text:
        raise SystemExit("[reel] give text or --file")
    say(text, a.voice, a.out, a.model, a.lang, a.stability, 0.8, a.style, a.speed)


if __name__ == "__main__":
    main(sys.argv[1:])
