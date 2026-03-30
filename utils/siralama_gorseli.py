"""
utils/siralama_gorseli.py — assets/siralama_sablon.png üzerine top 10 sıralama çizer.
Koordinatlar 1024×573 şablonuna göre ayarlı; şablon değişirse PODIUM / LIST satırlarını güncelle.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import aiohttp
import asyncio

from utils.logger import setup_logger

log = setup_logger("siralama_gorseli")

_PROJE_KOK = Path(__file__).resolve().parent.parent
SABLON_YOLU = _PROJE_KOK / "assets" / "siralama_sablon.png"
_BOT_FONT = _PROJE_KOK / "assets" / "font.ttf"

# 1024×573 şablon — kalibre edilmiş merkezler (piksel)
PODIUM = [
    {"cx": 165, "cy": 142, "r": 56},
    {"cx": 375, "cy": 150, "r": 46},
    {"cx": 520, "cy": 160, "r": 40},
]

# Alt liste: her satırın avatar merkezi (sıra 4–10)
LISTE_SATIRLARI = [{"cx": 78, "cy": 302 + i * 38, "r": 20} for i in range(7)]

FONT_YOLLARI = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
if _BOT_FONT.is_file():
    FONT_YOLLARI.insert(0, str(_BOT_FONT))

FONT_INCE_YOLLARI = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
if _BOT_FONT.is_file():
    FONT_INCE_YOLLARI.insert(0, str(_BOT_FONT))


def _font(boyut: int, kalin: bool = True) -> ImageFont.FreeTypeFont:
    yollar = FONT_YOLLARI if kalin else FONT_INCE_YOLLARI
    for yol in yollar:
        if not os.path.exists(yol):
            continue
        try:
            return ImageFont.truetype(yol, boyut)
        except Exception:
            continue
    return ImageFont.load_default()


def _yuvarlak_maske(boyut: int) -> Image.Image:
    maske = Image.new("L", (boyut, boyut), 0)
    draw = ImageDraw.Draw(maske)
    draw.ellipse((0, 0, boyut, boyut), fill=255)
    return maske


async def _indir(url: str, boyut: tuple[int, int]) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                img = Image.open(io.BytesIO(data)).convert("RGBA")
                return img.resize(boyut, Image.LANCZOS)
    except Exception:
        return None


def _yazi_orta(draw: ImageDraw.ImageDraw, cx: int, y: int, metin: str, font: ImageFont.FreeTypeFont, fill: tuple):
    bbox = draw.textbbox((0, 0), metin, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w // 2, y), metin, font=font, fill=fill)


def _yazi_sag(draw: ImageDraw.ImageDraw, sag_x: int, cy: int, metin: str, font: ImageFont.FreeTypeFont, fill: tuple):
    bbox = draw.textbbox((0, 0), metin, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((sag_x - w, cy - h // 2), metin, font=font, fill=fill)


def _kisalt(metin: str, max_len: int) -> str:
    metin = metin.strip()
    if len(metin) <= max_len:
        return metin
    return metin[: max_len - 1] + "…"


async def siralama_gorseli_olustur(
    bot,
    satirlar: list,
) -> io.BytesIO:
    """
    satirlar: asyncpg.Record veya dict listesi — discord_id, username, bakiye
    """
    if not SABLON_YOLU.is_file():
        log.error("Sıralama şablonu bulunamadı: %s", SABLON_YOLU)
        raise FileNotFoundError(f"Şablon eksik: {SABLON_YOLU}")

    sablon = Image.open(SABLON_YOLU).convert("RGBA")
    kart = sablon.copy()
    draw = ImageDraw.Draw(kart)

    font_isim_podyum = _font(18, True)
    font_skor_podyum = _font(16, True)
    font_isim_liste = _font(17, True)
    font_skor_liste = _font(16, True)
    font_sira = _font(15, True)

    renk_isim = (245, 245, 255, 255)
    renk_skor = (255, 220, 120, 255)
    renk_golge = (0, 0, 0, 200)

    async def avatar_url(uid: int) -> str:
        try:
            u = await bot.fetch_user(uid)
            return u.display_avatar.url
        except Exception:
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    n = min(len(satirlar), 10)
    uids = [int(satirlar[i]["discord_id"]) for i in range(n)]

    url_gorevleri = [avatar_url(uid) for uid in uids]
    urls = await asyncio.gather(*url_gorevleri)

    # Podium avatars (0–2)
    for i in range(min(3, n)):
        row = satirlar[i]
        p = PODIUM[i]
        cx, cy, r = p["cx"], p["cy"], p["r"]
        boyut = r * 2
        av = await _indir(urls[i], (boyut, boyut))
        if av:
            maske = _yuvarlak_maske(boyut)
            yuv = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
            yuv.paste(av, (0, 0), maske)
            kart.paste(yuv, (cx - r, cy - r), yuv)
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(60, 60, 80, 230))

        isim = _kisalt(str(row["username"]), 14)
        skor = f"{int(row['bakiye']):,}"
        iy, sy = cy + r + 6, cy + r + 30
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _yazi_orta(draw, cx + dx, iy + dy, isim, font_isim_podyum, renk_golge)
        _yazi_orta(draw, cx, iy, isim, font_isim_podyum, renk_isim)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _yazi_orta(draw, cx + dx, sy + dy, skor, font_skor_podyum, renk_golge)
        _yazi_orta(draw, cx, sy, skor, font_skor_podyum, renk_skor)

    # Liste 4–10
    for j in range(3, n):
        idx = j - 3
        if idx >= len(LISTE_SATIRLARI):
            break
        row = satirlar[j]
        L = LISTE_SATIRLARI[idx]
        cx, cy, r = L["cx"], L["cy"], L["r"]
        boyut = r * 2
        av = await _indir(urls[j], (boyut, boyut))
        if av:
            maske = _yuvarlak_maske(boyut)
            yuv = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
            yuv.paste(av, (0, 0), maske)
            kart.paste(yuv, (cx - r, cy - r), yuv)
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(55, 55, 75, 220))

        rank_no = str(j + 1)
        isim = _kisalt(str(row["username"]), 22)
        skor = f"{int(row['bakiye']):,}"

        rx = cx + r + 12
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((rx + dx, cy - 9 + dy), rank_no, font=font_sira, fill=renk_golge)
        draw.text((rx, cy - 9), rank_no, font=font_sira, fill=renk_isim)

        ix = rx + 26
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((ix + dx, cy - 9 + dy), isim, font=font_isim_liste, fill=renk_golge)
        draw.text((ix, cy - 9), isim, font=font_isim_liste, fill=renk_isim)

        sag = 498
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _yazi_sag(draw, sag + dx, cy + dy, skor, font_skor_liste, renk_golge)
        _yazi_sag(draw, sag, cy, skor, font_skor_liste, renk_skor)

    buf = io.BytesIO()
    kart.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
