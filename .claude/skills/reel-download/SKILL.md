---
name: reel-download
description: Download videos or audio from YouTube, TikTok, Instagram, VK, X, Vimeo and other sites with yt-dlp (`reel download`), whole or only a time range. Use for «скачай видео», «скачай с ютуба», «скачай рилс/тикток», «вытащи звук», «download this video», «save this clip».
---

# reel-download

```bash
reel download "https://youtube.com/shorts/ID"
reel download URL --section 0:12-0:27        # only that part
reel download URL --audio                     # mp3
reel download --list urls.txt --out media/refs
```

Files go to `media/downloads/` by default. Then `reel watch <file>` to look at it.

## Rules

- Download only what the user has the right to use: their own videos, licensed clips, or references for
  analysis. Do not re-upload someone else's video as the user's own; use references to learn the format.
- If a site answers with a sign-in wall, "confirm you're not a bot" or a CAPTCHA, stop. Tell the user to save the
  file in their browser and give you the path. Do not try other clients, cookies or tricks to get around it.
- Private or paid content is off limits unless it belongs to the user.
