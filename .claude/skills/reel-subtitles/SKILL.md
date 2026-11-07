---
name: reel-subtitles
description: Add speech subtitles to a video with local Whisper transcription (`reel subtitles`), as bold, clean or karaoke phrase captions, plus SRT export. Use when the user asks «добавь субтитры», «сделай титры по речи», «captions», «karaoke subtitles», «srt», or a talking video needs readable captions for silent viewing.
---

# reel-subtitles

```bash
reel subtitles talk.mp4 --lang ru --style karaoke --words 3 --out out/talk_subs.mp4
reel subtitles talk.mp4 --srt-only              # only SRT + words.json, nothing burned
reel subtitles talk.mp4 --srt fixed.srt         # burn an SRT you corrected by hand
```

Needs `pip install faster-whisper` (free, runs on CPU; first run downloads the model).

## Checklist

1. Run `--srt-only` first and read the SRT. Fix names, brand words and numbers by hand, then burn with `--srt`.
   Whisper often mishears names and rare words; never publish unread subtitles.
2. Keep captions below faces and above the platform UI: default `--y 0.70`. Move with `--y` if a face is low.
3. One text layer at a time: if a big title is on screen, the caption should not duplicate its words.
4. Check timing with `reel watch out/talk_subs.mp4 --dense 0-5` and read the dense sheet.
