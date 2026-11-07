#!/usr/bin/env bash
# Reel Factory: full setup on a clean macOS or Linux computer.
#   curl -fsSL https://raw.githubusercontent.com/Shahen777/reel-factory/main/scripts/bootstrap.sh | bash
# or, inside a clone:  ./scripts/bootstrap.sh
# Options (env): REEL_DIR=~/reel-factory  REEL_NO_GLOBAL=1 (skip ~/.local/bin link and global skills)
#                REEL_LIGHT=1 (skip Whisper, Playwright browser and Remotion packages)
set -e
REPO="https://github.com/Shahen777/reel-factory.git"
say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
need_user() { printf '\n\033[33mACTION NEEDED:\033[0m %s\n' "$*"; exit 2; }

OS=$(uname -s)
say "System: $OS $(uname -m)"

# 1. system tools
if [ "$OS" = "Darwin" ]; then
  if ! command -v brew >/dev/null 2>&1; then
    for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$($b shellenv)"; done
  fi
  if ! command -v brew >/dev/null 2>&1; then
    need_user "Homebrew is not installed. It asks for your Mac password, so run this yourself in Terminal, then start this script again:
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  fi
  PKGS=""
  command -v git >/dev/null 2>&1 || PKGS="$PKGS git"
  command -v ffmpeg >/dev/null 2>&1 || PKGS="$PKGS ffmpeg"
  command -v python3 >/dev/null 2>&1 || PKGS="$PKGS python"
  command -v node >/dev/null 2>&1 || PKGS="$PKGS node"
  command -v yt-dlp >/dev/null 2>&1 || PKGS="$PKGS yt-dlp"
  if [ -n "$PKGS" ]; then say "brew install$PKGS"; brew install $PKGS; fi
elif [ "$OS" = "Linux" ]; then
  APT=""
  command -v git >/dev/null 2>&1 || APT="$APT git"
  command -v ffmpeg >/dev/null 2>&1 || APT="$APT ffmpeg"
  command -v python3 >/dev/null 2>&1 || APT="$APT python3 python3-pip"
  python3 -c "import venv, ensurepip" 2>/dev/null || APT="$APT python3-venv"
  command -v npm >/dev/null 2>&1 || APT="$APT nodejs npm"
  if [ -n "$APT" ]; then
    if command -v apt-get >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
      say "apt-get install$APT"; sudo apt-get update -y && sudo apt-get install -y $APT
    elif command -v apt-get >/dev/null 2>&1; then
      need_user "Install system packages (needs your password), then run this script again:
  sudo apt-get update && sudo apt-get install -y$APT"
    else
      need_user "Install with your package manager:$APT, then run this script again."
    fi
  fi
else
  need_user "On Windows use scripts/bootstrap.ps1 in PowerShell."
fi

# 2. code
HERE=$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")
if [ -n "$HERE" ] && [ -f "$HERE/../pyproject.toml" ] && grep -q 'name = "reel-factory"' "$HERE/../pyproject.toml"; then
  DIR=$(cd "$HERE/.." && pwd)
elif [ -f pyproject.toml ] && grep -q 'name = "reel-factory"' pyproject.toml; then
  DIR=$(pwd)
else
  DIR=${REEL_DIR:-$HOME/reel-factory}
  if [ -d "$DIR/.git" ]; then say "Updating $DIR"; git -C "$DIR" pull --ff-only
  else say "Cloning into $DIR"; git clone --depth 1 "$REPO" "$DIR"; fi
fi
cd "$DIR"

# 3. python environment
say "Python environment in $DIR/.venv"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/python -m pip install -q --upgrade pip
if [ -n "$REEL_LIGHT" ]; then
  ./.venv/bin/python -m pip install -q -e ".[download,dev]"
else
  ./.venv/bin/python -m pip install -q -e ".[all,dev]"
  say "Browser for motion design (Playwright Chromium)"
  ./.venv/bin/python -m playwright install chromium || echo "Playwright browser not installed; reel motion will use Google Chrome if present"
  if command -v npm >/dev/null 2>&1; then
    say "Remotion packages"; (cd remotion && npm install --no-audit --no-fund --loglevel=error)
  fi
fi

# 4. command + skills available everywhere
if [ -z "$REEL_NO_GLOBAL" ]; then
  mkdir -p "$HOME/.local/bin"
  ln -sf "$DIR/.venv/bin/reel" "$HOME/.local/bin/reel"
  for dest in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
    mkdir -p "$dest"
    for s in .claude/skills/*/; do
      n=$(basename "$s")
      rm -rf "${dest:?}/${n:?}"
      cp -R "$s" "$dest/$n"
    done
  done
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *)
      for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
        if [ -f "$rc" ] || { [ "$rc" = "$HOME/.zshrc" ] && [ "$OS" = "Darwin" ]; }; then
          grep -q '.local/bin' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
      done
      export PATH="$HOME/.local/bin:$PATH";;
  esac
fi

# 5. check
say "Check"
./.venv/bin/reel doctor || true
say "Demo render"
./.venv/bin/python examples/make_demo.py >/dev/null && echo "demo OK: $DIR/out/demo.mp4"
printf '\n\033[32mReel Factory is ready in %s\033[0m\nOpen a new terminal, cd %s, run claude or codex and ask in plain words.\n' "$DIR" "$DIR"
