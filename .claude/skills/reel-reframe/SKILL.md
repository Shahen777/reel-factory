---
name: reel-reframe
description: Remove black bars, convert horizontal video to vertical 9:16 (crop or blurred fill), 4:5 or 1:1, and export platform-ready files for Reels, TikTok, Shorts with loudness normalisation. Use for «убери чёрные полосы», «сделай вертикальным», «переведи в 9:16», «сожми для инсты», «экспорт под Reels/TikTok/Shorts», «normalize audio».
---

# reel-reframe and reel-export

```bash
reel reframe in.mp4 --aspect 9:16 --mode auto      # bars detected and removed, then crop or blur-fill
reel reframe in.mp4 --mode crop --cx 0.4           # fill by cropping, centre a bit left
reel reframe in.mp4 --mode blur                    # keep the whole picture over a blurred copy
reel reframe in.mp4 --mode bars                    # only cut the black bars
reel export final.mp4 --all                        # reels, tiktok, shorts files at -14 LUFS
reel export final.mp4 --preset telegram            # light file for messengers
```

- `auto` crops when the aspect is close to the target and blur-fills when it is far (16:9 into 9:16).
- After a crop, check that heads and hands are not cut: `reel watch out.mp4 --no-audio`.
- Presets: reels, tiktok, shorts (1080x1920), feed45 (1080x1350), square, youtube (1920x1080), telegram (720x1280).
