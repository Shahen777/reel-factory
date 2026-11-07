---
name: reel-montage
description: Edit clips and photos into a dynamic beat-synced vertical video (Reels, TikTok, Shorts) by writing an EDL JSON and rendering it with `reel montage`. Use when the user asks for a montage, a dynamic edit to music, a highlight reel, a sports/fashion/travel/product edit, «смонтируй», «сделай красивый динамичный монтаж», «под музыку», «нарезка», or wants to change cuts, titles, slow motion or zooms in an existing edit.
---

# reel-montage — beat-synced edit from an EDL

The renderer is `reel montage EDL.json` (or `python3 -m reelfactory montage`). Every cut lands on a real beat
of the track. Read `docs/EDL.md` for every key.

## Workflow

1. **Copy inputs into the project first** (`media/<project>/`). Downloads and chat attachments can vanish.
2. **Look at the material.** For each clip run `reel watch <clip> --no-audio` and read the sheets. Write a short
   catalogue: clip, what happens, best moments with timecodes, orientation. Never guess what is in a clip.
3. **Beats.** `reel beats track.mp3` prints tempo and beat times. Find where the drop starts (use `music_offset`).
4. **Structure** (example for 30–50 s): hook 1–2 s (the strongest moment, flash) → build-up with 2-beat cuts →
   peak with 1-beat or half-beat cuts on the drop → breath (4 beats, slow-mo) → finale with title and fade.
5. **Write the EDL** in `media/<project>/edl_A.json`. Lengths are in beats; `in` is the source second.
   - vertical sources: `"fit": "full"`; horizontal 16:9: `"fit": "4x5"` (sharp window over blurred fill).
   - `push` 0.08–0.15 for slow zoom-in, `flash` 0.06–0.1 on impacts, `shake` 4–8 on hits, `speed` 0.5 slow-mo.
   - titles: one text layer at a time, at least 1 s on screen, never over a face, inside the safe zone
     (y 0.25–0.75), `anim: "pop"` for a hook word, `scrim: true` when text sits on a busy picture.
6. **Preview fast:** `reel montage edl_A.json --preview` (skips slow-mo interpolation). Check with
   `reel watch out/edl_A.mp4 --no-audio --dense 0-3` and read the sheets before showing anyone.
7. Final render without `--preview`, then `reel export out/edl_A.mp4 --all` for platform files.

## Rules

- Offer two variants (A/B) with different music or pacing when the brief is open.
- Music must be licensed, royalty-free or supplied by the user. Never pull copyrighted tracks from YouTube.
- Do not repeat the same moment twice; vary shot size (wide, medium, close) between cuts.
- Report: duration, tempo, structure by seconds, output path. Say plainly what you did not check.
