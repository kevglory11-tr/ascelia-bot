"""
utils/siralama_gorseli.py — Olimpik podyum (sol 2., orta 1., sağ 3.), gradyan kademeler.

assets/siralama_arka.png — opsiyonel arka plan.
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

GORSEL_SURUM = 9

_PROJE_KOK = Path(__file__).resolve().parent.parent
ARKA_YOLU = _PROJE_KOK / "assets" / "siralama_arka.png"
_BOT_FONT = _PROJE_KOK / "assets" / "font.ttf"

GENISLIK = 760
YUKSEKLIK = 556

MARGIN = 26
PODYUM_GAP = 10
PODYUM_BASE_Y = 262
KAVIS = 16

ALTIN_UST = (255, 218, 105)
ALTIN_ALT = (175, 125, 38)
GUM_UST = (228, 234, 244)
GUM_ALT = (128, 138, 156)
BRONZ_UST = (212, 162, 108)
BRONZ_ALT = (125, 78, 42)

C_METIN = (248, 250, 252)
C_KOYU = (15, 23, 42)
C_SOLUK = (148, 163, 184)
C_LISTE_BG = (18, 24, 38, 245)
C_AYIRICI = (55, 65, 85)

FONT_ISIM = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\seguiemj.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

FONT_KALIN = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
if _BOT_FONT.is_file():
    FONT_KALIN.insert(0, str(_BOT_FONT))


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for yol in paths:
        if os.path.exists(yol):
            try:
                return ImageFont.truetype(yol, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _yuvarlak_maske(n: int) -> Image.Image:
    m = Image.new("L", (n, n), 0)
    ImageDraw.Draw(m).ellipse((0, 0, n, n), fill=255)
    return m


def _gradyan_kademe(w: int, h: int, r: int, c_ust: tuple, c_alt: tuple) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        rr = int(c_ust[0] + t * (c_alt[0] - c_ust[0]))
        gg = int(c_ust[1] + t * (c_alt[1] - c_ust[1]))
        bb = int(c_ust[2] + t * (c_alt[2] - c_ust[2]))
        for x in range(w):
            px[x, y] = (rr, gg, bb, 255)
    maske = Image.new("L", (w, h), 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, w, h), radius=r, fill=255)
    img.putalpha(maske)
    return img


def _arka_derin(w: int, h: int) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    px = img.load()
    cx, cy = w * 0.5, h * 0.32
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / w
            dy = (y - cy) / h
            v = 0.5 + 0.5 * (dx * dx + dy * dy) ** 0.45
            px[x, y] = (int(7 + v * 14), int(9 + v * 16), int(20 + v * 24), 255)
    return img


def _arka_hazirla(w: int, h: int) -> Image.Image:
    if ARKA_YOLU.is_file():
        try:
            return Image.open(ARKA_YOLU).convert("RGBA").resize((w, h), Image.LANCZOS)
        except Exception as e:
            log.warning("siralama_arka.png: %s", e)
    return _arka_derin(w, h)


def _vignette(im: Image.Image) -> Image.Image:
    if ARKA_YOLU.is_file():
        f = Image.new("RGBA", im.size, (0, 0, 0, 105))
        return Image.alpha_composite(im, f)
    return im


async def _indir(url: str, boyut: tuple[int, int]) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                return Image.open(io.BytesIO(data)).convert("RGBA").resize(boyut, Image.LANCZOS)
    except Exception:
        return None


def _metin_guvenli(s: str, max_len: int = 26) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.strip())
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _kisalt_genislik(draw, font, metin: str, max_w: int) -> str:
    if not metin:
        return metin
    if draw.textbbox((0, 0), metin, font=font)[2] - draw.textbbox((0, 0), metin, font=font)[0] <= max_w:
        return metin
    k = metin
    while len(k) > 1:
        d = k[:-1] + "…"
        ww = draw.textbbox((0, 0), d, font=font)[2] - draw.textbbox((0, 0), d, font=font)[0]
        if ww <= max_w:
            return d
        k = k[:-1]
    return "…"


def _golge(im: Image.Image, x: int, y: int, w: int, h: int, r: int) -> None:
    s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((0, 0, w, h), radius=r, fill=(0, 0, 0, 100))
    im.paste(s, (x + 5, y + 6), s)


def _orta(draw, cx: int, y: int, t: str, font, fill):
    bb = draw.textbbox((0, 0), t, font=font)
    draw.text((cx - (bb[2] - bb[0]) // 2, y), t, font=font, fill=fill)


def _sag(draw, rx: int, cy: int, t: str, font, fill):
    bb = draw.textbbox((0, 0), t, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((rx - w, cy - h // 2), t, font=font, fill=fill)


async def siralama_gorseli_olustur(bot, satirlar: list) -> io.BytesIO:
    w, h = GENISLIK, YUKSEKLIK
    im = _arka_hazirla(w, h)
    im = _vignette(im)
    draw = ImageDraw.Draw(im)

    f_bas = _font(FONT_KALIN, 10)
    f_etik = _font(FONT_KALIN, 9)
    f_ip = _font(FONT_ISIM, 13)
    f_sp = _font(FONT_KALIN, 12)
    f_il = _font(FONT_ISIM, 12)
    f_sl = _font(FONT_KALIN, 11)
    f_sira = _font(FONT_KALIN, 11)
    f_rozet = _font(FONT_KALIN, 20)

    async def avatar_url(uid: int) -> str:
        try:
            u = await bot.fetch_user(uid)
            return u.display_avatar.url
        except Exception:
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    n = min(len(satirlar), 10)
    uids = [int(satirlar[i]["discord_id"]) for i in range(n)]
    urls = await asyncio.gather(*[avatar_url(uid) for uid in uids])

    bt = "M2B COIN  ·  EN İYİLER"
    bb = draw.textbbox((0, 0), bt, font=f_bas)
    draw.text(((w - (bb[2] - bb[0])) // 2, 14), bt, font=f_bas, fill=(*C_SOLUK, 255))

    ic = w - 2 * MARGIN
    ara = 2 * PODYUM_GAP
    blok = ic - ara
    w_sol, w_orta, w_sag = 200, 268, 200
    if w_sol + w_orta + w_sag != blok:
        w_orta = blok - w_sol - w_sag
    x_sol = MARGIN
    x_orta = x_sol + w_sol + PODYUM_GAP
    x_sag = x_orta + w_orta + PODYUM_GAP

    h_orta, h_sol, h_sag = 168, 148, 138
    base = PODYUM_BASE_Y

    # Merkez parıltı
    glow = Image.new("RGBA", (w_orta + 100, h_orta + 80), (0, 0, 0, 0))
    gpx = glow.load()
    gcx, gcy = (w_orta + 100) // 2, (h_orta + 80) // 2
    for gy in range(h_orta + 80):
        for gx in range(w_orta + 100):
            d = ((gx - gcx) ** 2 + (gy - gcy) ** 2) ** 0.5 / (w_orta * 0.9)
            a = max(0, int(50 - d * 85))
            if a:
                gpx[gx, gy] = (255, 210, 90, a)
    im.paste(glow, (x_orta - 50, base - h_orta - 12), glow)

    # (sıra, x, genişlik, yükseklik, gradyan, veri index, etiket, skor_renk)
    podyum = [
        ("sol", x_sol, w_sol, h_sol, GUM_UST, GUM_ALT, 1, "İKİNCİ", (35, 45, 65)),
        ("sag", x_sag, w_sag, h_sag, BRONZ_UST, BRONZ_ALT, 2, "ÜÇÜNCÜ", (55, 40, 25)),
        ("orta", x_orta, w_orta, h_orta, ALTIN_UST, ALTIN_ALT, 0, "ŞAMPİYON", (62, 38, 8)),
    ]

    for _, x0, ww, hh, cu, ca, vi, etik, sk_col in podyum:
        if vi >= n:
            continue
        y0 = base - hh
        _golge(im, x0, y0, ww, hh, KAVIS)
        tab = _gradyan_kademe(ww, hh, KAVIS, cu, ca)
        parlak = Image.new("RGBA", (ww, 4), (0, 0, 0, 0))
        cl = tuple(min(255, c + 48) for c in cu)
        ImageDraw.Draw(parlak).rectangle((0, 0, ww, 4), fill=(*cl, 230))
        tab.alpha_composite(parlak, (0, 0))
        im.paste(tab, (x0, y0), tab)

        cx = x0 + ww // 2
        rb = 17
        ry0 = y0 + 10
        rz = Image.new("RGBA", (rb * 2, rb * 2), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rz)
        rd.ellipse((0, 0, rb * 2, rb * 2), fill=(*C_KOYU, 245))
        rd.ellipse((0, 0, rb * 2, rb * 2), outline=(*cu, 255), width=2)
        im.paste(rz, (cx - rb, ry0), rz)
        rk = str(vi + 1)
        bbr = draw.textbbox((0, 0), rk, font=f_rozet)
        draw.text(
            (cx - (bbr[2] - bbr[0]) // 2, ry0 + rb - (bbr[3] - bbr[1]) // 2 - 1),
            rk,
            font=f_rozet,
            fill=(*C_METIN, 255),
        )

        _orta(draw, cx, y0 + 46, etik, f_etik, (*C_KOYU, 255))

        r_av = 32 if vi == 0 else 26 if vi == 1 else 25
        av_y = y0 + 66
        boy = r_av * 2
        av = await _indir(urls[vi], (boy, boy))
        if av:
            m = _yuvarlak_maske(boy)
            yu = Image.new("RGBA", (boy, boy), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx - r_av, av_y), yu)
        else:
            draw.ellipse([cx - r_av, av_y, cx + r_av, av_y + boy], fill=(38, 46, 62, 255))
        draw.ellipse(
            [cx - r_av - 2, av_y - 2, cx + r_av + 2, av_y + boy + 2],
            outline=(*cu, 240),
            width=2,
        )

        isim = _metin_guvenli(str(satirlar[vi]["username"]), 16)
        sk = f"{int(satirlar[vi]['bakiye']):,}"
        ty = av_y + boy + 7
        _orta(draw, cx, ty, isim, f_ip, (*C_KOYU, 255))
        _orta(draw, cx, ty + 19, sk, f_sp, (*sk_col, 255))

    # —— 4–10: tek panel, ince ayırıcı ——
    yp = base + 18
    y_alt = h - MARGIN
    draw.rounded_rectangle(
        [MARGIN, yp, w - MARGIN, y_alt],
        radius=18,
        fill=C_LISTE_BG,
    )
    # İç kenar ışığı
    draw.rounded_rectangle(
        [MARGIN, yp, w - MARGIN, y_alt],
        radius=18,
        outline=(90, 100, 130, 120),
        width=1,
    )

    satir_h = 36
    gap_i = 1
    sol0 = MARGIN + 14
    rank_w = 32
    av_r = 14
    av_x0 = sol0 + rank_w + 8
    isim_x = av_x0 + av_r * 2 + 10
    sag_x = w - MARGIN - 16
    max_i = sag_x - isim_x - 52

    for j in range(3, n):
        idx = j - 3
        ry = yp + 12 + idx * (satir_h + gap_i)
        if ry + satir_h > y_alt - 8:
            break
        if idx > 0:
            ly = ry - gap_i // 2
            draw.line([(MARGIN + 16, ly), (w - MARGIN - 16, ly)], fill=(*C_AYIRICI, 160), width=1)

        rno = str(j + 1)
        bb = draw.textbbox((0, 0), rno, font=f_sira)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        rcx = sol0 + (rank_w - tw) // 2
        rcy = ry + (satir_h - th) // 2
        draw.text((rcx, rcy), rno, font=f_sira, fill=(*C_SOLUK, 255))

        cx = av_x0 + av_r
        cy = ry + satir_h // 2
        b = av_r * 2
        av = await _indir(urls[j], (b, b))
        if av:
            m = _yuvarlak_maske(b)
            yu = Image.new("RGBA", (b, b), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx - av_r, cy - av_r), yu)
        else:
            draw.ellipse([cx - av_r, cy - av_r, cx + av_r, cy + av_r], fill=(55, 62, 78, 255))

        isim = _metin_guvenli(str(satirlar[j]["username"]), 40)
        isim = _kisalt_genislik(draw, f_il, isim, max_i)
        bb_i = draw.textbbox((0, 0), isim, font=f_il)
        ih = bb_i[3] - bb_i[1]
        draw.text((isim_x, ry + (satir_h - ih) // 2), isim, font=f_il, fill=(*C_METIN, 255))

        sk = f"{int(satirlar[j]['bakiye']):,}"
        _sag(draw, sag_x, cy, sk, f_sl, (245, 200, 90, 255))

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli (podyum v%s, kullanıcı=%s)", GORSEL_SURUM, n)
    return buf
