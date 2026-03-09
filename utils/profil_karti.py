"""
utils/profil_karti.py — Dinamik profil kartı üretici.
PIL/Pillow ile arka plan görseli üzerine kullanıcı bilgilerini çizer.
"""

import io
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import aiohttp
import asyncio
import os

# Font yolları — Railway'de sistem fontları
FONT_YOLLARI = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
]
FONT_NORMAL_YOLLARI = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
]

KART_W  = 900
KART_H  = 300
AVATAR_BOYUT = 110
PANEL_X = 20   # Sol panel başlangıcı
PANEL_W = 260  # Sol panel genişliği


def _font_yukle(boyut: int, kalin: bool = True) -> ImageFont.FreeTypeFont:
    yollar = FONT_YOLLARI if kalin else FONT_NORMAL_YOLLARI
    for yol in yollar:
        if os.path.exists(yol):
            try:
                return ImageFont.truetype(yol, boyut)
            except Exception:
                continue
    return ImageFont.load_default()


async def _gorsel_indir(url: str, boyut: tuple = None) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    img  = Image.open(io.BytesIO(data)).convert("RGBA")
                    if boyut:
                        img = img.resize(boyut, Image.LANCZOS)
                    return img
    except Exception:
        return None


def _yuvarlak_maske(boyut: int) -> Image.Image:
    """Daire şeklinde maske üretir."""
    maske = Image.new("L", (boyut, boyut), 0)
    draw  = ImageDraw.Draw(maske)
    draw.ellipse((0, 0, boyut, boyut), fill=255)
    return maske


def _exp_bar_ciz(draw: ImageDraw.Draw, x: int, y: int, genislik: int, yukseklik: int,
                  exp: int, gereken: int):
    oran  = min(exp / gereken, 1.0)
    dolu  = int(genislik * oran)

    # Arka plan
    draw.rounded_rectangle([x, y, x + genislik, y + yukseklik],
                            radius=yukseklik // 2, fill=(40, 40, 60, 200))
    # Dolu kısım
    if dolu > 0:
        draw.rounded_rectangle([x, y, x + dolu, y + yukseklik],
                                radius=yukseklik // 2, fill=(147, 51, 234, 255))
    # Parlama efekti (üst şerit)
    draw.rounded_rectangle([x + 4, y + 3, x + max(dolu - 4, 4), y + yukseklik // 2],
                            radius=2, fill=(200, 150, 255, 100))


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
) -> io.BytesIO:
    """
    Profil kartı üretir ve BytesIO olarak döndürür.
    Discord'a File olarak gönderilebilir.
    """

    # ── Arka plan ──────────────────────────────────────────
    if arka_plan_url:
        arka = await _gorsel_indir(arka_plan_url, (KART_W, KART_H))
    else:
        arka = None

    if arka is None:
        # Gradient arka plan (fallback)
        try:
            bg_renk = tuple(int(renk_hex[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            bg_renk = (43, 45, 49)
        arka = Image.new("RGBA", (KART_W, KART_H), (*bg_renk, 255))
    else:
        # Sağ tarafı biraz bulanıklaştır (okunaklılık için)
        arka = arka.convert("RGBA")
        blur_bolge = arka.crop((0, 0, KART_W, KART_H))
        blur_bolge = blur_bolge.filter(ImageFilter.GaussianBlur(radius=2))
        # Hafif karartma
        karartma = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 80))
        arka.paste(karartma, (0, 0), karartma)

    kart = arka.copy()
    draw = ImageDraw.Draw(kart)

    # ── Sol yarı saydam panel ──────────────────────────────
    panel = Image.new("RGBA", (PANEL_W + 40, KART_H), (15, 15, 25, 200))
    kart.paste(panel, (0, 0), panel)

    # Panel kenar vurgusu
    draw.line([(PANEL_W + 40, 0), (PANEL_W + 40, KART_H)], fill=(147, 51, 234, 180), width=2)

    # ── Avatar ────────────────────────────────────────────
    avatar = await _gorsel_indir(avatar_url, (AVATAR_BOYUT, AVATAR_BOYUT))
    av_x   = 20
    av_y   = 20

    if avatar:
        avatar = avatar.convert("RGBA")
        # Daire maske
        maske  = _yuvarlak_maske(AVATAR_BOYUT)
        avatar_yuvarlak = Image.new("RGBA", (AVATAR_BOYUT, AVATAR_BOYUT), (0, 0, 0, 0))
        avatar_yuvarlak.paste(avatar, (0, 0), maske)
        # Mor çerçeve
        cerc = Image.new("RGBA", (AVATAR_BOYUT + 6, AVATAR_BOYUT + 6), (0, 0, 0, 0))
        cerc_draw = ImageDraw.Draw(cerc)
        cerc_draw.ellipse((0, 0, AVATAR_BOYUT + 5, AVATAR_BOYUT + 5), fill=(147, 51, 234, 255))
        kart.paste(cerc, (av_x - 3, av_y - 3), cerc)
        kart.paste(avatar_yuvarlak, (av_x, av_y), avatar_yuvarlak)
    else:
        draw.ellipse([av_x, av_y, av_x + AVATAR_BOYUT, av_y + AVATAR_BOYUT],
                     fill=(80, 80, 100, 200))

    # ── Kullanıcı adı ─────────────────────────────────────
    font_buyuk  = _font_yukle(22, kalin=True)
    font_normal = _font_yukle(16, kalin=False)
    font_kucuk  = _font_yukle(13, kalin=False)
    font_sayi   = _font_yukle(20, kalin=True)
    font_etiket = _font_yukle(11, kalin=False)

    isim_x = av_x
    isim_y = av_y + AVATAR_BOYUT + 10
    draw.text((isim_x, isim_y), kullanici_adi[:20], font=font_buyuk, fill=(255, 255, 255, 255))

    # Aktif rozet
    if aktif_rozet:
        rozet_y = isim_y + 28
        draw.text((isim_x, rozet_y), f"🏅 {aktif_rozet[:28]}", font=font_kucuk, fill=(200, 160, 255, 220))
        stat_y = rozet_y + 20
    else:
        stat_y = isim_y + 30

    # ── Sol istatistikler ─────────────────────────────────
    def stat_satir(etiket, deger, y):
        draw.text((isim_x, y),      etiket, font=font_etiket, fill=(160, 160, 180, 200))
        draw.text((isim_x, y + 14), deger,  font=font_sayi,   fill=(255, 255, 255, 255))
        return y + 40

    col2_x = isim_x + 110
    stat_y = max(stat_y, 155)

    # Satır 1 (2 kolon)
    draw.text((isim_x,  stat_y),      "LVL",     font=font_etiket, fill=(160, 160, 180, 200))
    draw.text((isim_x,  stat_y + 14), str(level), font=font_sayi,  fill=(147, 51, 234, 255))
    draw.text((col2_x,  stat_y),      "COINS",   font=font_etiket, fill=(160, 160, 180, 200))
    draw.text((col2_x,  stat_y + 14), f"{bakiye:,}", font=font_sayi, fill=(255, 200, 50, 255))

    # Satır 2
    stat_y += 44
    draw.text((isim_x,  stat_y),      "RANK",    font=font_etiket, fill=(160, 160, 180, 200))
    draw.text((isim_x,  stat_y + 14), f"#{siralama:,}", font=font_sayi, fill=(255, 255, 255, 255))

    # ── Sağ panel: EXP bar + bilgiler ─────────────────────
    sag_x = PANEL_W + 60
    sag_y = 30

    # "TOTAL XP" etiketi
    draw.text((sag_x, sag_y), "TOTAL XP", font=font_etiket, fill=(200, 200, 220, 220))
    draw.text((sag_x, sag_y + 15), f"{exp:,}", font=font_buyuk, fill=(255, 255, 255, 255))

    # EXP progress bar
    bar_y = sag_y + 55
    bar_w = KART_W - sag_x - 30
    _exp_bar_ciz(draw, sag_x, bar_y, bar_w, 22, exp, gereken_exp)

    # Bar altı bilgi
    oran_str = f"{exp:,} / {gereken_exp:,} XP"
    draw.text((sag_x, bar_y + 28), oran_str, font=font_kucuk, fill=(200, 180, 255, 200))

    # Yüzde
    yuzde = int((exp / gereken_exp) * 100) if gereken_exp else 0
    draw.text((sag_x + bar_w - 40, bar_y + 28), f"%{yuzde}", font=font_kucuk, fill=(200, 180, 255, 200))

    # ── Alt süsleme çizgisi ───────────────────────────────
    draw.rectangle([(0, KART_H - 4), (KART_W, KART_H)], fill=(147, 51, 234, 200))

    # ── Çıktı ─────────────────────────────────────────────
    buf = io.BytesIO()
    kart.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
