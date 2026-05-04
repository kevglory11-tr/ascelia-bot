"""
utils/profil_karti.py — Card1 (DiscordLevelingCard, birebir).
GIF arka plan desteği: .gif uzantılı banner → animasyonlu GIF çıktı.
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
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://discord.com"}
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                return Image.open(BytesIO(await r.read()))
    raise ValueError(f"Gorsel indirilemedi: {url}")


def _load_gif_frames(path: str) -> list[Image.Image]:
    """GIF'ten tüm frame'leri RGB olarak döndür."""
    frames = []
    with Image.open(path) as gif:
        for i in range(getattr(gif, "n_frames", 1)):
            gif.seek(i)
            frames.append(gif.convert("RGB").copy())
    return frames


def _build_static_layers(
    kullanici_adi: str,
    level: int,
    exp: int,
    gereken_exp: int,
    avatar: Image.Image,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    """
    Arka plandan bağımsız katmanları hazırla.
    Dönen değerler: (overlay, xp_bar_im, av_masked, mask, curved)
    Ama tek seferlik hazırlık için composite tuple dönüyoruz.
    """
    overlay  = Image.open(_CARD1 / "overlay1.png")
    mask_img = Image.open(_CARD1 / "mask_circle.jpg").convert("L").resize((170, 170))
    curved   = Image.open(_CARD1 / "curvedoverlay.png").convert("L")

    # XP bar
    bar_exp = max((exp / gereken_exp) * 420 if gereken_exp else 0, 50)
    bar_im  = Image.new("RGB", (490, 51), (0, 0, 0))
    bd      = ImageDraw.Draw(bar_im, "RGBA")
    bd.rounded_rectangle((0, 0, 420, 50), 30, fill=(255, 255, 255, 50))
    if exp != 0:
        bd.rounded_rectangle((0, 0, int(bar_exp), 50), 30, fill=(255, 255, 255, 255))

    # Avatar (masked)
    av = Image.new("RGB", avatar.size, (0, 0, 0))
    try:
        av.paste(avatar, mask=avatar.convert("RGBA").split()[3])
    except Exception:
        av.paste(avatar, (0, 0))

    return overlay, bar_im, av, mask_img, curved


def _composite_frame(
    bg_frame: Image.Image,
    overlay: Image.Image,
    bar_im: Image.Image,
    av: Image.Image,
    mask_img: Image.Image,
    curved: Image.Image,
    kullanici_adi: str,
    level: int,
    exp: int,
    gereken_exp: int,
    f40: ImageFont.FreeTypeFont,
    f30: ImageFont.FreeTypeFont,
) -> Image.Image:
    """Tek bir arka plan frame'i üzerine tüm kartı çiz, RGBA döndür."""
    TEXT = (255, 255, 255)

    canvas = Image.new("RGBA", overlay.size)
    bg_resized = bg_frame.convert("RGB").resize((638, 159))
    canvas.paste(bg_resized, (0, 0))
    canvas = canvas.resize(overlay.size)
    canvas.paste(overlay, (0, 0), overlay)

    draw = ImageDraw.Draw(canvas)
    draw.text((205, (327 / 2) + 20), kullanici_adi[:20],
              font=f40, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    canvas.paste(bar_im, (190, 235))

    level_y = (327 / 2) + 125
    draw.text((197, level_y), f"LEVEL - {_fmt(level)}",
              font=f30, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))
    xp_str = f"{_fmt(exp)}/{_fmt(gereken_exp)}"
    xp_w   = draw.textlength(xp_str, font=f30)
    draw.text((638 - xp_w - 50, level_y), xp_str,
              font=f30, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    canvas.paste(av, (13, 65), mask_img)

    final = Image.new("RGBA", canvas.size)
    final.paste(canvas, (0, 0), curved)
    return final.resize((505, 259), Image.LANCZOS)


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

    avatar = await _fetch(avatar_url)
    avatar = avatar.resize((170, 170))

    overlay, bar_im, av, mask_img, curved = _build_static_layers(
        kullanici_adi, level, exp, gereken_exp, avatar
    )
    f40 = ImageFont.truetype(_FONT, 40)
    f30 = ImageFont.truetype(_FONT, 30)

    # GIF arka plan → animasyonlu çıktı
    is_gif = arka_plan_url and not arka_plan_url.startswith("http") and arka_plan_url.endswith(".gif")

    if is_gif:
        try:
            gif_frames = _load_gif_frames(arka_plan_url)
        except Exception:
            gif_frames = []

        if gif_frames:
            card_frames = [
                _composite_frame(f, overlay, bar_im, av, mask_img, curved,
                                 kullanici_adi, level, exp, gereken_exp, f40, f30)
                for f in gif_frames
            ]
            buf = io.BytesIO()
            card_frames[0].save(
                buf, "GIF",
                save_all=True,
                append_images=card_frames[1:],
                loop=0,
                duration=83,
                optimize=False,
            )
            buf.seek(0)
            return buf, True   # (buffer, is_animated)

    # Statik arka plan
    if arka_plan_url:
        try:
            if arka_plan_url.startswith("http"):
                fetched = await _fetch(arka_plan_url)
            else:
                fetched = Image.open(arka_plan_url)
            if fetched.width < 100 or fetched.height < 50:
                raise ValueError("Gecersiz gorsel")
            bg = fetched.convert("RGB").resize((638, 159))
        except Exception:
            bg = _solid(renk_hex)
    else:
        bg = _solid(renk_hex)

    final = _composite_frame(bg, overlay, bar_im, av, mask_img, curved,
                              kullanici_adi, level, exp, gereken_exp, f40, f30)

    buf = io.BytesIO()
    final.save(buf, "PNG")
    buf.seek(0)
    return buf, False   # (buffer, is_animated)


def _solid(renk_hex: str) -> Image.Image:
    try:
        r, g, b = (int(renk_hex[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        r, g, b = 30, 30, 50
    return Image.new("RGB", (638, 159), (r, g, b))
