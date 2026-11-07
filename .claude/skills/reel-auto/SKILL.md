---
name: reel-auto
description: One-command automatic beat montage from a folder of clips/photos and a music track (`reel auto`). Use for a quick first cut, when the user just drops files and says «сделай быстро ролик», «автомонтаж», «собери из этих видео», «quick edit», or when there are many clips and you need a draft EDL to refine.
---

# reel-auto — automatic first cut

```bash
reel auto media/myproject --music media/myproject/track.mp3 --duration 30 --style punchy --title "TITLE" --out out/auto.mp4
```

- `--style`: `punchy` (fast cuts, flashes, shake), `smooth` (long shots), `cinematic` (slow-mo on top moments).
- `--hook clip.mp4` forces the first shot. `--preview` renders fast. `--edl-only` only writes the EDL.
- The tool scores motion, sharpness and exposure every half second and picks the best non-overlapping moments,
  rotating across clips. It writes `<out>.edl.json` next to the video.

## Make it good

1. Render `--preview`, then review with `reel watch out/auto.mp4 --no-audio` and read every sheet.
2. Fix weak moments by editing `out/auto.mp4.edl.json` (change `in`, `beats`, `fit`, `cx/cy`, titles) and
   re-render with `reel montage out/auto.mp4.edl.json`. See the `reel-montage` skill for EDL rules.
3. The automatic pick does not understand meaning (who scores, who smiles). Check the hook and the finale by eye.
