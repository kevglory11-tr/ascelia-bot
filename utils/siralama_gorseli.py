"""
utils/siralama_gorseli.py — Kompakt, modern sıralama kartı (kodla çizim).

assets/siralama_arka.png — opsiyonel arka plan; yoksa nötr koyu gradyan.
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

GORSEL_SURUM = 8

_PROJE_KOK = Path(__file__).resolve().parent.parent
ARKA_YOLU = _PROJE_KOK / "assets" / "siralama_arka.png"
_BOT_FONT = _PROJE_KOK / "assets" / "font.ttf"

# Kompakt çıktı — Discord’da daha az “dev ekran” hissi
GENISLIK = 720
YUKSEKLIK = 468

MARGIN = 18
UST_BASLIK_H = 32
PODYUM_KART_H = 100
PODYUM_GAP = 8
LISTE_SATIR_H = 38
LISTE_GAP = 5

# Modern koyu arayüz paleti (slate / indigo)
C_ARKA_UST = (12, 18, 32)
C_ARKA_ALT = (15, 23, 42)
C_YUZEY = (30, 41, 59)  # slate-700
C_YUZEY2 = (24, 33, 48)
C_KENAR = (71, 85, 105)  # slate-600
C_METIN = (241, 245, 249)  # slate-100
C_SOLUK = (148, 163, 184)  # slate-400
C_VURG = (129, 140, 248)  # indigo-400
C_ALTIN = (251, 191, 36)  # amber-400
C_GUM = (203, 213, 225)
C_BRONZ = (180, 83, 9)

FONT_ISIM_YOLLARI = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\seguiemj.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

FONT_KALIN = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
if _BOT_FONT.is_file():
    FONT_KALIN.insert(0, str(_BOT_FONT))


def _font(path_list: list[str], boyut: int) -> ImageFont.FreeTypeFont:
    for yol in path_list:
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


def _gradyan_diagonal(w: int, h: int) -> Image.Image:
    """Yumuşak çapraz geçiş."""
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / max(w - 1, 1) + y / max(h - 1, 1)) * 0.5
            r = int(C_ARKA_UST[0] + t * (C_ARKA_ALT[0] - C_ARKA_UST[0]))
            g = int(C_ARKA_UST[1] + t * (C_ARKA_ALT[1] - C_ARKA_UST[1]))
            b = int(C_ARKA_UST[2] + t * (C_ARKA_ALT[2] - C_ARKA_UST[2]))
            px[x, y] = (r, g, b, 255)
    return img


def _arka_hazirla(w: int, h: int) -> Image.Image:
    if ARKA_YOLU.is_file():
        try:
            bg = Image.open(ARKA_YOLU).convert("RGBA")
            return bg.resize((w, h), Image.LANCZOS)
        except Exception as e:
            log.warning("siralama_arka.png okunamadı: %s", e)
    return _gradyan_diagonal(w, h)


def _film_arka(ust: Image.Image) -> Image.Image:
    """Özel fotoğraf varsa hafif karartı; gradyanda gereksiz."""
    if not ARKA_YOLU.is_file():
        return ust
    film = Image.new("RGBA", ust.size, (11, 15, 28, 95))
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


def _metin_guvenli(s: str, max_len: int = 28) -> str:
    s = s.strip()
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def _kisalt_genislik(
    draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, metin: str, max_w: int
) -> str:
    if not metin:
        return metin
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


def _tx(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    metin: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
):
    draw.text(xy, metin, font=font, fill=fill)


def _tx_orta(draw, cx: int, y: int, metin: str, font, fill):
    bbox = draw.textbbox((0, 0), metin, font=font)
    w = bbox[2] - bbox[0]
    _tx(draw, (cx - w // 2, y), metin, font, fill)


def _tx_sag(draw, sag_x: int, cy: int, metin: str, font, fill):
    bbox = draw.textbbox((0, 0), metin, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    _tx(draw, (sag_x - w, cy - h // 2), metin, font, fill)


async def siralama_gorseli_olustur(bot, satirlar: list) -> io.BytesIO:
    w, h = GENISLIK, YUKSEKLIK
    arka = _arka_hazirla(w, h)
    arka = _film_arka(arka)
    im = arka.copy()
    draw = ImageDraw.Draw(im)

    f_baslik = _font(FONT_KALIN, 11)
    f_podyum_isim = _font(FONT_ISIM_YOLLARI, 13)
    f_podyum_skor = _font(FONT_KALIN, 12)
    f_satir_isim = _font(FONT_ISIM_YOLLARI, 13)
    f_satir_skor = _font(FONT_KALIN, 12)
    f_sira = _font(FONT_KALIN, 12)

    async def avatar_url(uid: int) -> str:
        try:
            u = await bot.fetch_user(uid)
            return u.display_avatar.url
        except Exception:
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    n = min(len(satirlar), 10)
    uids = [int(satirlar[i]["discord_id"]) for i in range(n)]
    urls = await asyncio.gather(*[avatar_url(uid) for uid in uids])

    # Üst başlık
    baslik = "M2B COIN · TOP 10"
    bbox = draw.textbbox((0, 0), baslik, font=f_baslik)
    bw = bbox[2] - bbox[0]
    _tx(draw, ((w - bw) // 2, 10), baslik, f_baslik, (*C_SOLUK, 255))

    ic = w - 2 * MARGIN
    kart_w = (ic - 2 * PODYUM_GAP) // 3
    y0 = UST_BASLIK_H
    vurgu = [C_ALTIN, C_GUM, C_BRONZ]

    for i in range(min(3, n)):
        x0 = MARGIN + i * (kart_w + PODYUM_GAP)
        # İnce üst şerit (sıra vurgusu)
        draw.rounded_rectangle(
            [x0, y0, x0 + kart_w, y0 + PODYUM_KART_H],
            radius=10,
            fill=(*C_YUZEY, 245),
            outline=(*C_KENAR, 200),
            width=1,
        )
        draw.rounded_rectangle(
            [x0, y0, x0 + kart_w, y0 + 3],
            radius=10,
            fill=(*vurgu[i], 255),
        )
        cx = x0 + kart_w // 2
        r_av = 24 if i == 0 else 22 if i == 1 else 20
        boyut = r_av * 2
        ay = y0 + 14
        av = await _indir(urls[i], (boyut, boyut))
        if av:
            m = _yuvarlak_maske(boyut)
            yuv = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
            yuv.paste(av, (0, 0), m)
            im.paste(yuv, (cx - r_av, ay), yuv)
        else:
            draw.ellipse([cx - r_av, ay, cx + r_av, ay + boyut], fill=(*C_YUZEY2, 255))
        draw.ellipse(
            [cx - r_av - 1, ay - 1, cx + r_av + 1, ay + boyut + 1],
            outline=(*vurgu[i], 180),
            width=1,
        )

        isim = _metin_guvenli(str(satirlar[i]["username"]), 14)
        skor = f"{int(satirlar[i]['bakiye']):,}"
        iy = ay + boyut + 6
        _tx_orta(draw, cx, iy, isim, f_podyum_isim, (*C_METIN, 255))
        _tx_orta(draw, cx, iy + 17, skor, f_podyum_skor, (*C_ALTIN, 255))

    y_liste = y0 + PODYUM_KART_H + 12
    sol_pad = MARGIN + 10
    rank_w = 36
    av_r = 15
    av_x0 = sol_pad + rank_w + 6
    isim_x = av_x0 + av_r * 2 + 10
    sag_x = w - MARGIN - 12
    max_isim = sag_x - isim_x - 56

    for j in range(3, n):
        idx = j - 3
        row = satirlar[j]
        ry = y_liste + idx * (LISTE_SATIR_H + LISTE_GAP)
        zeb = idx % 2
        yuz = C_YUZEY if zeb == 0 else C_YUZEY2

        draw.rounded_rectangle(
            [MARGIN, ry, w - MARGIN, ry + LISTE_SATIR_H],
            radius=8,
            fill=(*yuz, 238),
            outline=(*C_KENAR, 120),
            width=1,
        )

        rno = str(j + 1)
        bb = draw.textbbox((0, 0), rno, font=f_sira)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        rcx = sol_pad + (rank_w - tw) // 2
        rcy = ry + (LISTE_SATIR_H - th) // 2
        _tx(draw, (rcx, rcy), rno, f_sira, (*C_SOLUK, 255))

        cx = av_x0 + av_r
        cy = ry + LISTE_SATIR_H // 2
        b = av_r * 2
        av = await _indir(urls[j], (b, b))
        if av:
            m = _yuvarlak_maske(b)
            yuv = Image.new("RGBA", (b, b), (0, 0, 0, 0))
            yuv.paste(av, (0, 0), m)
            im.paste(yuv, (cx - av_r, cy - av_r), yuv)
        else:
            draw.ellipse([cx - av_r, cy - av_r, cx + av_r, cy + av_r], fill=(*C_KENAR, 200))

        isim = _metin_guvenli(str(row["username"]), 40)
        isim = _kisalt_genislik(draw, f_satir_isim, isim, max_isim)
        bb_i = draw.textbbox((0, 0), isim, font=f_satir_isim)
        ih = bb_i[3] - bb_i[1]
        iy = ry + (LISTE_SATIR_H - ih) // 2
        _tx(draw, (isim_x, iy), isim, f_satir_isim, (*C_METIN, 255))

        skor = f"{int(row['bakiye']):,}"
        # Skor: küçük “chip” arka planı
        sw = draw.textbbox((0, 0), skor, font=f_satir_skor)[2] - draw.textbbox((0, 0), skor, font=f_satir_skor)[0]
        chip_pad = 6
        chip_x1 = sag_x - sw - chip_pad * 2
        chip_y1 = ry + (LISTE_SATIR_H - 22) // 2
        chip_x2 = sag_x
        chip_y2 = chip_y1 + 22
        draw.rounded_rectangle(
            [chip_x1, chip_y1, chip_x2, chip_y2],
            radius=6,
            fill=(15, 23, 42, 200),
            outline=(*C_KENAR, 100),
            width=1,
        )
        _tx_sag(draw, sag_x - chip_pad, cy, skor, f_satir_skor, (*C_ALTIN, 255))

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli (UI v%s, kullanıcı=%s)", GORSEL_SURUM, n)
    return buf
