---
name: reel-crew
description: Agent mode — run many agents at the same time on one video project (several montage variants, motion titles, captions, scripts, QA in parallel) via Claude Code subagents, `reel crew` (headless Claude or Codex workers) or Ruflo swarms; and `reel batch` for parallel renders. Use for «агентский режим», «много агентов одновременно», «параллельно», «сделай сразу 5 вариантов», «рой агентов», «swarm», «Ruflo», «claude flow», «запусти агентов».
---

# reel-crew — many agents at once

Read `docs/AGENT_MODE.md`. Roles: `.claude/agents/reel-*.md` (editor, motion-designer, captioner, scriptwriter, qa).

## Choose the way

- **You are in an interactive Claude Code session:** spawn the role subagents yourself, all independent ones in ONE
  message so they run in parallel. Give each a task folder (`out/crew/<id>/`) and explicit output paths. When they
  finish, run a `reel-qa` subagent on every output, fix what QA reports, then present the results.
- **Headless / many variants / Codex:** write `plan.json` (see `reel crew example`), run `reel crew plan.json --dry-run`,
  then `reel crew plan.json [--engine codex] [--parallel N]`. Read `out/crew/<run>/SUMMARY.md` and look at the outputs
  with `reel watch` before reporting.
- **Only renders, no thinking needed:** `reel batch jobs.json` (many `reel` commands in parallel with `after`).
- **Ruflo:** only if the user asks for it or already has it; follow the Ruflo section of `docs/AGENT_MODE.md`.

## Planning rules

1. Split by independent outputs: one variant, one title, one caption track per agent. Two agents never write the same file.
2. Put shared facts (folder, format, colours, language, music rights) into `brief`; keep each task prompt specific.
3. QA always last, with `after` on everything it reviews.
4. Parallel 3–4 on a laptop; renders are CPU-heavy. More agents do not help when they wait for the same CPU.
5. Paid generation stays outside the crew: show the price, get the user's yes, run it yourself.
6. Report: what each agent made, the QA verdicts, what failed or was skipped.
