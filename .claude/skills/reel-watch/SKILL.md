---
name: reel-watch
description: Let the agent actually see and hear a video — timestamped contact sheets, dense frames for a range, and a word-level transcript (`reel watch`). Use when asked «посмотри видео», «что в ролике», «проверь монтаж/титры», «разбери ролик», «найди момент где», to review your own render before delivering it, or when a .mp4/.mov path is given.
---

# reel-watch — see the video before talking about it

```bash
reel watch clip.mp4                       # sheets + transcript in watch_clip/
reel watch clip.mp4 --dense 3-6.5         # 5 frames per second for a range (titles, transitions, lips)
reel watch clip.mp4 --no-audio --fps 2
reel watch https://example.com/video.mp4  # public URLs via yt-dlp when it works
```

1. Open `REPORT.md`, then read **every** `sheet_NN.jpg` in order (each frame has a timecode), then `transcript.txt`.
2. Answer only from what you saw and heard, with timecodes. Do not invent frames you did not look at.
3. **Self-QA before delivering any render:** dense frames on the first 3 s, every title and the last 3 s.
   Look for flashes of black, cut-off text, text on faces, frozen frames, wrong aspect, jumps in colour.
4. If a site asks to sign in or confirm you are not a bot, stop and ask the user for the file.
   Do not try to get around such checks.
