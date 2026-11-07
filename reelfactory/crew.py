"""Agent mode: many Claude Code or Codex agents work at the same time on one project.

A plan lists tasks; each task gets a role (editor, motion-designer, captioner, scriptwriter, qa), its own folder,
and may wait for other tasks (`after`). Independent tasks run in parallel; waiting tasks receive the reports of
the tasks they waited for (so QA sees what the editors made).

  reel crew example > plan.json          sample plan
  reel crew plan.json                    run it (engine from the plan, default claude)
  reel crew plan.json --engine codex --parallel 3
  reel crew plan.json --dry-run          print what would run
  reel crew roles                        list roles
  reel crew export-codex                 write .codex/agents/*.toml from .claude/agents/*.md

Plan:
  {"engine": "claude", "parallel": 3, "model": null, "brief": "shared brief for all agents",
   "tasks": [
     {"id": "A", "role": "editor", "prompt": "Variant A, punchy, track1 ...", "outputs": ["out/A.mp4"]},
     {"id": "B", "role": "editor", "prompt": "Variant B, smooth, track2 ...", "outputs": ["out/B.mp4"]},
     {"id": "title", "role": "motion-designer", "prompt": "Intro title ...", "outputs": ["out/title.mp4"]},
     {"id": "qa", "role": "qa", "after": ["A", "B", "title"], "prompt": "Review all three"}]}

Workers never get paid APIs: REEL_NO_PAID=1 is set, so `reel kie` and `reel voice say` refuse to spend money.
Claude workers may only use file tools and reel/ffmpeg commands (permission mode dontAsk).
Codex workers run in the workspace-write sandbox (use --codex-sandbox danger-full-access if browser renders fail).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

from .parallel import run_all, summary

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.join(ROOT, ".claude", "agents")

EXAMPLE = {
    "engine": "claude", "parallel": 3, "model": None,
    "brief": "Project folder media/demo. Vertical 9:16 Reel for a summer sale. Accent colour #ffcc00. Russian text.",
    "tasks": [
        {"id": "script", "role": "scriptwriter", "prompt": "Write 3 hooks and a 15 s script for the summer sale video.",
         "outputs": ["out/crew/script/SCRIPT.md"]},
        {"id": "intro", "role": "motion-designer",
         "prompt": "Render an intro with reel remotion KineticTitle, lines ЛЕТО, *СКИДКИ*, ДО -50%. Save out/crew/intro.mp4",
         "outputs": ["out/crew/intro.mp4"]},
        {"id": "edit", "role": "editor",
         "prompt": "Make a 15 s punchy montage of media/demo with music media/demo/beat.wav using reel auto, "
                   "then fix the EDL by eye. Save out/crew/edit.mp4", "outputs": ["out/crew/edit.mp4"]},
        {"id": "qa", "role": "qa", "after": ["intro", "edit"], "prompt": "Review out/crew/intro.mp4 and out/crew/edit.mp4."},
    ],
}


def parse_role(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", txt, re.S)
    meta, body = {}, txt
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        body = m.group(2).strip()
    meta["body"] = body
    meta["tools"] = [t.strip() for t in meta.get("tools", "").split(",") if t.strip()]
    return meta


def roles():
    out = {}
    if os.path.isdir(AGENTS):
        for f in sorted(os.listdir(AGENTS)):
            if f.endswith(".md"):
                r = parse_role(os.path.join(AGENTS, f))
                out[r["name"].replace("reel-", "")] = r
    return out


def export_codex(dest=None):
    dest = dest or os.path.join(ROOT, ".codex", "agents")
    os.makedirs(dest, exist_ok=True)
    for key, r in roles().items():
        body = r["body"].replace('"""', "'''")
        desc = r.get("description", "").replace('"', "'")
        with open(os.path.join(dest, r["name"] + ".toml"), "w", encoding="utf-8") as f:
            f.write(f'name = "{r["name"]}"\ndescription = "{desc}"\ndeveloper_instructions = """\n{body}\n"""\n')
    print(f"[reel] wrote Codex agents to {dest}")


def reel_cmd():
    venv = os.path.join(ROOT, ".venv", "bin", "reel")
    if os.path.exists(venv):
        return venv
    return shutil.which("reel") or f"{sys.executable} -m reelfactory"


def build_prompt(task, role, brief, taskdir, earlier):
    outs = ", ".join(task.get("outputs", [])) or "(files in your task folder)"
    parts = [
        f"You are one of several AI agents working at the same time in the Reel Factory repo at {ROOT}.",
        "Read AGENTS.md first, then the skills your role names.",
        "", "## Your role", role["body"] if role else "General Reel Factory agent.",
    ]
    if brief:
        parts += ["", "## Shared brief (same for every agent)", brief]
    parts += ["", f"## Your task ({task['id']})", task["prompt"],
              "", "## Rules for this run",
              f"- Your task folder: {taskdir}. Put drafts, EDLs and notes there.",
              f"- Expected outputs: {outs}.",
              "- Other agents work in parallel: never edit, move or delete files outside your task folder and your outputs.",
              "- Paid APIs are disabled (REEL_NO_PAID=1). Do not try kie.ai or ElevenLabs generation.",
              f"- Run reel as: {reel_cmd()}",
              "- Do not ask questions; nobody is watching. Make sensible choices and state them in the report.",
              "- Finish with a short final report: files made, what you checked, what you could not do."]
    if earlier:
        parts += ["", "## Reports of the tasks you waited for"] + earlier
    return "\n".join(parts)


def engine_cmd(engine, prompt, role, model, final_path, codex_sandbox):
    if engine == "claude":
        if not shutil.which("claude"):
            raise SystemExit("[reel] Claude Code CLI not found (npm install -g @anthropic-ai/claude-code)")
        allowed = ["Read", "Glob", "Grep"]
        tools = role["tools"] if role else ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
        if "Write" in tools:
            allowed.append("Write")
        if "Edit" in tools:
            allowed.append("Edit")
        if "Bash" in tools:
            rc = reel_cmd()
            allowed += [f"Bash({c} *)" for c in ("reel", rc, "python3 -m reelfactory", "ffmpeg", "ffprobe",
                                                 "ls", "mkdir", "cp", "cat", "head")]
        cmd = ["claude", "-p", prompt, "--permission-mode", "dontAsk", "--output-format", "text", "--allowedTools"] + allowed
        if model:
            cmd += ["--model", model]
        return cmd
    if engine == "codex":
        if not shutil.which("codex"):
            raise SystemExit("[reel] Codex CLI not found (npm install -g @openai/codex)")
        cmd = ["codex", "exec", "-C", ROOT, "-s", codex_sandbox, "--skip-git-repo-check", "-o", final_path]
        if model:
            cmd += ["-m", model]
        return cmd + [prompt]
    raise SystemExit(f"[reel] unknown engine {engine}: use claude or codex")


def preflight(engine):
    """Fail fast when the agent CLI is missing or not signed in."""
    exe = shutil.which(engine)
    if not exe:
        hint = "npm install -g @anthropic-ai/claude-code" if engine == "claude" else "npm install -g @openai/codex"
        raise SystemExit(f"[reel] {engine} CLI not found: {hint}")
    cmd = [exe, "auth", "status"] if engine == "claude" else [exe, "login", "status"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return
    out = (r.stdout + r.stderr).lower()
    if '"loggedin": false' in out or "not logged in" in out:
        raise SystemExit(f"[reel] {engine} is not signed in. Run `{engine}` in a terminal and log in "
                         f"(Claude: /login, Codex: codex login), then start the crew again.")


def run_plan(plan, engine=None, parallel=None, model=None, dry=False, timeout=1800, codex_sandbox="workspace-write",
             run_dir=None):
    engine = engine or plan.get("engine", "claude")
    parallel = parallel or plan.get("parallel", 3)
    model = model or plan.get("model")
    rl = roles()
    tasks = plan["tasks"]
    for t in tasks:
        if t.get("role") and t["role"] not in rl:
            raise SystemExit(f"[reel] task {t['id']}: unknown role {t['role']} (see `reel crew roles`)")
    if not dry:
        preflight(engine)
    run_dir = run_dir or os.path.join(ROOT, "out", "crew", time.strftime("run_%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    reports = {}

    def worker(task):
        role = rl.get(task.get("role"))
        taskdir = os.path.join(run_dir, task["id"])
        os.makedirs(taskdir, exist_ok=True)
        earlier = [f"### {d}\n{reports.get(d, '(no report)')}" for d in task.get("after", [])]
        prompt = build_prompt(task, role, plan.get("brief", ""), taskdir, earlier)
        final_path = os.path.join(taskdir, "REPORT.md")
        cmd = engine_cmd(engine, prompt, role, task.get("model", model), final_path, codex_sandbox)
        open(os.path.join(taskdir, "PROMPT.md"), "w", encoding="utf-8").write(prompt)
        if dry:
            print(f"--- {task['id']}: {engine}, role {task.get('role')}, prompt {os.path.join(taskdir, 'PROMPT.md')}")
            reports[task["id"]] = "(dry run)"
            return True, "dry run"
        env = dict(os.environ, REEL_NO_PAID="1")
        log = os.path.join(taskdir, "agent.log")
        with open(log, "w", encoding="utf-8") as f:
            try:
                r = subprocess.run(cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=f if engine == "codex" else subprocess.PIPE,
                                   stderr=f, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return False, f"timeout after {timeout}s"
        if engine == "claude":
            open(final_path, "w", encoding="utf-8").write(r.stdout or "")
            with open(log, "a", encoding="utf-8") as f:
                f.write(r.stdout or "")
        rep = open(final_path, encoding="utf-8").read().strip() if os.path.exists(final_path) else ""
        reports[task["id"]] = rep[-4000:] or "(empty report)"
        missing = [o for o in task.get("outputs", []) if not os.path.exists(os.path.join(ROOT, o))]
        if r.returncode != 0:
            text = open(log, encoding="utf-8", errors="ignore").read()
            if "authenticate" in text.lower() or "not logged in" in text.lower() or "login" in text.lower():
                return False, f"{engine} is not signed in: run `{engine}` once in a terminal and log in, then retry"
            return False, f"agent exit {r.returncode}, see {log}"
        if missing:
            return False, "missing outputs: " + ", ".join(missing)
        return True, (rep.splitlines() or [""])[0][:100]

    print(f"[reel] crew: {len(tasks)} tasks, engine {engine}, {parallel} agents at once, folder {run_dir}")
    st = run_all(tasks, worker, parallel, os.path.join(run_dir, "status.json"))
    print(summary(st))
    with open(os.path.join(run_dir, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("# Crew run\n\n```\n" + summary(st) + "\n```\n")
        for k, v in reports.items():
            f.write(f"\n## {k}\n\n{v}\n")
    print(f"[reel] reports: {os.path.join(run_dir, 'SUMMARY.md')}")
    return all(v["state"] == "done" for v in st.values())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel crew", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", help="plan.json, or: example | roles | export-codex")
    ap.add_argument("--engine", choices=["claude", "codex"])
    ap.add_argument("--parallel", type=int)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per task")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--codex-sandbox", default="workspace-write", choices=["read-only", "workspace-write", "danger-full-access"])
    a = ap.parse_args(argv)
    if a.plan == "example":
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2)); return 0
    if a.plan == "roles":
        for k, r in roles().items():
            print(f"  {k:<16} {r.get('description', '')[:110]}")
        return 0
    if a.plan == "export-codex":
        export_codex(); return 0
    plan = json.load(open(a.plan, encoding="utf-8"))
    ok = run_plan(plan, a.engine, a.parallel, a.model, a.dry_run, a.timeout, a.codex_sandbox)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
