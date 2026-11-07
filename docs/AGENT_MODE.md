# Agent mode: many agents at once

Reel Factory gives you three ways to run several AI agents in parallel on one video project.
All of them use the same roles: `editor`, `motion-designer`, `captioner`, `scriptwriter`, `qa`.

| way | install | engines | best for |
|---|---|---|---|
| 1. Subagents inside your Claude Code session | nothing | Claude Code | everyday work, you watch and steer |
| 2. `reel crew plan.json` | nothing | Claude Code CLI or Codex CLI, headless | many variants at once, overnight batches |
| 3. Ruflo swarms (optional) | Ruflo plugin | Claude Code, Codex via MCP | big swarms, shared memory between agents |

For pure rendering with no AI agents (many EDLs, exports, titles) use `reel batch jobs.json`.

## 1. Subagents in Claude Code

The roles live in `.claude/agents/reel-*.md`, and Claude Code loads them automatically. Ask the lead session in plain words:

> Make three variants of the Reel from media/trip in parallel: one editor per music track, a motion-designer for the
> intro title, then a QA agent checks all of them.

The lead agent starts the subagents at the same time, each with its own task folder, then merges the results.

## 2. `reel crew` — headless agents, Claude or Codex

```bash
reel crew example > plan.json      # sample plan
reel crew plan.json --dry-run      # show the tasks and prompts (PROMPT.md per task)
reel crew plan.json                # run with Claude Code (default)
reel crew plan.json --engine codex --parallel 4
```

A plan:

```json
{"engine": "claude", "parallel": 3, "brief": "shared brief for every agent",
 "tasks": [
   {"id": "A", "role": "editor", "prompt": "Variant A ...", "outputs": ["out/A.mp4"]},
   {"id": "B", "role": "editor", "prompt": "Variant B ...", "outputs": ["out/B.mp4"]},
   {"id": "title", "role": "motion-designer", "prompt": "Intro ...", "outputs": ["out/title.mp4"]},
   {"id": "qa", "role": "qa", "after": ["A", "B", "title"], "prompt": "Review all three", "outputs": ["out/QA.md"]}]}
```

- Tasks without `after` start at once, up to `parallel` agents at a time. A task with `after` waits and receives the
  final reports of those tasks in its prompt.
- Each run gets `out/crew/run_<time>/<task>/` with `PROMPT.md`, `agent.log`, `REPORT.md`, plus `status.json`
  (live) and `SUMMARY.md`.
- A task fails when the agent exits with an error or a listed output file is missing; tasks waiting for it are skipped.
- `examples/crew_demo.json` is a small working plan.

Safety:

- Workers get `REEL_NO_PAID=1`, so `reel kie` and `reel voice say` refuse to spend money. Run paid steps yourself
  after the user approves the price.
- Claude workers run with `--permission-mode dontAsk` and may only use file tools plus `reel`, `ffmpeg` and `ffprobe`.
- Codex workers run in the `workspace-write` sandbox. If browser renders (`reel motion`, `reel remotion`) fail inside the
  sandbox, use `--codex-sandbox danger-full-access` only on a machine you trust.
- Each agent is told to write only inside its own task folder and outputs, so parallel agents do not overwrite each other.

Codex also gets the roles as `.codex/agents/reel-*.toml`. Regenerate them after editing a role with `reel crew export-codex`.

## 3. Ruflo (optional)

[Ruflo](https://github.com/ruvnet/ruflo), formerly Claude Flow, is a third-party, MIT-licensed meta-harness for
Claude Code and Codex. It adds swarms, shared memory and many ready agents. It is not required for Reel Factory.

The lightest way, which writes no files into the project, is the Claude Code plugin:

```
/plugin marketplace add ruvnet/ruflo
/plugin install ruflo-core@ruflo
```

To get its MCP tools (swarms, memory) in Claude Code or Codex:

```bash
claude mcp add claude-flow -- npx ruflo@latest mcp start
```

Then ask for a swarm that uses our roles and commands, for example:
"spawn a swarm: 3 reel-editor agents for variants A/B/C, 1 reel-motion-designer, then reel-qa; follow AGENTS.md".

Be careful with `npx ruflo@latest init`. It writes its own `CLAUDE.md`, `.claude/` settings, hooks and a background
daemon into the project. That can override the Reel Factory rules, so run it in a copy of the repo or keep our
`CLAUDE.md` and `AGENTS.md`. Plugins run with your account's permissions, so review them before installing.
Commands change often; check the Ruflo README.
