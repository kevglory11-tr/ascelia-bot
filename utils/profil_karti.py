"""
utils/profil_karti.py — Discord level card generator.
Internal render: 1600×500 → LANCZOS → 800×250 final output.

Font: assets/fonts/levelfont.otf (bundled — no system font dependency).
Avatar + background downloads run in parallel via asyncio.gather().
"""

import asyncio
import io
import os

import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Dimensions ────────────────────────────────────────────────────────────────
OUT_W, OUT_H = 800, 250
W,     H     = OUT_W * 2, OUT_H * 2      # 1600 × 500 render canvas

# ── Layout (render-px) ────────────────────────────────────────────────────────
PAD     = 50
AV_SIZE = 300
AV_X    = PAD
AV_Y    = (H - AV_SIZE) // 2             # 100 — vertically centred
AV_CX   = AV_X + AV_SIZE // 2            # 200
AV_CY   = AV_Y + AV_SIZE // 2            # 250
TEXT_X  = AV_X + AV_SIZE + 60            # 410 — right panel start
BAR_X   = TEXT_X
BAR_Y   = 415
BAR_W   = W - TEXT_X - PAD               # 1140
BAR_H   = 34

# ── Colours ───────────────────────────────────────────────────────────────────
WHITE = (255, 255, 255, 255)
MUTED = (158, 158, 192, 215)
TRACK = (35,  35,  50,  255)

# ── Font ─────────────────────────────────────────────────────────────────────
_FONT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "levelfont.otf")
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


# ── Colour helpers ────────────────────────────────────────────────────────────

def _parse_hex(h: str) -> tuple[int, int, int]:
    try:
        h = h.strip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return (30, 30, 47)


def _accent(hex_color: str) -> tuple[int, int, int]:
    """Boost very dark palette colors to a visible accent."""
    r, g, b = _parse_hex(hex_color)
    if max(r, g, b) < 90:
        f = 200 / max(max(r, g, b), 1)
        r, g, b = min(int(r * f), 255), min(int(g * f), 255), min(int(b * f), 255)
    return r, g, b


# ── Image helpers ─────────────────────────────────────────────────────────────

def _circle_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


def _composite(base: Image.Image, draw_fn) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Draw on a transparent layer and alpha-composite it onto base. Prevents white artifacts."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    result = Image.alpha_composite(base, layer)
    return result, ImageDraw.Draw(result)


# ── Async I/O ─────────────────────────────────────────────────────────────────

async def _fetch_image(url: str) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return Image.open(io.BytesIO(await r.read())).convert("RGBA")
    except Exception:
        pass
    return None


async def load_avatar(url: str, size: int) -> Image.Image:
    img = await _fetch_image(url)

    if img is None:
        placeholder = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(placeholder).ellipse([0, 0, size - 1, size - 1], fill=(80, 80, 110, 255))
        return placeholder

    w, h = img.size
    s    = min(w, h)
    img  = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    img  = img.resize((size, size), Image.Resampling.LANCZOS)
    out  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), _circle_mask(size))
    return out


async def process_background(source: str, width: int, height: int) -> Image.Image:
    """source: '#rrggbb' hex OR image URL. Returns width×height RGBA with dark overlay."""
    if source.startswith(("http://", "https://")):
        img = await _fetch_image(source)
        if img is not None:
            iw, ih = img.size
            scale  = max(width / iw, height / ih)
            nw, nh = int(iw * scale) + 1, int(ih * scale) + 1
            img    = img.resize((nw, nh), Image.Resampling.LANCZOS)
            left, top = (nw - width) // 2, (nh - height) // 2
            img    = img.crop((left, top, left + width, top + height))
            img    = img.filter(ImageFilter.GaussianBlur(2))
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 155))
            return Image.alpha_composite(img, overlay)

    r, g, b = _parse_hex(source)
    dark = (max(r // 9, 6), max(g // 9, 6), max(b // 8 + 3, 10))
    return Image.new("RGBA", (width, height), (*dark, 255))


# ── Card components ───────────────────────────────────────────────────────────

def _draw_avatar(canvas: Image.Image, av_img: Image.Image,
                 acc: tuple) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    def shadow(d):
        sr = AV_SIZE // 2 + 14
        d.ellipse([AV_CX - sr, AV_CY - sr, AV_CX + sr, AV_CY + sr], fill=(0, 0, 0, 88))
    canvas, draw = _composite(canvas, shadow)

    ring_r = AV_SIZE // 2 + 5
    draw.ellipse([AV_CX - ring_r, AV_CY - ring_r, AV_CX + ring_r, AV_CY + ring_r],
                 outline=(*acc, 255), width=4)

    canvas.paste(av_img, (AV_X, AV_Y), av_img)
    return canvas, ImageDraw.Draw(canvas)


def _draw_accent_bars(canvas: Image.Image, acc: tuple) -> Image.Image:
    def bars(d):
        d.rectangle([(0, 0), (8, H)],      fill=(*acc, 255))
        d.rectangle([(0, H - 8), (W, H)],  fill=(*acc, 228))
    canvas, _ = _composite(canvas, bars)
    return canvas


def _draw_rozet_pill(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                     text: str, y: int, font: ImageFont.FreeTypeFont,
                     acc: tuple) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    text = text[:24]
    bbox = draw.textbbox((0, 0), text, font=font)
    pw, ph = bbox[2] - bbox[0] + 30, 44

    pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle(
        [0, 0, pw - 1, ph - 1], radius=ph // 2,
        fill=(*acc, 38), outline=(*acc, 145), width=1,
    )
    canvas.paste(pill, (TEXT_X, y), pill)
    draw = ImageDraw.Draw(canvas)
    draw.text((TEXT_X + 15, y + 8), text, font=font, fill=(*acc, 232))
    return canvas, draw, y + ph + 8


def draw_text_elements(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                       username: str, level: int,
                       bio: str | None, aktif_rozet: str | None,
                       acc: tuple) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    """Returns (canvas, draw, next_y) — first free Y below all text elements."""
    fn_name  = _font(90)
    fn_level = _font(56)
    fn_sub   = _font(38)

    y = 50
    draw.text((TEXT_X, y), username[:20], font=fn_name,  fill=WHITE)
    y += 90 + 10

    draw.text((TEXT_X, y), f"Seviye {level}", font=fn_level, fill=(*acc, 255))
    y += 56 + 12

    if bio:
        draw.text((TEXT_X, y), bio[:50], font=fn_sub, fill=MUTED)
        y += 38 + 8

    if aktif_rozet:
        canvas, draw, y = _draw_rozet_pill(canvas, draw, aktif_rozet, y, fn_sub, acc)

    return canvas, draw, y


def _draw_stats(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                bakiye: int, siralama: int,
                stat_y: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    fn_label = _font(32)
    fn_value = _font(48)
    col_w    = 280

    for i, (label, value) in enumerate([("COINS", f"{bakiye:,}"), ("SIRALAMA", f"#{siralama:,}")]):
        x = TEXT_X + i * col_w
        draw.text((x, stat_y),      label, font=fn_label, fill=MUTED)
        draw.text((x, stat_y + 34), value, font=fn_value, fill=WHITE)

    def divider(d):
        dx = TEXT_X + col_w - 18
        d.rectangle([(dx, stat_y), (dx + 2, stat_y + 90)], fill=(255, 255, 255, 18))
    return _composite(canvas, divider)


def draw_xp_bar(canvas: Image.Image,
                x: int, y: int, w: int, h: int,
                current: int, required: int,
                accent: tuple) -> Image.Image:
    radius   = h // 2
    fill_w   = int(w * min(current / max(required, 1), 1.0))

    def track(d):
        d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=TRACK)
    canvas, _ = _composite(canvas, track)

    if fill_w > radius:
        def fill(d):
            d.rounded_rectangle([x, y, x + fill_w, y + h], radius=radius, fill=(*accent, 255))
        canvas, _ = _composite(canvas, fill)

    return canvas


def _draw_xp_text(draw: ImageDraw.ImageDraw, current: int, required: int) -> None:
    fn    = _font(36)
    pct   = int(min(current / max(required, 1), 1.0) * 100)
    left  = f"{current:,} / {required:,} XP"
    right = f"%{pct}"
    text_y = BAR_Y + BAR_H + 6

    draw.text((BAR_X, text_y), left, font=fn, fill=MUTED)
    bbox = draw.textbbox((0, 0), right, font=fn)
    draw.text((BAR_X + BAR_W - (bbox[2] - bbox[0]), text_y), right, font=fn, fill=WHITE)


def _draw_separator(canvas: Image.Image) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    def line(d):
        d.rectangle([(TEXT_X, BAR_Y - 18), (W - PAD, BAR_Y - 16)], fill=(255, 255, 255, 18))
    return _composite(canvas, line)


def _supersample(canvas: Image.Image) -> Image.Image:
    """Composite over dark bg → LANCZOS resize → RGB. Eliminates transparent-to-white artifacts."""
    dark  = Image.new("RGBA", (W, H), (8, 8, 14, 255))
    final = Image.alpha_composite(dark, canvas)
    return final.resize((OUT_W, OUT_H), Image.Resampling.LANCZOS).convert("RGB")


# ── Public API ────────────────────────────────────────────────────────────────

async def profil_karti_olustur(
    kullanici_adi: str,
    avatar_url:    str,
    level:         int,
    exp:           int,
    gereken_exp:   int,
    bakiye:        int,
    siralama:      int,
    aktif_rozet:   str | None,
    arka_plan_url: str | None,
    renk_hex:      str = "2b2d31",
    bio:           str | None = None,
) -> io.BytesIO:
    acc       = _accent(renk_hex)
    bg_source = arka_plan_url or f"#{renk_hex}"

    # Avatar ve background aynı anda indirilir
    canvas, av_img = await asyncio.gather(
        process_background(bg_source, W, H),
        load_avatar(avatar_url, AV_SIZE),
    )

    canvas, draw = _draw_avatar(canvas, av_img, acc)
    canvas       = _draw_accent_bars(canvas, acc)
    canvas, draw, stat_y = draw_text_elements(canvas, draw, kullanici_adi, level, bio, aktif_rozet, acc)
    canvas, draw = _draw_stats(canvas, draw, bakiye, siralama, stat_y)
    canvas, draw = _draw_separator(canvas)
    canvas       = draw_xp_bar(canvas, BAR_X, BAR_Y, BAR_W, BAR_H, exp, gereken_exp, acc)
    draw         = ImageDraw.Draw(canvas)
    _draw_xp_text(draw, exp, gereken_exp)

    buf = io.BytesIO()
    _supersample(canvas).save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
