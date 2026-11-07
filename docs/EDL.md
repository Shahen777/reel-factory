# EDL reference (`reel montage`)

An EDL is a JSON file that describes the whole edit. Segment lengths are in **beats** of the music, so every
cut lands on the rhythm. Paths are relative to the EDL file.

```json
{
  "out": "out/my_reel.mp4",
  "music": "track.mp3",
  "music_offset": 12.0,
  "start_beat": 0,
  "fps": 30, "w": 1080, "h": 1920,
  "look": {"contrast": 1.06, "saturation": 1.12, "brightness": 0.0, "sharpen": 0.5, "grain": 4, "vignette": true},
  "segments": [
    {"type": "video", "src": "clips/a.mp4", "in": 3.2, "beats": 2, "fit": "full", "push": 0.1, "flash": 0.08},
    {"type": "video", "src": "clips/wide.mp4", "in": 10, "beats": 4, "fit": "4x5", "speed": 0.5},
    {"type": "photo", "src": "photos/p1.jpg", "beats": 2, "cy": 0.42, "push": 0.14},
    {"type": "black", "beats": 1}
  ],
  "titles": [
    {"text": "CHAMPION", "at_beat": 0, "beats": 4, "y": 0.32, "size": 170, "anim": "pop", "stroke": "#000000",
     "sub": "Yerevan 2026", "sub_size": 56}
  ],
  "audio": {"fade_in": 0.2, "fade_out": 1.5, "gain_db": -1,
            "voice": "vo.mp3", "voice_at": 1.0, "voice_gain_db": 0, "duck_db": -12}
}
```

## Top level

| key | default | meaning |
|---|---|---|
| `out` | `out/montage.mp4` | output file |
| `music` | none | track; without it a silent `bpm` grid is used |
| `bpm` | 120 | grid tempo when there is no music |
| `music_offset` | 0 | second of the track where the video starts (skip the intro, start on the drop) |
| `beat_source` | music | detect beats on another file (e.g. a clean stem) |
| `start_beat` | 0 | beat index where the first cut lands |
| `fps`, `w`, `h` | 30, 1080, 1920 | output format (use 1080x1350 for 4:5, 1920x1080 for 16:9) |
| `look` | none | final colour pass: contrast, saturation, brightness, sharpen, grain, vignette |

## Segment

| key | default | meaning |
|---|---|---|
| `type` | video | `video`, `photo` or `black` (`color` sets the colour of a black segment) |
| `src` | | file path |
| `in` | 0 | start second inside the source (video) |
| `beats` | 1 | length in beats, fractions allowed (0.5 = half beat) |
| `fit` | full | `full` fills the frame by cropping; `4x5` puts a sharp 4:5 window over a blurred copy (good for 16:9 sources) |
| `cx`, `cy` | 0.5 | crop centre as a fraction of the source |
| `zoom` | 1.0 | static zoom |
| `push` | 0 (photo 0.12) | zoom-in over the segment, 0.08–0.15 looks natural |
| `speed` | 1.0 | below 1 = smooth slow motion with frame interpolation, above 1 = fast |
| `rotate` | 0 | 1 = 90° clockwise, 2 = counter-clockwise (for sideways phone clips) |
| `flash` | 0 | white flash at the start, seconds |
| `shake` | 0 | camera shake in pixels |
| `fade_in`, `fade_out` | 0 | fade from/to black, seconds |

## Title

| key | default | meaning |
|---|---|---|
| `text` | | text, `\n` for a new line, long lines wrap |
| `at_beat`, `beats` | 0, 2 | when it appears and how long it stays (beats from the first cut) |
| `y` | 0.45 | vertical centre (0 top, 1 bottom); kept inside the social safe zone |
| `size` | 150 | font size in px |
| `font` | display | `display` (bundled Russo One), `sans` (bundled PT Sans Bold), a system alias or a path to .ttf/.otf |
| `color`, `stroke`, `stroke_w` | white, none | colours as hex |
| `anim` | rise | `rise`, `pop` or `none` |
| `scrim` | false | dark band behind text, use it over busy pictures |
| `shadow` | true | soft drop shadow |
| `sub`, `sub_size`, `sub_font`, `sub_color` | | second smaller line |
| `bar`, `bar_color` | false | small accent bar above the title |
| `fade_in`, `fade_out` | 0.08, 0.12 | alpha fades, seconds |

Bundled fonts support Latin and Cyrillic. For Armenian, Georgian, Arabic and others pass a font path that covers the script
(for example Noto Sans Armenian).

## Audio

| key | default | meaning |
|---|---|---|
| `fade_in`, `fade_out` | 0.2, 1.5 | music fades |
| `gain_db` | 0 | music volume |
| `voice` | none | voice-over file |
| `voice_at` | 0 | when the voice starts, seconds |
| `voice_gain_db` | 0 | voice volume |
| `duck_db` | -12 | how strongly music ducks under the voice |

## Tips

- `reel montage edl.json --preview` renders fast without slow-motion interpolation.
- Temporary segments live in `out/.tmp_<name>/` and can be deleted.
- Text is drawn with Pillow, so ffmpeg builds without `drawtext` work too.
