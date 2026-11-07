# Reel Factory: full setup on a clean Windows 10/11 computer (PowerShell).
#   irm https://raw.githubusercontent.com/Shahen777/reel-factory/main/scripts/bootstrap.ps1 | iex
$ErrorActionPreference = "Stop"
$Repo = "https://github.com/Shahen777/reel-factory.git"
$Dir = if ($env:REEL_DIR) { $env:REEL_DIR } else { Join-Path $HOME "reel-factory" }
function Say($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Has($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

if (-not (Has winget)) { Write-Host "ACTION NEEDED: install 'App Installer' from the Microsoft Store (gives winget), then run again." -ForegroundColor Yellow; exit 2 }
$pkgs = [ordered]@{ git = "Git.Git"; ffmpeg = "Gyan.FFmpeg"; python = "Python.Python.3.12"; node = "OpenJS.NodeJS.LTS"; "yt-dlp" = "yt-dlp.yt-dlp" }
foreach ($k in $pkgs.Keys) {
  if (-not (Has $k)) { Say "winget install $($pkgs[$k])"; winget install --id $pkgs[$k] -e --silent --accept-source-agreements --accept-package-agreements }
}
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

if (Test-Path (Join-Path $Dir ".git")) { Say "Updating $Dir"; git -C $Dir pull --ff-only } else { Say "Cloning into $Dir"; git clone --depth 1 $Repo $Dir }
Set-Location $Dir

Say "Python environment"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python -m pip install -q --upgrade pip
.\.venv\Scripts\python -m pip install -q -e ".[all,dev]"
.\.venv\Scripts\python -m playwright install chromium
Say "Remotion packages"; Push-Location remotion; npm install --no-audit --no-fund --loglevel=error; Pop-Location

Say "Command and skills"
$bin = Join-Path $HOME ".local\bin"; New-Item -ItemType Directory -Force $bin | Out-Null
Set-Content -Path (Join-Path $bin "reel.cmd") -Value "@`"$Dir\.venv\Scripts\reel.exe`" %*"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$bin*") { [Environment]::SetEnvironmentVariable("Path", "$userPath;$bin", "User") }
foreach ($dest in @((Join-Path $HOME ".claude\skills"), (Join-Path $HOME ".agents\skills"))) {
  New-Item -ItemType Directory -Force $dest | Out-Null
  Get-ChildItem ".claude\skills" -Directory | ForEach-Object { Copy-Item $_.FullName $dest -Recurse -Force }
}

Say "Check"; .\.venv\Scripts\reel doctor
Say "Demo"; .\.venv\Scripts\python examples\make_demo.py | Out-Null; Write-Host "demo OK: $Dir\out\demo.mp4"
Write-Host "`nReel Factory is ready in $Dir. Open a new terminal, cd there, run claude or codex." -ForegroundColor Green
