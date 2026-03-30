"""
utils/siralama_gorseli.py — Sıralama görseli: arka plan + tamamen kodla çizilen tablo.

assets/siralama_arka.png  (opsiyonel) — boş veya illüstrasyon; yoksa koyu gradyan kullanılır.
Eski siralama_sablon.png üzerine piksel hizalama kullanılmaz (bakımı zordu).
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

GORSEL_SURUM = 7

_PROJE_KOK = Path(__file__).resolve().parent.parent
# İstersen buraya kendi boş / arka görselini koy: siralama_arka.png
ARKA_YOLU = _PROJE_KOK / "assets" / "siralama_arka.png"
_BOT_FONT = _PROJE_KOK / "assets" / "font.ttf"

# Çıktı boyutu (Discord için uygun genişlik)
GENISLIK = 1024
YUKSEKLIK = 680

MARGIN = 20
SATIR_YUKSEKLIK = 48
SATIR_ARALIK = 7

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
]
if _BOT_FONT.is_file():
    FONT_YOLLARI.insert(0, str(_BOT_FONT))

FONT_INCE_YOLLARI = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
if _BOT_FONT.is_file():
    FONT_INCE_YOLLARI.insert(0, str(_BOT_FONT))


def _font_isim(boyut: int) -> ImageFont.FreeTypeFont:
    for yol in FONT_ISIM_YOLLARI + FONT_YOLLARI:
        if os.path.exists(yol):
            try:
                return ImageFont.truetype(yol, boyut)
            except Exception:
                continue
    return ImageFont.load_default()


def _font(boyut: int, kalin: bool = True) -> ImageFont.FreeTypeFont:
    yollar = FONT_YOLLARI if kalin else FONT_INCE_YOLLARI
    for yol in yollar:
        if os.path.exists(yol):
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


def _gradyan_arka(w: int, h: int) -> Image.Image:
    """Şık koyu mor-lacivert gradyan."""
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(22 + t * 18)
        g = int(14 + t * 22)
        b = int(48 + t * 35)
        a = 255
        for x in range(w):
            px[x, y] = (r, g, b, a)
    return img


def _arka_hazirla(w: int, h: int) -> Image.Image:
    if ARKA_YOLU.is_file():
        try:
            bg = Image.open(ARKA_YOLU).convert("RGBA")
            return bg.resize((w, h), Image.LANCZOS)
        except Exception as e:
            log.warning("siralama_arka.png okunamadı, gradyan kullanılıyor: %s", e)
    return _gradyan_arka(w, h)


def _okunaklik_katmani(ust: Image.Image) -> Image.Image:
    """Metin okunaklı olsun diye hafif koyu film (RGBA üst üste)."""
    film = Image.new("RGBA", ust.size, (10, 8, 22, 115))
    return Image.alpha_composite(ust, film)


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


def _metin_guvenli(s: str, max_len: int = 32) -> str:
    s = s.strip()
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def _kisalt_genislik(
    draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, metin: str, max_w: int
) -> str:
    if draw.textbbox((0, 0), metin, font=font)[2] - draw.textbbox((0, 0), metin, font=font)[0] <= max_w:
        return metin
    k = metin
    while len(k) > 1:
        d = k[:-1] + "…"
        w = draw.textbbox((0, 0), d, font=font)[2] - draw.textbbox((0, 0), d, font=font)[0]
        if w <= max_w:
            return d
        k = k[:-1]
    return "…"


def _golge_yazi(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    metin: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    golge: tuple[int, int, int, int] = (0, 0, 0, 200),
):
    x, y = xy
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        draw.text((x + dx, y + dy), metin, font=font, fill=golge)
    draw.text((x, y), metin, font=font, fill=fill)


def _yazi_orta_x(draw, cx: int, y: int, metin: str, font, fill):
    bbox = draw.textbbox((0, 0), metin, font=font)
    w = bbox[2] - bbox[0]
    _golge_yazi(draw, (cx - w // 2, y), metin, font, fill)


def _yazi_sag(draw, sag_x: int, cy: int, metin: str, font, fill):
    bbox = draw.textbbox((0, 0), metin, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    _golge_yazi(draw, (sag_x - w, cy - h // 2), metin, font, fill)


async def siralama_gorseli_olustur(bot, satirlar: list) -> io.BytesIO:
    """
    satirlar: asyncpg.Record veya dict — discord_id, username, bakiye
    """
    w, h = GENISLIK, YUKSEKLIK
    arka = _arka_hazirla(w, h)
    arka = _okunaklik_katmani(arka)
    canvas = arka.copy()
    draw = ImageDraw.Draw(canvas)

    font_isim_buyuk = _font_isim(18)
    font_isim_satir = _font_isim(16)
    font_skor = _font(15, True)
    font_sira = _font(16, True)

    renk_isim = (248, 248, 255, 255)
    renk_skor = (255, 215, 100, 255)
    renk_sira = (200, 205, 230, 255)

    # ── Üst 3: kartlar ─────────────────────────────────────
    gap = 14
    ust_y = 16
    kart_h = 172
    ic = w - 2 * MARGIN
    kart_w = (ic - 2 * gap) // 3

    kenarlar = [
        (218, 165, 32, 255),
        (192, 192, 210, 255),
        (205, 127, 50, 255),
    ]

    async def avatar_url(uid: int) -> str:
        try:
            u = await bot.fetch_user(uid)
            return u.display_avatar.url
        except Exception:
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    n = min(len(satirlar), 10)
    uids = [int(satirlar[i]["discord_id"]) for i in range(n)]
    urls = await asyncio.gather(*[avatar_url(uid) for uid in uids])

    for i in range(min(3, n)):
        x0 = MARGIN + i * (kart_w + gap)
        y0 = ust_y
        ic_renk = kenarlar[i]
        draw.rounded_rectangle(
            [x0, y0, x0 + kart_w, y0 + kart_h],
            radius=16,
            fill=(18, 16, 32, 230),
            outline=ic_renk,
            width=3,
        )
        cx = x0 + kart_w // 2
        r = 40 if i == 0 else 34 if i == 1 else 30
        boyut = r * 2
        av = await _indir(urls[i], (boyut, boyut))
        ay = y0 + 28
        if av:
            maske = _yuvarlak_maske(boyut)
            yuv = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
            yuv.paste(av, (0, 0), maske)
            canvas.paste(yuv, (cx - r, ay), yuv)
        else:
            draw.ellipse([cx - r, ay, cx + r, ay + r * 2], fill=(55, 55, 75, 240))

        isim = _metin_guvenli(str(satirlar[i]["username"]), 16)
        skor = f"{int(satirlar[i]['bakiye']):,}"
        iy = ay + boyut + 10
        _yazi_orta_x(draw, cx, iy, isim, font_isim_buyuk, renk_isim)
        sy = iy + 26
        _yazi_orta_x(draw, cx, sy, skor, font_skor, renk_skor)

    # ── 4–10: satırlar (tek tutarlı grid) ───────────────────
    y_liste = ust_y + kart_h + 20
    sol_ic = MARGIN + 12
    rank_col_w = 44
    av_r = 18
    av_x0 = sol_ic + rank_col_w + 8
    isim_x0 = av_x0 + av_r * 2 + 14
    sag_kenar = w - MARGIN - 16
    max_isim_w = sag_kenar - isim_x0 - 12

    for j in range(3, n):
        idx = j - 3
        row = satirlar[j]
        ry = y_liste + idx * (SATIR_YUKSEKLIK + SATIR_ARALIK)
        rx1, ry1 = MARGIN, ry
        rx2, ry2 = w - MARGIN, ry + SATIR_YUKSEKLIK

        draw.rounded_rectangle(
            [rx1, ry1, rx2, ry2],
            radius=12,
            fill=(16, 18, 38, 235),
            outline=(80, 70, 120, 180),
            width=1,
        )

        rno = str(j + 1)
        bbox = draw.textbbox((0, 0), rno, font=font_sira)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        rcx = sol_ic + (rank_col_w - tw) // 2
        rcy = ry + (SATIR_YUKSEKLIK - th) // 2
        _golge_yazi(draw, (rcx, rcy), rno, font_sira, renk_sira)

        cx = av_x0 + av_r
        cy = ry + SATIR_YUKSEKLIK // 2
        boyut = av_r * 2
        av = await _indir(urls[j], (boyut, boyut))
        if av:
            maske = _yuvarlak_maske(boyut)
            yuv = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
            yuv.paste(av, (0, 0), maske)
            canvas.paste(yuv, (cx - av_r, cy - av_r), yuv)
        else:
            draw.ellipse([cx - av_r, cy - av_r, cx + av_r, cy + av_r], fill=(60, 60, 85, 255))

        isim = _metin_guvenli(str(row["username"]), 48)
        isim = _kisalt_genislik(draw, font_isim_satir, isim, max_isim_w)
        bbox_i = draw.textbbox((0, 0), isim, font=font_isim_satir)
        ih = bbox_i[3] - bbox_i[1]
        iy = ry + (SATIR_YUKSEKLIK - ih) // 2
        _golge_yazi(draw, (isim_x0, iy), isim, font_isim_satir, renk_isim)

        skor = f"{int(row['bakiye']):,}"
        _yazi_sag(draw, sag_kenar, cy, skor, font_skor, renk_skor)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli (tam çizim v%s, kullanıcı=%s)", GORSEL_SURUM, n)
    return buf
