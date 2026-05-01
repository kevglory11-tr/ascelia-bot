"""
utils/profil_karti.py — Discord level card generator.
card2 / card3 layout from DiscordLevelingCard, adapted for Ascelia.

card2: solid dark panel background
card3: custom image background + semi-transparent overlay

Assets: assets/fonts/levelfont.otf, assets/fonts/curveborder.png
"""

import asyncio
import io
import os

import aiohttp
from PIL import Image, ImageDraw, ImageFont

# ── Dimensions ────────────────────────────────────────────────────────────────
OUT_W, OUT_H = 1000, 333

# ── Layout (px) ───────────────────────────────────────────────────────────────
INNER_X, INNER_Y = 25, 25
INNER_W, INNER_H = 950, 283
AV_SIZE          = 260
AV_X, AV_Y       = 53, 36
TEXT_X           = 330    # left edge of text area
TEXT_R           = 950    # right edge of text area

# ── Assets ────────────────────────────────────────────────────────────────────
_ASSETS     = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
_FONT_PATH  = os.path.join(_ASSETS, "levelfont.otf")
_CURVE_MASK = os.path.join(_ASSETS, "curveborder.png")


# ── Font ─────────────────────────────────────────────────────────────────────

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
    r, g, b = _parse_hex(hex_color)
    if max(r, g, b) < 90:
        f = 200 / max(max(r, g, b), 1)
        r, g, b = min(int(r * f), 255), min(int(g * f), 255), min(int(b * f), 255)
    return r, g, b


def _bg_dark(hex_color: str) -> tuple[int, int, int]:
    """Derive a very dark solid color from the accent hex for card2-style background."""
    r, g, b = _parse_hex(hex_color)
    return (max(r // 9, 6), max(g // 9, 6), max(b // 8 + 3, 10))


# ── Async fetch ───────────────────────────────────────────────────────────────

async def _fetch_image(url: str) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return Image.open(io.BytesIO(await r.read())).convert("RGBA")
    except Exception:
        pass
    return None


# ── Image helpers ─────────────────────────────────────────────────────────────

async def load_avatar(url: str, size: int) -> Image.Image:
    """Download, center-crop to square, resize. Returns RGBA (no mask applied)."""
    img = await _fetch_image(url)
    if img is None:
        return Image.new("RGBA", (size, size), (80, 80, 110, 255))
    w, h = img.size
    s    = min(w, h)
    img  = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    return img.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


async def process_background(source: str, width: int, height: int) -> Image.Image:
    """Returns an RGB image at (width × height). Source is a URL or hex string."""
    if source.startswith(("http://", "https://")):
        img = await _fetch_image(source)
        if img is not None:
            iw, ih = img.size
            scale  = max(width / iw, height / ih)
            nw, nh = int(iw * scale) + 1, int(ih * scale) + 1
            img    = img.resize((nw, nh), Image.Resampling.LANCZOS)
            left, top = (nw - width) // 2, (nh - height) // 2
            return img.crop((left, top, left + width, top + height)).convert("RGB")
    return Image.new("RGB", (width, height), _bg_dark(source))


def _apply_inner_panel(bg: Image.Image, image_bg: bool) -> None:
    """Paste inner panel onto bg in-place."""
    if image_bg:
        # card3: semi-transparent dark overlay
        cut = Image.new("RGBA", (INNER_W, INNER_H), (0, 0, 0, 200))
        bg.paste(cut, (INNER_X, INNER_Y), cut)
    else:
        # card2: solid dark Discord panel
        bg.paste(Image.new("RGB", (INNER_W, INNER_H), (47, 49, 54)), (INNER_X, INNER_Y))


def _paste_avatar(bg: Image.Image, av_img: Image.Image) -> None:
    """Paste avatar at (AV_X, AV_Y) using curveborder.png as mask."""
    try:
        mask = Image.open(_CURVE_MASK).resize((AV_SIZE, AV_SIZE)).convert("L")
    except Exception:
        mask = Image.new("L", (AV_SIZE, AV_SIZE), 255)

    frame = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
    try:
        frame.paste(av_img, mask=av_img.split()[3])
    except Exception:
        frame.paste(av_img, (0, 0))
    bg.paste(frame, (AV_X, AV_Y), mask)


# ── Draw helpers ──────────────────────────────────────────────────────────────

def _right(draw: ImageDraw.ImageDraw, text: str, y: int,
           font: ImageFont.FreeTypeFont, fill=(255, 255, 255)) -> None:
    w = draw.textlength(text, font=font)
    draw.text((TEXT_R - w, y), text, font=font, fill=fill,
              stroke_width=1, stroke_fill=(0, 0, 0))


def _left(draw: ImageDraw.ImageDraw, text: str, y: int,
          font: ImageFont.FreeTypeFont, fill=(255, 255, 255)) -> None:
    draw.text((TEXT_X, y), text, font=font, fill=fill,
              stroke_width=1, stroke_fill=(0, 0, 0))


# ── XP bar ────────────────────────────────────────────────────────────────────

def draw_xp_bar(bg: Image.Image, x: int, y: int, w: int, h: int,
                current: int, required: int, accent: tuple) -> None:
    progress = min(current / max(required, 1), 1.0)
    fill_w   = max(int(w * progress), h)   # minimum = one radius

    bar = Image.new("RGBA", (w + 1, h + 1), (0, 0, 0, 0))
    d   = ImageDraw.Draw(bar, "RGBA")
    d.rounded_rectangle((0, 0, w, h), radius=h // 2, fill=(255, 255, 255, 50))
    if current > 0:
        d.rounded_rectangle((0, 0, fill_w, h), radius=h // 2, fill=(*accent, 255))
    bg.paste(bar, (x, y), bar)


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
    acc        = _accent(renk_hex)
    has_img_bg = bool(arka_plan_url)
    bg_source  = arka_plan_url or f"#{renk_hex}"

    # Avatar + background in parallel
    bg, av_img = await asyncio.gather(
        process_background(bg_source, OUT_W, OUT_H),
        load_avatar(avatar_url, AV_SIZE),
    )

    _apply_inner_panel(bg, has_img_bg)
    _paste_avatar(bg, av_img)

    draw = ImageDraw.Draw(bg)
    fn50 = _font(50)
    fn38 = _font(38)
    fn28 = _font(28)

    # ── Top-right: LEVEL + RANK ──────────────────────────────
    _right(draw, f"LEVEL: {level}       RANK: #{siralama}", 35, fn50)

    # ── Below: COINS ────────────────────────────────────────
    _right(draw, f"COINS: {bakiye:,}", 95, fn38)

    # ── Middle: username (left) + XP (right) ────────────────
    _left(draw,  kullanici_adi[:20], 145, fn50)
    _right(draw, f"{exp:,}/{gereken_exp:,} XP", 150, fn38)

    # ── Optional: bio or rozet ───────────────────────────────
    if bio:
        _left(draw, bio[:60], 203, fn28, fill=(158, 158, 192))
    elif aktif_rozet:
        _left(draw, f"🏅 {aktif_rozet[:30]}", 203, fn28, fill=acc)

    # ── XP bar ───────────────────────────────────────────────
    draw_xp_bar(bg, TEXT_X, 235, 619, 50, exp, gereken_exp, acc)

    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
