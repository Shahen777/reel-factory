"""AI images and video through kie.ai (your own key in KIE_API_KEY or .env).

Every paid command prints the price first and only runs with --yes.

  reel kie balance
  reel kie price veo                       search the public kie.ai price list
  reel kie image "prompt" [--ref photo.jpg] [--model nano-banana-2] [--ar 9:16] [--res 1K] --yes
  reel kie video "prompt" [--image first_frame.png] [--model veo3_lite] [--ar 9:16] --yes

Make original content: no deepfakes, no likeness of real people without consent.
"""
import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

from .ffutil import load_env

API = "https://api.kie.ai"
UPLOAD = "https://kieai.redpandaai.co/api/file-stream-upload"
PRICING = "https://api.kie.ai/client/v1/model-pricing/page"
UA = "reel-factory/0.1"

# rough credit prices to show before a run (1 credit is about $0.005). `reel kie price` gives live numbers.
EST = {
    "nano-banana-2": 8, "nano-banana-pro": 18, "nano-banana-2-1": 6,
    "veo3_lite": 30, "veo3_fast": 60, "veo3": 250,
}


def _key():
    load_env()
    k = os.environ.get("KIE_API_KEY")
    if not k:
        raise SystemExit("[reel] set KIE_API_KEY (environment or .env). Get it at https://kie.ai/api-key")
    return k


def _http(method, url, body=None, headers=None, raw=None, timeout=120):
    h = {"User-Agent": UA}
    h.update(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[reel] kie.ai error {e.code}: {e.read().decode(errors='ignore')[:400]}")


def api(method, path, body=None):
    j = json.loads(_http(method, API + path, body, {"Authorization": "Bearer " + _key()}))
    if j.get("code") not in (200, None):
        raise SystemExit(f"[reel] kie.ai: {j.get('msg')} (code {j.get('code')})")
    return j


def upload(path):
    """Upload a local file to kie.ai storage and return its URL (inputs must be URLs)."""
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    parts = []
    for name, val in (("uploadPath", "reel-factory"),):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
                 f"Content-Type: {ctype}\r\n\r\n".encode())
    parts.append(open(path, "rb").read())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    raw = b"".join(parts)
    j = json.loads(_http("POST", UPLOAD, raw=raw, timeout=300, headers={
        "Authorization": "Bearer " + _key(), "Content-Type": f"multipart/form-data; boundary={boundary}"}))
    url = (j.get("data") or {}).get("downloadUrl")
    if not url:
        raise SystemExit(f"[reel] upload failed: {j}")
    return url


def balance():
    j = api("GET", "/api/v1/chat/credit")
    print(f"[reel] kie.ai balance: {j.get('data')} credits")


def price(query):
    rows, page = [], 1
    while True:
        j = json.loads(_http("POST", PRICING, {"pageNum": page, "pageSize": 100}))
        d = j.get("data") or {}
        rows += d.get("records", [])
        if page >= int(d.get("pages", 1)):
            break
        page += 1
    q = query.lower().split()
    hits = [r for r in rows if all(w in (r.get("modelDescription") or "").lower() for w in q)]
    for r in hits[:60]:
        print(f"{r.get('creditPrice'):>8} cr  ${r.get('usdPrice'):<7} {r.get('creditUnit') or '':<20} {r.get('modelDescription')}")
    print(f"[reel] {len(hits)} rows match '{query}' (of {len(rows)})")


def _urls(data):
    resp = data.get("response") or {}
    if isinstance(resp, dict) and resp.get("resultUrls"):
        return resp["resultUrls"]
    rj = data.get("resultJson")
    if rj:
        rj = json.loads(rj) if isinstance(rj, str) else rj
        return rj.get("resultUrls") or []
    return []


def wait(task_id, veo=False, every=10, max_wait=1200):
    path = "/api/v1/veo/record-info" if veo else "/api/v1/jobs/recordInfo"
    t0 = time.time()
    while time.time() - t0 < max_wait:
        d = api("GET", f"{path}?taskId={task_id}").get("data") or {}
        if veo:
            flag = d.get("successFlag", 0)
            if flag == 1:
                return _urls(d)
            if flag in (2, 3):
                raise SystemExit(f"[reel] Veo failed: {d.get('errorMessage')}")
        else:
            st = d.get("state")
            if st == "success":
                return _urls(d)
            if st == "fail":
                raise SystemExit(f"[reel] task failed: {d.get('failMsg')}")
        print(f"  ... {int(time.time() - t0)} s", flush=True)
        time.sleep(every)
    raise SystemExit(f"[reel] timeout, task {task_id} is still running; check it in the kie.ai dashboard")


def fetch(url, out, tries=8):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300) as r:
                open(out, "wb").write(r.read())
            print(f"[reel] OUT {out}")
            return out
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  download retry {i + 1}: {e}")
            time.sleep(15 + i * 2)
    raise SystemExit(f"[reel] could not download {url}")


def gate(model, n, yes):
    est = EST.get(model)
    msg = f"~{est * n} credits (~${est * n * 0.005:.2f})" if est else "unknown price, run `reel kie price <model>`"
    print(f"[reel] {model} x{n}: {msg}")
    if not yes:
        raise SystemExit("[reel] not started. Re-run with --yes to pay and generate.")


def image(prompt, out, model="nano-banana-2", ar="9:16", res="1K", refs=(), yes=False):
    gate(model, 1, yes)
    inp = {"prompt": prompt, "aspect_ratio": ar, "resolution": res, "output_format": "png"}
    if refs:
        inp["image_input"] = [r if r.startswith("http") else upload(r) for r in refs]
    tid = api("POST", "/api/v1/jobs/createTask", {"model": model, "input": inp})["data"]["taskId"]
    print(f"[reel] task {tid}")
    urls = wait(tid)
    return fetch(urls[0], out)


def video(prompt, out, model="veo3_lite", ar="9:16", image_path=None, yes=False):
    gate(model, 1, yes)
    body = {"prompt": prompt, "model": model, "aspect_ratio": ar, "enableTranslation": True,
            "generationType": "TEXT_2_VIDEO"}
    if image_path:
        body["imageUrls"] = [image_path if image_path.startswith("http") else upload(image_path)]
        body["generationType"] = "FIRST_AND_LAST_FRAMES_2_VIDEO"
    tid = None
    for attempt in range(3):  # Veo sometimes returns transient INTERNAL errors
        try:
            tid = api("POST", "/api/v1/veo/generate", body)["data"]["taskId"]
            break
        except SystemExit as e:
            if attempt == 2 or "INTERNAL" not in str(e).upper():
                raise
            time.sleep(10)
    print(f"[reel] task {tid}")
    urls = wait(tid, veo=True)
    return fetch(urls[0], out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel kie", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("balance")
    p = sub.add_parser("price"); p.add_argument("query")
    i = sub.add_parser("image")
    i.add_argument("prompt"); i.add_argument("--out", default="out/image.png")
    i.add_argument("--model", default="nano-banana-2"); i.add_argument("--ar", default="9:16")
    i.add_argument("--res", default="1K"); i.add_argument("--ref", action="append", default=[])
    i.add_argument("--yes", action="store_true")
    v = sub.add_parser("video")
    v.add_argument("prompt"); v.add_argument("--out", default="out/video.mp4")
    v.add_argument("--model", default="veo3_lite", choices=["veo3_lite", "veo3_fast", "veo3"])
    v.add_argument("--ar", default="9:16"); v.add_argument("--image", help="first frame (file or URL)")
    v.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "balance":
        balance()
    elif a.cmd == "price":
        price(a.query)
    elif a.cmd == "image":
        image(a.prompt, a.out, a.model, a.ar, a.res, a.ref, a.yes)
    else:
        video(a.prompt, a.out, a.model, a.ar, a.image, a.yes)


if __name__ == "__main__":
    main(sys.argv[1:])
