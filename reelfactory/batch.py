"""Run many `reel` commands in parallel (render farm on one machine).

jobs file, JSON:
  {"parallel": 3, "jobs": [
     {"id": "A", "cmd": "montage media/p/edl_A.json"},
     {"id": "B", "cmd": "montage media/p/edl_B.json"},
     {"id": "title", "cmd": "remotion KineticTitle --set 'lines=[\\"HELLO\\"]' --out out/title.mp4"},
     {"id": "subsA", "cmd": "subtitles out/edl_A.mp4 --lang ru", "after": ["A"]},
     {"id": "export", "cmd": "export out/edl_A_subs.mp4 --all", "after": ["subsA"]}]}
or a plain text file: one reel command per line (no dependencies), `#` for comments.

  reel batch jobs.json [--parallel 4] [--stop-on-fail]
Logs: out/batch/<name>/<id>.log, live status: out/batch/<name>/status.json
"""
import argparse
import json
import os
import shlex
import subprocess
import sys

from .parallel import run_all, summary


def load_jobs(path):
    if path.endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        return d.get("jobs", d if isinstance(d, list) else []), d.get("parallel") if isinstance(d, dict) else None
    jobs = []
    for i, line in enumerate(open(path, encoding="utf-8")):
        line = line.strip()
        if line and not line.startswith("#"):
            jobs.append({"id": f"job{len(jobs) + 1:02d}", "cmd": line})
    return jobs, None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel batch", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs")
    ap.add_argument("--parallel", type=int, help="jobs at once (default: file value or half the CPU cores)")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--out", help="log folder")
    a = ap.parse_args(argv)
    jobs, par = load_jobs(a.jobs)
    if not jobs:
        raise SystemExit("[reel] no jobs found")
    parallel = a.parallel or par or max(1, (os.cpu_count() or 2) // 2)
    logdir = a.out or os.path.join("out", "batch", os.path.splitext(os.path.basename(a.jobs))[0])
    os.makedirs(logdir, exist_ok=True)

    def worker(job):
        cmd = job["cmd"]
        args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
        if args and args[0] == "reel":
            args = args[1:]
        log = os.path.join(logdir, job["id"] + ".log")
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run([sys.executable, "-m", "reelfactory"] + args, stdout=f, stderr=subprocess.STDOUT)
        tail = open(log, encoding="utf-8", errors="ignore").read().strip().splitlines()[-1:] or [""]
        return r.returncode == 0, tail[0]

    print(f"[reel] {len(jobs)} jobs, {parallel} at once, logs in {logdir}")
    st = run_all(jobs, worker, parallel, os.path.join(logdir, "status.json"), a.stop_on_fail)
    print(summary(st))
    return 0 if all(v["state"] == "done" for v in st.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
