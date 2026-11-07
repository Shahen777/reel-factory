# SETUP — for AI agents installing Reel Factory on a computer

The user asked you (Claude Code, Codex or another agent) to install Reel Factory, maybe on a brand-new computer.
Follow these steps in order. Run the commands yourself; stop and ask the user only where marked **USER**.

## 1. Detect the system

`uname -s` (Darwin = macOS, Linux). On Windows you are in PowerShell.

## 2. Run the bootstrap

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Shahen777/reel-factory/main/scripts/bootstrap.sh | bash
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/Shahen777/reel-factory/main/scripts/bootstrap.ps1 | iex
```

Already inside a clone? Run `./scripts/bootstrap.sh` from the repo root instead.

The bootstrap installs what is missing (git, ffmpeg, Python, Node.js, yt-dlp), clones the repo to `~/reel-factory`,
creates `.venv`, installs the Python packages (Whisper, Playwright), the Chromium browser for motion design and the
Remotion packages. It links the `reel` command into `~/.local/bin`, copies the skills to `~/.claude/skills` and
`~/.agents/skills`, runs `reel doctor` and renders a demo. It takes 3–10 minutes and downloads about 1 GB.

## 3. When the script stops with "ACTION NEEDED"

Exit code 2 means a step needs the user's password or a manual install. **USER:** show the exact command from the
message and ask the user to run it in their own terminal. Never type or ask for their password yourself. Then run the
bootstrap again.

- macOS without Homebrew: the Homebrew install command from https://brew.sh
- Linux without cached sudo rights: the printed `sudo apt-get install ...` line
- Windows without winget: install "App Installer" from the Microsoft Store

## 4. Verify

```bash
cd ~/reel-factory
./.venv/bin/reel doctor          # Windows: .\.venv\Scripts\reel doctor
ls out/demo.mp4
./.venv/bin/reel motion kinetic --set text="HELLO" --out out/check_motion.mp4
./.venv/bin/reel remotion TextReveal --set title="HELLO" --out out/check_remotion.mp4
./.venv/bin/reel watch out/check_remotion.mp4 --no-audio
```

Every required line of `reel doctor` must say `ok`. Read the sheet image from `reel watch` to confirm the render.

## 5. Optional keys

Only if the user wants paid features: copy `.env.example` to `.env` and ask the user to paste their own
`ELEVENLABS_API_KEY` / `KIE_API_KEY` into that file themselves. Do not ask them to paste keys into the chat.

## 6. Tell the user

Where it is installed, that `reel doctor` passed, where the demo is, and how to start:
`cd ~/reel-factory && claude` (or `codex`), then ask in plain words, e.g. "make a dynamic Reel from media/trip to track.mp3".

## Troubleshooting

| symptom | fix |
|---|---|
| `reel: command not found` | open a new terminal, or use `~/reel-factory/.venv/bin/reel` |
| `ffmpeg` missing | macOS `brew install ffmpeg`, Ubuntu `sudo apt install ffmpeg`, Windows `winget install Gyan.FFmpeg` |
| motion: no browser | `./.venv/bin/python -m playwright install chromium` |
| remotion: npx missing | install Node.js 18+, then `cd remotion && npm install` |
| Whisper slow on first run | it downloads the model once (small is about 500 MB) |
| download: "not a bot" or sign-in | the site blocks automated downloads; ask the user for the file |
