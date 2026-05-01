# utils/profil_karti.py — Discord Level Card Generator
# Supersampling: 1600x500 internal render → LANCZOS → 800x250 final output
#
# Helper functions: load_avatar | process_background | draw_xp_bar | draw_text_elements

import io
import os
import glob
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Render / output dimensions ────────────────────────────────────────────────
OUT_W  = 800
OUT_H  = 250
KART_W = OUT_W * 2   # 1600  — internal render width
KART_H = OUT_H * 2   # 500   — internal render height

# Layout constants (all in render-pixel space)
PAD      = 50
LEFT_BAR = 8
AV_SIZE  = 300        # avatar diameter (display ≈ 150 px)
TEXT_X   = PAD + AV_SIZE + 60    # right-panel text start x = 410


# ── Font discovery ────────────────────────────────────────────────────────────

def _find_font(names: list[str]) -> str | None:
    dirs = [
        "/usr/share/fonts", "/usr/local/share/fonts",
        "/run/current-system/sw/share/fonts", "/nix/store",
        "C:/Windows/Fonts",
    ]
    for name in names:
        for d in dirs:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        for d in dirs:
            if not os.path.isdir(d):
                continue
            hits = glob.glob(os.path.join(d, "**", name), recursive=True)
            if hits:
                return hits[0]
    return None


_BOLD  = _find_font(["DejaVuSans-Bold.ttf",    "LiberationSans-Bold.ttf",
                      "FreeSansBold.ttf",        "Ubuntu-B.ttf",  "arialbd.ttf"])
_PLAIN = _find_font(["DejaVuSans.ttf",          "LiberationSans-Regular.ttf",
                      "FreeSans.ttf",            "Ubuntu-R.ttf",  "arial.ttf"])


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Load TTF font with safe fallback. Never returns default bitmap font unless unavoidable."""
    path = _BOLD if bold else _PLAIN
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ── Color utilities ───────────────────────────────────────────────────────────

def _parse_hex(h: str) -> tuple[int, int, int]:
    try:
        h = h.strip("#")
        return int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return (30, 30, 47)


def _accent(h: str) -> tuple[int, int, int]:
    """Derive a visible accent color from a hex string."""
    r, g, b = _parse_hex(h)
    m = max(r, g, b)
    if m < 90:                         # too dark — boost to a visible level
        f = 200 / max(m, 1)
        r = min(int(r * f), 255)
        g = min(int(g * f), 255)
        b = min(int(b * f), 255)
    return (r, g, b)


def _circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _layer(base: Image.Image, draw_fn) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create transparent RGBA layer, apply draw_fn, alpha-composite onto base."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    out = Image.alpha_composite(base, layer)
    return out, ImageDraw.Draw(out)


# ── Helper 1: load_avatar ─────────────────────────────────────────────────────

async def load_avatar(url: str, size: int) -> Image.Image:
    """
    Download avatar from URL.
    Returns a square-cropped, LANCZOS-resized circular RGBA image.
    Falls back to a placeholder if download fails.
    """
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    raw = Image.open(io.BytesIO(await r.read())).convert("RGBA")
                    # center-crop to square
                    w, h  = raw.size
                    s     = min(w, h)
                    raw   = raw.crop(((w - s) // 2, (h - s) // 2,
                                      (w + s) // 2, (h + s) // 2))
                    raw   = raw.resize((size, size), Image.Resampling.LANCZOS)
                    # apply circular mask
                    out   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                    out.paste(raw, (0, 0), _circle_mask(size))
                    return out
    except Exception:
        pass

    # placeholder avatar
    ph = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(ph).ellipse([0, 0, size - 1, size - 1], fill=(80, 80, 110, 255))
    return ph


# ── Helper 2: process_background ─────────────────────────────────────────────

async def process_background(background: str, width: int, height: int) -> Image.Image:
    """
    background: hex string (e.g. '#1e1e2f') OR image URL.
    Returns a (width × height) RGBA image with a dark overlay already applied.
    Falls back to dark solid color on any error.
    """
    is_url = background.startswith(("http://", "https://"))

    if is_url:
        try:
            async with aiohttp.ClientSession() as ses:
                async with ses.get(background, timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        img = Image.open(io.BytesIO(await r.read())).convert("RGBA")
                        # cover-resize with LANCZOS
                        iw, ih  = img.size
                        scale   = max(width / iw, height / ih)
                        nw, nh  = int(iw * scale) + 1, int(ih * scale) + 1
                        img     = img.resize((nw, nh), Image.Resampling.LANCZOS)
                        left    = (nw - width)  // 2
                        top     = (nh - height) // 2
                        img     = img.crop((left, top, left + width, top + height))
                        img     = img.filter(ImageFilter.GaussianBlur(2))
                        # dark overlay for readability
                        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 155))
                        return Image.alpha_composite(img, overlay)
        except Exception:
            pass  # fall through to solid-color fallback

    # Hex color → very dark derivation of the chosen color
    r, g, b = _parse_hex(background)
    base = (max(r // 9, 6), max(g // 9, 6), max(b // 8 + 3, 10))
    return Image.new("RGBA", (width, height), (*base, 255))


# ── Helper 3: draw_xp_bar ────────────────────────────────────────────────────

def draw_xp_bar(canvas: Image.Image,
                x: int, y: int, width: int, height: int,
                current_xp: int, required_xp: int,
                accent: tuple) -> Image.Image:
    """
    Draw a clean, minimal rounded XP bar.
    - Track: dark gray (no glow, no noise)
    - Fill: solid accent color
    - No shine or gradient effects.
    """
    progress = min(current_xp / max(required_xp, 1), 1.0)
    fill_w   = int(width * progress)
    radius   = height // 2

    # Dark track
    def bg(d):
        d.rounded_rectangle([x, y, x + width, y + height],
                             radius=radius, fill=(35, 35, 50, 255))
    canvas, _ = _layer(canvas, bg)

    # Accent fill (solid, no effects)
    if fill_w > radius:
        def fill(d):
            d.rounded_rectangle([x, y, x + fill_w, y + height],
                                 radius=radius, fill=(*accent, 255))
        canvas, _ = _layer(canvas, fill)

    return canvas


# ── Helper 4: draw_text_elements ─────────────────────────────────────────────

def draw_text_elements(
    canvas:       Image.Image,
    draw:         ImageDraw.ImageDraw,
    username:     str,
    level:        int,
    bio:          str | None,
    aktif_rozet:  str | None,
    text_x:       int,
    accent:       tuple,
) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    """
    Draw username, level, optional bio, optional rozet pill.
    Font sizes are defined at 2x render scale — readable after LANCZOS downscale.
    Returns (canvas, draw, next_y) where next_y is the first free Y below all text.
    """
    WHITE = (255, 255, 255, 255)
    MUTED = (158, 158, 192, 215)

    # Font sizes at 2x render (display size = half):
    fn_name  = _font(72, bold=True)    # display ≈ 36 px — spec range: 60-80 px render ✓
    fn_level = _font(44, bold=True)    # display ≈ 22 px — spec range: 40-50 px render ✓
    fn_sub   = _font(30, bold=False)   # display ≈ 15 px

    # ── Username ───────────────────────────────────────────────
    draw.text((text_x, 78), username[:20], font=fn_name, fill=WHITE)
    ty = 78 + 72 + 14   # 164

    # ── Level ─────────────────────────────────────────────────
    draw.text((text_x, ty), f"Seviye {level}", font=fn_level, fill=(*accent, 255))
    ty += 44 + 16   # 224

    # ── Bio (optional) ────────────────────────────────────────
    if bio:
        draw.text((text_x, ty), bio[:50], font=fn_sub, fill=MUTED)
        ty += 30 + 10   # 264

    # ── Rozet pill (optional) ─────────────────────────────────
    if aktif_rozet:
        rtxt = aktif_rozet[:24]
        bbox = draw.textbbox((0, 0), rtxt, font=fn_sub)
        pw   = bbox[2] - bbox[0] + 26
        ph   = 34
        pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle(
            [0, 0, pw - 1, ph - 1], radius=ph // 2,
            fill=(*accent, 38), outline=(*accent, 145), width=1,
        )
        canvas.paste(pill, (text_x, ty), pill)
        draw = ImageDraw.Draw(canvas)
        draw.text((text_x + 13, ty + 7), rtxt, font=fn_sub, fill=(*accent, 232))
        ty += ph + 10   # +44

    return canvas, draw, ty


# ── Main entry point ──────────────────────────────────────────────────────────

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
    """
    Generate a Discord level card.
    Internal render: 1600x500 → LANCZOS downscale → 800x250 final output.
    """
    acc = _accent(renk_hex)

    # ── Step 1: Background ────────────────────────────────────
    bg_source = arka_plan_url if arka_plan_url else f"#{renk_hex}"
    kart      = await process_background(bg_source, KART_W, KART_H)

    # ── Step 2: Avatar ────────────────────────────────────────
    av_img = await load_avatar(avatar_url, AV_SIZE)
    av_x   = PAD
    av_y   = (KART_H - AV_SIZE) // 2   # vertically centered = 100
    av_cx  = av_x + AV_SIZE // 2        # 200
    av_cy  = av_y + AV_SIZE // 2        # 250

    # Avatar shadow
    def av_shadow(d):
        sr = AV_SIZE // 2 + 14
        d.ellipse([av_cx - sr, av_cy - sr, av_cx + sr, av_cy + sr],
                  fill=(0, 0, 0, 88))
    kart, draw = _layer(kart, av_shadow)

    # Accent ring (4 render px = 2 display px)
    ring_r = AV_SIZE // 2 + 5
    draw.ellipse([av_cx - ring_r, av_cy - ring_r, av_cx + ring_r, av_cy + ring_r],
                 outline=(*acc, 255), width=4)

    kart.paste(av_img, (av_x, av_y), av_img)
    draw = ImageDraw.Draw(kart)

    # ── Step 3: Left accent bar ───────────────────────────────
    def lbar(d):
        d.rectangle([(0, 0), (LEFT_BAR, KART_H)], fill=(*acc, 255))
    kart, draw = _layer(kart, lbar)

    # ── Step 4: Text elements ─────────────────────────────────
    kart, draw, stat_y = draw_text_elements(
        kart, draw, kullanici_adi, level, bio, aktif_rozet, TEXT_X, acc
    )

    # ── Step 5: Stats row (COINS + SIRALAMA) ──────────────────
    WHITE = (255, 255, 255, 255)
    MUTED = (158, 158, 192, 215)
    fn_slbl = _font(26, bold=False)   # display ≈ 13 px
    fn_sval = _font(38, bold=True)    # display ≈ 19 px

    stats  = [("COINS", f"{bakiye:,}"), ("SIRALAMA", f"#{siralama:,}")]
    col_w  = 280
    for i, (lbl, val) in enumerate(stats):
        sx = TEXT_X + i * col_w
        draw.text((sx, stat_y),      lbl, font=fn_slbl, fill=MUTED)
        draw.text((sx, stat_y + 30), val, font=fn_sval, fill=WHITE)

    # Vertical dividers between stats
    def vdivs(d):
        for i in range(1, len(stats)):
            dx = TEXT_X + i * col_w - 18
            d.rectangle([(dx, stat_y), (dx + 2, stat_y + 80)],
                        fill=(255, 255, 255, 18))
    kart, draw = _layer(kart, vdivs)

    # ── Step 6: Horizontal separator before XP bar ────────────
    bar_y = 390
    def hsep(d):
        d.rectangle([(TEXT_X, bar_y - 20), (KART_W - PAD, bar_y - 18)],
                    fill=(255, 255, 255, 18))
    kart, draw = _layer(kart, hsep)

    # ── Step 7: XP bar ────────────────────────────────────────
    bar_x = TEXT_X
    bar_w = KART_W - TEXT_X - PAD   # 1140 render px
    bar_h = 34

    kart = draw_xp_bar(kart, bar_x, bar_y, bar_w, bar_h, exp, gereken_exp, acc)
    draw = ImageDraw.Draw(kart)

    # XP text — spec range 28-36 px render ✓
    fn_xp = _font(30, bold=False)   # display ≈ 15 px
    pct       = int(min(exp / max(gereken_exp, 1), 1.0) * 100)
    xp_left   = f"{exp:,} / {gereken_exp:,} XP"
    xp_right  = f"%{pct}"

    draw.text((bar_x, bar_y + bar_h + 12), xp_left, font=fn_xp, fill=MUTED)
    bbox = draw.textbbox((0, 0), xp_right, font=fn_xp)
    draw.text((bar_x + bar_w - (bbox[2] - bbox[0]), bar_y + bar_h + 12),
              xp_right, font=fn_xp, fill=WHITE)

    # ── Step 8: Bottom accent stripe ──────────────────────────
    def stripe(d):
        d.rectangle([(0, KART_H - 8), (KART_W, KART_H)], fill=(*acc, 228))
    kart, _ = _layer(kart, stripe)

    # ── Step 9: Supersampling → 800x250 ───────────────────────
    # Composite over dark bg first (prevents transparent → white artifacts)
    dark  = Image.new("RGBA", (KART_W, KART_H), (8, 8, 14, 255))
    final = Image.alpha_composite(dark, kart)

    # LANCZOS resize to final output dimensions
    final = final.resize((OUT_W, OUT_H), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    final.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ── Example usage ─────────────────────────────────────────────────────────────
# import asyncio
#
# async def main():
#     buf = await profil_karti_olustur(
#         kullanici_adi = "tmaselica",
#         avatar_url    = "https://cdn.discordapp.com/avatars/.../avatar.png",
#         level         = 23,
#         exp           = 1234,
#         gereken_exp   = 1890,
#         bakiye        = 15230,
#         siralama      = 4,
#         aktif_rozet   = "Vanguard",
#         arka_plan_url = None,        # or image URL
#         renk_hex      = "6c3483",    # or "2b2d31" for default
#         bio           = "Ascelia sunucusunun kahraman!",
#     )
#     with open("card.png", "wb") as f:
#         f.write(buf.read())
#
# asyncio.run(main())
