---
name: reel-ai-video
description: Generate AI images and AI video shots through kie.ai (Nano Banana, Veo 3.1) with the user's own key, always showing the price first (`reel kie`). Use for «сгенерируй картинку/видео», «AI-кадр», «оживи фото», «image to video», «Veo», «nano banana», «сколько стоит генерация».
---

# reel-ai-video — kie.ai with a price gate

Needs `KIE_API_KEY` (environment or `.env`).

```bash
reel kie balance
reel kie price veo                              # live price list search
reel kie image "prompt" --ref hero.jpg          # prints the price and stops
reel kie image "prompt" --ref hero.jpg --yes    # pays and generates
reel kie video "prompt" --image first_frame.png --model veo3_lite --yes
```

## Workflow

1. Write the shot list first. For each shot: still (image model) then motion (video model).
2. **Show the user the total price in credits and dollars and wait for a clear yes** before any `--yes` run.
   Never start a paid batch on your own.
3. One anchor still per character or product, reused as the first frame of every shot of that subject: this keeps
   faces and products consistent.
4. Prefer standing, turning, close and medium shots. Long full-body walks usually look fake.
5. Review each result with `reel watch` before using it. Then edit the shots with `reel montage`.

## Hard limits

- Original characters and products only. No deepfakes, face swaps or lipsync of real identifiable people,
  no fake "leaked" footage, no election campaigning.
- If a generation is blocked by a safety filter, change the idea. Do not reword prompts to sneak past the filter.
