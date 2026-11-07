---
name: reel-remotion
description: Beautiful animated text with Remotion (React) — springy kinetic titles, TikTok-style word-by-word captions with a highlight pill, premium title cards with mask reveal, stacking lists; over a video, a dark gradient or transparent for overlays (`reel remotion`). Use for «красивый текст», «анимированные титры», «Remotion», «ремоушен», «субтитры как в тиктоке», «титульная карточка», «текст по словам», «premium captions».
---

# reel-remotion — premium animated text

```bash
reel remotion list
reel remotion KineticTitle --set 'lines=["SUMMER","*DROP*","IS HERE"]' --music track.mp3 --out out/title.mp4
reel remotion Captions --video talk.mp4 --transcribe --lang ru --set style=pill --out out/talk_caps.mp4
reel remotion Captions --video talk.mp4 --words out/talk.mp4.words.json --set style=pop
reel remotion TextReveal --set kicker="New collection" --set title="AUTUMN 26" --set subtitle="From Friday"
reel remotion ListStack --set title="3 rules" --set 'items=["One","Two","Three"]' --transparent --out out/list.mov
reel remotion studio            # live preview/editor in the browser
```

Props common to all: `accent` (hex), `background` (css colour or `transparent`), `video`, `music`, `musicVolume`,
`durationInSeconds`, `font`. `*word*` marks an accent word in KineticTitle. Captions styles: `pill`, `pop`, `clean`.

## When to use which

- `reel remotion` — the most polished text: springs, gradients, per-letter motion, karaoke pill. Needs Node.js.
- `reel motion` — quick HTML/JS scenes, no Node. `reel subtitles` — plain burned captions without Node.
- `--transparent` renders ProRes 4444 with alpha. Use the .mov as an overlay, or render straight over `--video`.

## New compositions

Add a component in `remotion/src/` and register it in `remotion/src/Root.tsx` (and in `COMPS` in
`reelfactory/remotion.py`). Everything must be driven by `useCurrentFrame()`; use `spring()` / `interpolate()`,
no CSS transitions. Keep text in the 9:16 safe zone (top ≥ 220 px, bottom ≤ 1500 px). Check with `npx tsc --noEmit`
in `remotion/`, render, then `reel watch out/x.mp4 --no-audio --dense 0-2` and read the sheets.

## Licence

Remotion is free for individuals and companies of up to 3 people. Larger companies need a Remotion company licence
(remotion.dev/license). Say this to the user if they work for a bigger company.
