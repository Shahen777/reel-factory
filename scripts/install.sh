#!/usr/bin/env bash
# Install Reel Factory: Python package + optional global skills for Claude Code and Codex.
#   ./scripts/install.sh            install the `reel` command (editable) with speech support
#   ./scripts/install.sh --skills   also copy skills to ~/.claude/skills and ~/.agents/skills
set -e
cd "$(dirname "$0")/.."

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is missing."
  echo "  macOS:   brew install ffmpeg"
  echo "  Ubuntu:  sudo apt install ffmpeg"
  echo "  Windows: winget install Gyan.FFmpeg"
  exit 1
fi

PY=${PYTHON:-python3}
$PY -m pip install --upgrade pip >/dev/null
$PY -m pip install -e ".[all,dev]"
$PY -m playwright install chromium || echo "playwright browser not installed: reel motion will try Google Chrome"

if [ "$1" = "--skills" ]; then
  for dest in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
    mkdir -p "$dest"
    for s in .claude/skills/*/; do
      name=$(basename "$s")
      rm -rf "${dest:?}/${name:?}"
      cp -R "$s" "$dest/$name"
    done
    echo "skills copied to $dest"
  done
fi

reel doctor
echo
echo "Done. Try:  python3 examples/make_demo.py   then open out/demo.mp4"
