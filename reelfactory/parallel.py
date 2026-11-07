"""Run many jobs at once with dependencies (`after`), live status file and a summary table."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait


def check_graph(jobs):
    ids = [j["id"] for j in jobs]
    if len(ids) != len(set(ids)):
        raise SystemExit("[reel] job ids must be unique")
    known = set(ids)
    for j in jobs:
        for d in j.get("after", []):
            if d not in known:
                raise SystemExit(f"[reel] job {j['id']} waits for unknown job {d}")
    # cycle check (Kahn)
    deps = {j["id"]: set(j.get("after", [])) for j in jobs}
    done = set()
    while True:
        ready = [k for k, v in deps.items() if k not in done and v <= done]
        if not ready:
            break
        done |= set(ready)
    if len(done) != len(jobs):
        raise SystemExit("[reel] jobs wait for each other in a circle: " + ", ".join(sorted(set(deps) - done)))


def run_all(jobs, worker, parallel=4, status_path=None, stop_on_fail=False):
    """worker(job) -> (ok: bool, note: str). Returns dict id -> status record."""
    check_graph(jobs)
    lock = threading.Lock()
    st = {j["id"]: {"state": "waiting", "after": j.get("after", []), "note": "", "seconds": 0} for j in jobs}

    def save():
        if status_path:
            tmp = status_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False, indent=1)
            os.replace(tmp, status_path)

    def wrapped(job):
        t0 = time.time()
        with lock:
            st[job["id"]]["state"] = "running"; save()
        print(f"[reel] start {job['id']}", flush=True)
        try:
            ok, note = worker(job)
        except Exception as e:  # keep the queue alive
            ok, note = False, f"{type(e).__name__}: {e}"
        except SystemExit as e:
            ok, note = False, str(e)
        with lock:
            st[job["id"]].update(state="done" if ok else "failed", note=note, seconds=round(time.time() - t0, 1))
            save()
        print(f"[reel] {'done' if ok else 'FAILED'} {job['id']} ({time.time() - t0:.0f}s) {note[:120]}", flush=True)
        return ok

    by_id = {j["id"]: j for j in jobs}
    pending = [j["id"] for j in jobs]
    running = {}
    save()
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
        while pending or running:
            failed = {k for k, v in st.items() if v["state"] in ("failed", "skipped")}
            for jid in list(pending):
                deps = set(by_id[jid].get("after", []))
                if deps & failed or (stop_on_fail and failed):
                    st[jid].update(state="skipped", note="a job it waits for failed"); pending.remove(jid); save()
                    continue
                if len(running) < parallel and all(st[d]["state"] == "done" for d in deps):
                    running[ex.submit(wrapped, by_id[jid])] = jid
                    pending.remove(jid)
            if not running:
                if pending:  # only blocked jobs remain
                    continue
                break
            finished, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for fut in finished:
                running.pop(fut)
    return st


def summary(st):
    lines = [f"{'job':<18} {'state':<8} {'sec':>6}  note"]
    for k, v in st.items():
        lines.append(f"{k:<18} {v['state']:<8} {v['seconds']:>6}  {v['note'][:90]}")
    n_ok = sum(v["state"] == "done" for v in st.values())
    lines.append(f"{n_ok}/{len(st)} done")
    return "\n".join(lines)
