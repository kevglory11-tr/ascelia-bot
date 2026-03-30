"""
utils/siralama_gorseli.py — assets/siralama_sablon.png üzerine top 10 sıralama çizer.
Koordinatlar 1024×573 şablonuna göre ayarlı; şablon değişirse PODIUM / LIST satırlarını güncelle.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import aiohttp
import asyncio

from utils.logger import setup_logger

log = setup_logger("siralama_gorseli")

# Embed/destek: yeni hizalama çıktısını ayırt etmek için (kasa.py footer’da kullanılır)
GORSEL_SURUM = 6

_PROJE_KOK = Path(__file__).resolve().parent.parent
SABLON_YOLU = _PROJE_KOK / "assets" / "siralama_sablon.png"
_BOT_FONT = _PROJE_KOK / "assets" / "font.ttf"

# 1024×573 şablon — şablondaki koyu daire merkezlerine göre (otomatik tarama ile)
# Yarıçaplar çerçeveye sığacak şekilde küçük tutuldu; taşma olmasın diye.
PODIUM = [
    {"cx": 113, "cy": 101, "r": 26},
    {"cx": 263, "cy": 98, "r": 22},
    {"cx": 375, "cy": 110, "r": 21},
]

# Alt liste (4–10): merkez x şablonda satır başına ~84–88; cy aşağı kayarsa 10. sıra kesilir
LISTE_SATIRLARI = [
    {"cx": 87, "cy": 286, "r": 17},
    {"cx": 87, "cy": 329, "r": 17},
    {"cx": 87, "cy": 372, "r": 17},
    {"cx": 87, "cy": 415, "r": 17},
    {"cx": 87, "cy": 458, "r": 17},
    {"cx": 87, "cy": 501, "r": 17},
    {"cx": 87, "cy": 544, "r": 16},
]
LISTE_ISIM_X0 = 132
LISTE_SKOR_SAG = 458

# İsimler: mümkünse emoji + Latin (Windows’ta Segoe UI Emoji iyi karışık metin verir)
FONT_ISIM_YOLLARI = [
    r"C:\Windows\Fonts\seguiemj.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

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


def _font_isim(boyut: int) -> ImageFont.FreeTypeFont:
    yollar = FONT_ISIM_YOLLARI + FONT_YOLLARI
    for yol in yollar:
        if not os.path.exists(yol):
            continue
        try:
            return ImageFont.truetype(yol, boyut)
        except Exception:
            continue
    return ImageFont.load_default()


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


def _isim_guvenli(metin: str, max_len: int) -> str:
    """Çok bozuk glyph’leri azalt: kontrol karakterleri ve aşırı özel sembolleri temizle."""
    metin = metin.strip()
    metin = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", metin)
    return _kisalt(metin, max_len)


def _kisalt_genislik(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, metin: str, max_w: int) -> str:
    """Piksel genişliğine göre kısalt (uzun isimler skorun üstüne binmesin)."""
    if not metin:
        return metin
    if draw.textbbox((0, 0), metin, font=font)[2] - draw.textbbox((0, 0), metin, font=font)[0] <= max_w:
        return metin
    kis = metin
    while len(kis) > 1:
        deneme = kis[:-1] + "…"
        w = draw.textbbox((0, 0), deneme, font=font)[2] - draw.textbbox((0, 0), deneme, font=font)[0]
        if w <= max_w:
            return deneme
        kis = kis[:-1]
    return "…"


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

    font_isim_podyum = _font_isim(17)
    font_skor_podyum = _font(15, True)
    font_isim_liste = _font_isim(16)
    font_skor_liste = _font(15, True)

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

        isim = _isim_guvenli(str(row["username"]), 14)
        skor = f"{int(row['bakiye']):,}"
        iy, sy = cy + r + 4, cy + r + 26
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

        # Şablonda 4–10 sıra numaraları zaten basılı; tekrar yazma (üst üste binme oluyordu)
        isim = _isim_guvenli(str(row["username"]), 64)
        max_isim_w = LISTE_SKOR_SAG - LISTE_ISIM_X0 - 14
        isim = _kisalt_genislik(draw, font_isim_liste, isim, max_isim_w)
        skor = f"{int(row['bakiye']):,}"

        bbox_i = draw.textbbox((0, 0), isim, font=font_isim_liste)
        ih = bbox_i[3] - bbox_i[1]
        ix = LISTE_ISIM_X0
        iy = cy - ih // 2
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((ix + dx, iy + dy), isim, font=font_isim_liste, fill=renk_golge)
        draw.text((ix, iy), isim, font=font_isim_liste, fill=renk_isim)

        sag = LISTE_SKOR_SAG
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _yazi_sag(draw, sag + dx, cy + dy, skor, font_skor_liste, renk_golge)
        _yazi_sag(draw, sag, cy, skor, font_skor_liste, renk_skor)

    buf = io.BytesIO()
    kart.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli hazır (sürüm %s, kullanıcı=%s)", GORSEL_SURUM, n)
    return buf
