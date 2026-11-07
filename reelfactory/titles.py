"""Render titles and captions to transparent full-frame PNGs with PIL.

ffmpeg builds often ship without drawtext, so text is drawn here and overlaid.
Safe zones for 9:16 social video (1080x1920): text top >= ~220 px, bottom <= ~1500 px, width <= ~860 px.
"""
import hashlib
import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .ffutil import font_path

SAFE_TOP = 0.115
SAFE_BOTTOM = 0.78


def _hex(c, alpha=255):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)


def _line_width(d, text, font, tracking):
    if not text:
        return 0
    return sum(d.textlength(ch, font=font) for ch in text) + tracking * (len(text) - 1)


def wrap(text, font, max_w, tracking=0):
    """Greedy word wrap; explicit newlines are kept."""
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            cand = (line + " " + word).strip()
            if line and _line_width(d, cand, font, tracking) > max_w:
                out.append(line)
                line = word
            else:
                line = cand
        out.append(line)
    return out


def text_png(spec, W, H, outdir):
    """Draw one title spec to a WxH RGBA PNG and return its path.

    spec keys: text, size, y (0..1 centre of the block), color, stroke, stroke_w, font,
    tracking, shadow (bool), scrim (bool: dark band behind the text), sub, sub_size, sub_font,
    sub_color, bar (accent bar), bar_color, max_width (fraction of W).
    """
    os.makedirs(outdir, exist_ok=True)
    size = int(spec.get("size", 150))
    font = ImageFont.truetype(font_path(spec.get("font", "display")), size)
    tracking = int(spec.get("tracking", 0))
    color = _hex(spec.get("color", "#ffffff"))
    stroke = spec.get("stroke")
    sw = int(spec.get("stroke_w", max(2, size // 28)))
    max_w = W * float(spec.get("max_width", 0.80))
    lines = wrap(str(spec.get("text", "")), font, max_w, tracking)
    line_h = int(size * 1.08)

    sub = spec.get("sub")
    sfont = None
    s_h = 0
    if sub:
        ssize = int(spec.get("sub_size", max(28, size // 3)))
        sfont = ImageFont.truetype(font_path(spec.get("sub_font", "sans")), ssize)
        s_h = int(ssize * 1.3) + int(spec.get("sub_gap", 12))

    block_h = line_h * len(lines) + s_h
    yc = float(spec.get("y", 0.45)) * H
    y0 = yc - block_h / 2
    # keep inside the social safe zone
    y0 = max(SAFE_TOP * H, min(y0, SAFE_BOTTOM * H - block_h))

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if spec.get("scrim"):
        pad = int(size * 0.35)
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bd.rectangle([0, y0 - pad, W, y0 + block_h + pad], fill=(0, 0, 0, int(spec.get("scrim_alpha", 150))))
        img = Image.alpha_composite(img, band.filter(ImageFilter.GaussianBlur(6)))
        d = ImageDraw.Draw(img)

    if spec.get("shadow", True):
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for i, ln in enumerate(lines):
            x = (W - _line_width(sd, ln, font, tracking)) / 2
            y = y0 + i * line_h
            for ch in ln:
                sd.text((x + 5, y + 9), ch, font=font, fill=(0, 0, 0, 170))
                x += sd.textlength(ch, font=font) + tracking
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(max(4, size // 12))))
        d = ImageDraw.Draw(img)

    for i, ln in enumerate(lines):
        x = (W - _line_width(d, ln, font, tracking)) / 2
        y = y0 + i * line_h
        for ch in ln:
            kw = {"stroke_width": sw, "stroke_fill": _hex(stroke)} if stroke else {}
            d.text((x, y), ch, font=font, fill=color, **kw)
            x += d.textlength(ch, font=font) + tracking

    if sub:
        st = int(spec.get("sub_tracking", 4))
        sx = (W - _line_width(d, sub, sfont, st)) / 2
        sy = y0 + line_h * len(lines) + int(spec.get("sub_gap", 12))
        for ch in sub:
            d.text((sx, sy), ch, font=sfont, fill=_hex(spec.get("sub_color", "#ffffff")))
            sx += d.textlength(ch, font=sfont) + st

    if spec.get("bar"):
        bw, bh = int(spec.get("bar_w", 160)), int(spec.get("bar_h", 10))
        by = y0 - bh - int(size * 0.25)
        d.rectangle([(W - bw) / 2, by, (W + bw) / 2, by + bh], fill=_hex(spec.get("bar_color", "#e0242b")))

    key = hashlib.md5(json.dumps([spec, W, H], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]
    path = os.path.join(outdir, f"title_{key}.png")
    img.save(path)
    return path
