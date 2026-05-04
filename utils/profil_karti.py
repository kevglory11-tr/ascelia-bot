"""
utils/profil_karti.py — Card1 (DiscordLevelingCard, birebir).
"""

import io
from io import BytesIO
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

_CARD1 = Path(__file__).parent.parent / "assets" / "card1"
_FONT  = str(_CARD1 / "levelfont.otf")


def _fmt(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


async def _fetch(url: str) -> Image.Image:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                return Image.open(BytesIO(await r.read()))
    raise ValueError(f"Gorsel indirilemedi: {url}")


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

    # Avatar
    avatar = await _fetch(avatar_url)
    avatar = avatar.resize((170, 170))

    # Arka plan
    overlay = Image.open(_CARD1 / "overlay1.png")
    canvas  = Image.new("RGBA", overlay.size)

    if arka_plan_url:
        try:
            bg = (await _fetch(arka_plan_url)).resize((638, 159))
        except Exception:
            bg = _solid(renk_hex)
    else:
        bg = _solid(renk_hex)

    canvas.paste(bg, (0, 0))
    canvas = canvas.resize(overlay.size)
    canvas.paste(overlay, (0, 0), overlay)

    draw = ImageDraw.Draw(canvas)
    f40  = ImageFont.truetype(_FONT, 40)
    f30  = ImageFont.truetype(_FONT, 30)
    TEXT = (255, 255, 255)

    # Kullanıcı adı
    draw.text((205, (327 / 2) + 20), kullanici_adi[:20],
              font=f40, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    # XP bar
    bar_exp = max((exp / gereken_exp) * 420 if gereken_exp else 0, 50)
    bar_im  = Image.new("RGB", (490, 51), (0, 0, 0))
    bd      = ImageDraw.Draw(bar_im, "RGBA")
    bd.rounded_rectangle((0, 0, 420, 50), 30, fill=(255, 255, 255, 50))
    if exp != 0:
        bd.rounded_rectangle((0, 0, int(bar_exp), 50), 30, fill=(147, 51, 234, 255))
    canvas.paste(bar_im, (190, 235))

    # Level + XP metin
    level_y = (327 / 2) + 125
    draw.text((197, level_y), f"LEVEL - {_fmt(level)}",
              font=f30, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    xp_str = f"{_fmt(exp)}/{_fmt(gereken_exp)}"
    xp_w   = draw.textlength(xp_str, font=f30)
    draw.text((638 - xp_w - 50, level_y), xp_str,
              font=f30, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    # Avatar
    mask = Image.open(_CARD1 / "mask_circle.jpg").convert("L").resize((170, 170))
    av   = Image.new("RGB", avatar.size, (0, 0, 0))
    try:
        av.paste(avatar, mask=avatar.convert("RGBA").split()[3])
    except Exception:
        av.paste(avatar, (0, 0))
    canvas.paste(av, (13, 65), mask)

    # Curved overlay
    curved = Image.open(_CARD1 / "curvedoverlay.png").convert("L")
    final  = Image.new("RGBA", canvas.size)
    final.paste(canvas, (0, 0), curved)
    final  = final.resize((505, 259), Image.LANCZOS)

    buf = io.BytesIO()
    final.save(buf, "PNG")
    buf.seek(0)
    return buf


def _solid(renk_hex: str) -> Image.Image:
    try:
        r, g, b = (int(renk_hex[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        r, g, b = 30, 30, 50
    return Image.new("RGB", (638, 159), (r, g, b))
