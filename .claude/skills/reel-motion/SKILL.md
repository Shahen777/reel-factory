---
name: reel-motion
description: Create motion design and animated graphics as code — kinetic typography, title cards, stat counters, lower thirds, animated lists, logo reveals, intros — written by Claude or Codex as an HTML/JS page and rendered frame by frame to MP4 or transparent MOV (`reel motion`). Use for «моушн дизайн», «анимированный текст», «кинетическая типографика», «заставка», «плашка с именем», «анимация цифр», «инфографика в видео», «motion graphics», «intro», «lower third».
---

# reel-motion — motion design from code

The agent writes the animation as a web page; `reel motion` renders it deterministically (each frame is computed
from `t`, so there are no dropped frames and no real-time playback).

```bash
reel motion list
reel motion kinetic --set 'lines=["ONE IDEA","*BIG*","ON THE BEAT"]' --music track.mp3 --out out/title.mp4
reel motion stats --set value=250 --set suffix=K --set label="views" --out out/stats.mp4
reel motion lower_third --set name="Anna" --set role="Designer" --transparent --out out/lt.mov
reel motion media/p/my_scene.html --duration 8 --music media/p/track.mp3 --out out/scene.mp4
```

`*word*` in kinetic lines is drawn in the accent colour. `--transparent` gives ProRes 4444 with alpha for overlays.

## Writing a new scene

Copy a template from `reelfactory/assets/motion/` into `media/<project>/scene.html` and change it.
Contract:

```js
window.MOTION = {duration: 6, fps: 30, width: 1080, height: 1920};
window.renderFrame = (t, frame) => { /* set every element from t only */ };
```

- Everything must be a pure function of `t`. No `setTimeout`, CSS transitions/animations, `Date.now()` or random
  without a seed; they break frame-by-frame rendering.
- Available: `window.DATA` (from `--data file.json` / `--set k=v`), `window.BEATS` (beat seconds of `--music`, for
  hits on the beat), fonts `Display` and `Sans` (bundled, Latin + Cyrillic). Other fonts: `@font-face` with a file path.
- Easing: write small helpers (easeOutBack, easeOutCubic, clamp). Stagger words by 60–120 ms.
- Premium look: dark background, one accent colour, big type, generous empty space, soft glow or blur,
  motion with overshoot and settle. Keep text inside the 9:16 safe zone (top ≥ 220 px, bottom ≤ 1500 px).
- No external network assets (CDN fonts or images) — rendering must work offline. Inline SVG is fine.

## Review

Render, then `reel watch out/scene.mp4 --no-audio --dense 0-2` and read the sheets: check easing, overlaps,
cut-off text, the last frame. Fix and re-render. Use the result as a segment in a montage EDL
(`"type": "video", "src": "out/scene.mp4"`).

Needs `pip install playwright` and `playwright install chromium` (or an installed Google Chrome).
