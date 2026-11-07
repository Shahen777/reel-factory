---
name: reel-voice
description: Make a voice-over with ElevenLabs using the user's own API key (`reel voice`) and mix it into a montage with music ducking. Use for «озвучка», «сделай голос», «voice-over», «наложи голос на видео», «ElevenLabs».
---

# reel-voice — ElevenLabs voice-over

Needs `ELEVENLABS_API_KEY` in the environment or in `.env` (never commit `.env`).

```bash
reel voice list
reel voice say "Text of the voice-over" --voice VOICE_ID --lang ru --out media/p/vo.mp3
reel voice say --file media/p/script.txt --voice VOICE_ID --out media/p/vo.mp3
```

Then in the EDL: `"audio": {"voice": "vo.mp3", "voice_at": 1.5, "duck_db": -12}` and render with `reel montage`.

## Rules

- Polish the text before paying for audio: short sentences, numbers written as words, stress marks if needed.
- Audition one short line first, then render the whole script. Say how many characters will be billed.
- Use voices the user owns, designed voices or library voices. Never clone a real person's voice
  without their documented consent, and never imitate politicians or celebrities.
- For sync with picture, transcribe the voice (`reel watch vo.mp3` or `reel subtitles --srt-only`) and cut to
  the real word times instead of guessing.
