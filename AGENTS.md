# Reel Factory — instructions for AI agents (Codex, Claude Code, others)

This repo is a toolkit for making short vertical videos (Reels, TikTok, Shorts) with ffmpeg.
The user talks to you in plain words; you run the `reel` commands, look at the results and report.

## Setup check

Run `reel doctor` (or `python3 -m reelfactory doctor`) first. If `reel` is not on PATH, use `python3 -m reelfactory`.
If something is missing, tell the user the exact install command from README.

## Skills

Skills live in `.claude/skills/` (Claude Code) and the same files are linked as `.agents/skills/` (Codex).
Read the matching `SKILL.md` before the task:

| Task | Skill |
|---|---|
| dynamic edit to music from clips/photos | `reel-montage` |
| quick automatic first cut | `reel-auto` |
| speech subtitles, SRT | `reel-subtitles` |
| black bars, 9:16, export for platforms | `reel-reframe` |
| look at / review a video | `reel-watch` |
| ElevenLabs voice-over | `reel-voice` |
| AI images and video via kie.ai | `reel-ai-video` |
| hook, script, caption, hashtags | `reel-hooks` |
| motion design, kinetic text, animated graphics | `reel-motion` |
| download from YouTube, TikTok, Instagram... | `reel-download` |

## Commands

```
reel montage EDL.json [--preview]          beat-locked edit (docs/EDL.md)
reel auto FOLDER --music TRACK [...]       automatic edit, writes an editable EDL
reel subtitles VIDEO [--lang ru]           Whisper subtitles, SRT
reel reframe VIDEO [--aspect 9:16]         remove bars, reframe
reel export VIDEO --all                    Reels / TikTok / Shorts files, -14 LUFS
reel watch VIDEO [--dense 3-6]             contact sheets + transcript for you to read
reel motion SCENE [--set k=v] [--music]    HTML/JS animation -> MP4 / alpha MOV
reel download URL [--section a-b]          YouTube, TikTok, Instagram... via yt-dlp
reel beats TRACK                           tempo and beat times
reel voice list | say                      ElevenLabs (ELEVENLABS_API_KEY)
reel kie balance | price | image | video   kie.ai (KIE_API_KEY), price first, --yes to pay
```

## Working rules

1. **Copy user files into `media/<project>/` first.** Attachments and Downloads can disappear.
2. **Look before you edit and before you deliver.** You cannot see video directly: run `reel watch`, then read every
   sheet image. Check the first 3 s, every title and the ending with `--dense`. Never describe frames you did not see.
3. **Preview first** (`--preview`), final render after.
4. **Text:** one layer at a time, at least 1 s, never over faces, inside the safe zone (top ≥ 220 px, bottom ≤ 1500 px,
   width ≤ ~860 px on 1080×1920).
5. **Paid APIs (kie.ai, ElevenLabs):** show the price and wait for the user's clear yes. Never pass `--yes` on your own.
6. **Secrets:** keys go in `.env` (git-ignored). Never print, commit or send keys.
7. **Content limits:** original or licensed material only. No deepfakes, face swaps, voice clones or lipsync of real
   identifiable people without consent, no fake "leaked" footage, no election campaigning, no copyrighted music the user
   has no rights to. If a safety filter blocks a generation, change the idea; do not try to get around the filter.
8. **Do not bypass sign-in walls, bot checks or CAPTCHAs** when downloading; ask the user for the file.
9. Report at the end: what was made (path, duration, format), what you checked, what you did not check.

## Code layout

```
reelfactory/   python package: cli.py, montage.py, auto.py, subtitles.py, reframe.py, export.py, watch.py,
               motion.py, download.py, beats.py, titles.py, voice.py, kie.py, ffutil.py,
               assets/fonts (OFL fonts), assets/motion (HTML motion templates)
docs/          EDL.md (montage format), HOOKS.md (hooks and endings)
examples/      demo EDL and a script that renders it from generated test media
tests/         pytest, no network
```

Tests: `python3 -m pytest -q`. Keep Python 3.9 compatible, no new heavy dependencies.
