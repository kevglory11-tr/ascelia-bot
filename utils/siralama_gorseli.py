"""
utils/siralama_gorseli.py — M2B Coin Sıralama Görseli (v2)
Tasarım: Koyu premium tema, olimpik podyum + TOP 10 listesi.
"""
from __future__ import annotations

import io, os, re, asyncio
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from utils.logger import setup_logger

log = setup_logger("siralama_gorseli")

GORSEL_SURUM = 12

_KOK      = Path(__file__).resolve().parent.parent
ARKA_YOLU = _KOK / "assets" / "siralama_arka.png"
_BOT_FONT = _KOK / "assets" / "font.ttf"

# ── Tuval ────────────────────────────────────────────────────────
W = 840

POD_BASE_Y = 356          # podyum ortak alt kenar

GOLD_W, GOLD_H = 374, 268
SIL_W,  SIL_H  = 210, 228
BRZ_W,  BRZ_H  = 210, 210

MARGIN = 18

GOLD_X = (W - GOLD_W) // 2   # 233
SIL_X  = MARGIN               # 18
BRZ_X  = W - MARGIN - BRZ_W  # 612

GOLD_Y = POD_BASE_Y - GOLD_H  # 88
SIL_Y  = POD_BASE_Y - SIL_H   # 128
BRZ_Y  = POD_BASE_Y - BRZ_H   # 146

LIST_Y     = 368
LIST_ROW_H = 25
LIST_GAP   = 3
LIST_ROWS  = 7
_LIST_H    = 12 + LIST_ROWS * LIST_ROW_H + (LIST_ROWS - 1) * LIST_GAP + 12  # 217

H = LIST_Y + _LIST_H + 14   # 599

# ── Renkler ──────────────────────────────────────────────────────
C_METIN     = (242, 246, 255)
C_SOLUK     = (138, 155, 192)
C_SEP       = (50, 65, 108)
C_PANEL     = (12, 18, 42, 244)

ALTIN_UST   = (255, 234, 118)
ALTIN_ALT   = (148, 92, 14)
ALTIN_YAZ   = (255, 222, 68)
ALTIN_GOLGE = (90, 58, 8)

GUMUS_UST   = (238, 246, 255)
GUMUS_ALT   = (90, 102, 130)
GUMUS_YAZ   = (198, 215, 238)

BRONZ_UST   = (228, 166, 95)
BRONZ_ALT   = (112, 62, 28)
BRONZ_YAZ   = (212, 148, 76)

# ── Font listeleri ───────────────────────────────────────────────
_FI = [
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FB = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
if _BOT_FONT.is_file():
    _FB.insert(0, str(_BOT_FONT))

_FM = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _f(paths, size):
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Yardımcılar ──────────────────────────────────────────────────

def _wh(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def _daire(n):
    m = Image.new("L", (n, n), 0)
    ImageDraw.Draw(m).ellipse((0, 0, n, n), fill=255)
    return m


def _kisalt(draw, font, metin, max_w):
    if _wh(draw, metin, font)[0] <= max_w:
        return metin
    while len(metin) > 1:
        k = metin[:-1] + "…"
        if _wh(draw, k, font)[0] <= max_w:
            return k
        metin = metin[:-1]
    return "…"


def _temizle(s, mx=32):
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.strip())
    return s if len(s) <= mx else s[:mx - 1] + "…"


async def _indir(url, boyut):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status != 200:
                    return None
                return Image.open(io.BytesIO(await r.read())).convert("RGBA").resize(boyut, Image.LANCZOS)
    except Exception:
        return None


def _cx(draw, cx, y, t, font, fill, shadow=None):
    w, _ = _wh(draw, t, font)
    x = cx - w // 2
    if shadow:
        draw.text((x + 1, y + 1), t, font=font, fill=shadow)
    draw.text((x, y), t, font=font, fill=fill)


def _rx(draw, rx, cy, t, font, fill, shadow=None):
    tw, th = _wh(draw, t, font)
    x, y = rx - tw, cy - th // 2
    if shadow:
        draw.text((x + 1, y + 1), t, font=font, fill=shadow)
    draw.text((x, y), t, font=font, fill=fill)


def _overlay(im, fn):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(ov))
    im.alpha_composite(ov)


def _gradyan(w, h, r, c_ust, c_alt, sicak=False):
    img = Image.new("RGBA", (w, h))
    px  = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        for x in range(w):
            rv = int(c_ust[0] + t * (c_alt[0] - c_ust[0]))
            gv = int(c_ust[1] + t * (c_alt[1] - c_ust[1]))
            bv = int(c_ust[2] + t * (c_alt[2] - c_ust[2]))
            ux  = x / max(w - 1, 1)
            ust = max(0.0, 1.0 - y / (h * 0.40))
            p   = ust * (0.55 - 0.50 * abs(ux - 0.5) * 2)
            if sicak:
                rv = min(255, int(rv + p * 62))
                gv = min(255, int(gv + p * 50))
                bv = min(255, int(bv + p * 16))
            else:
                rv = min(255, int(rv + p * 44))
                gv = min(255, int(gv + p * 48))
                bv = min(255, int(bv + p * 40))
            px[x, y] = (rv, gv, bv, 255)
    maske = Image.new("L", (w, h), 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, w, h), radius=r, fill=255)
    img.putalpha(maske)
    return img


def _arka():
    if ARKA_YOLU.is_file():
        try:
            return Image.open(ARKA_YOLU).convert("RGBA").resize((W, H), Image.LANCZOS)
        except Exception as e:
            log.warning("siralama_arka.png: %s", e)
    img = Image.new("RGBA", (W, H))
    px  = img.load()
    cx, cy = W * 0.5, H * 0.22
    for y in range(H):
        for x in range(W):
            dx = (x - cx) / W
            dy = (y - cy) / H
            d  = (dx * dx + dy * dy) ** 0.5
            k  = 0.38 + 0.62 * min(1.0, d * 1.30)
            sp = max(0.0, 0.52 - d * 1.08)
            r  = int(5 + k * 16 + sp * 42)
            g  = int(7 + k * 14 + sp * 34)
            b  = int(18 + k * 20 + sp * 12)
            px[x, y] = (r, g, b, 255)
    return img


def _tac(draw, cx, y0, w, renk):
    half = w // 2
    for i in range(3):
        bx = cx - half + (i + 0.5) * (w / 3)
        draw.polygon(
            [(bx - 6, y0 + 9), (bx, y0), (bx + 6, y0 + 9)],
            fill=(*renk, 255),
            outline=(130, 85, 18, 220),
        )


def _altin_cizgi(draw, cx, y, w):
    x0 = cx - w // 2
    for i in range(w):
        t = i / max(w - 1, 1)
        r = int(175 + t * 72)
        g = int(145 + t * 65)
        b = int(38 + t * 50)
        draw.line([(x0 + i, y), (x0 + i, y + 2)], fill=(r, g, b, 210))


async def siralama_gorseli_olustur(bot, satirlar):
    n = min(len(satirlar), 10)

    async def av_url(uid):
        try:
            u = await bot.fetch_user(int(uid))
            return u.display_avatar.url
        except Exception:
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    urls = await asyncio.gather(*[av_url(satirlar[i]["discord_id"]) for i in range(n)])

    im   = _arka()
    draw = ImageDraw.Draw(im)

    # Fontlar
    fB22 = _f(_FB, 22)
    fI11 = _f(_FI, 11)
    fB11 = _f(_FB, 11)
    fB17 = _f(_FB, 17)
    fB15 = _f(_FB, 15)
    fB13 = _f(_FB, 13)
    fB19 = _f(_FB, 19)
    fB16 = _f(_FB, 16)
    fI13 = _f(_FI, 13)
    fB12 = _f(_FB, 12)
    fM12 = _f(_FM, 12)

    # ── Başlık ───────────────────────────────────────────────────
    _cx(draw, W // 2,  9, "M2B COIN",   fB22, ALTIN_YAZ, shadow=(*ALTIN_GOLGE, 200))
    _cx(draw, W // 2, 35, "SIRALAMASI", fI11, (*C_SOLUK, 255))
    _altin_cizgi(draw, W // 2, 52, 380)

    # ── Podyum arka paneli ───────────────────────────────────────
    def _pod_panel(d):
        d.rounded_rectangle([MARGIN, 60, W - MARGIN, POD_BASE_Y + 8], radius=22, fill=C_PANEL)
        d.rounded_rectangle([MARGIN, 60, W - MARGIN, POD_BASE_Y + 8], radius=22,
                             outline=(88, 78, 130, 88), width=1)
    _overlay(im, _pod_panel)

    # ── Podyum blokları ─────────────────────────────────────────
    # (x, y, w, h, c_ust, c_alt, sicak, vi, etiket, av_r, f_isim, f_skor, f_rozet, c_yaz, c_sk)
    BLOKLAR = [
        (SIL_X,  SIL_Y,  SIL_W,  SIL_H,  GUMUS_UST, GUMUS_ALT, False, 1, "İKİNCİ",   27, fB13, fB15, fB16, (*C_METIN, 255),      (*GUMUS_YAZ, 255)),
        (BRZ_X,  BRZ_Y,  BRZ_W,  BRZ_H,  BRONZ_UST, BRONZ_ALT, False, 2, "ÜÇÜNCÜ",  25, fB13, fB15, fB16, (*C_METIN, 255),      (*BRONZ_YAZ, 255)),
        (GOLD_X, GOLD_Y, GOLD_W, GOLD_H, ALTIN_UST, ALTIN_ALT, True,  0, "ŞAMPİYON", 34, fB15, fB17, fB19, (*ALTIN_GOLGE, 255), (*ALTIN_YAZ, 255)),
    ]

    for x0, y0, bw, bh, cu, ca, sicak, vi, etik, av_r, fi, fs, fr, c_yaz, c_sk in BLOKLAR:
        if vi >= n:
            continue
        cx = x0 + bw // 2

        # Gölge
        for off, a in [((5, 7), 75), ((2, 3), 45)]:
            s = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(s).rounded_rectangle((0, 0, bw, bh), radius=16, fill=(0, 0, 0, a))
            im.alpha_composite(s, (x0 + off[0], y0 + off[1]))

        # Gradyan blok
        tab = _gradyan(bw, bh, 16, cu, ca, sicak)
        # Parlak üst şerit
        pk = Image.new("RGBA", (bw, 3), (0, 0, 0, 0))
        cl = tuple(min(255, c + 55) for c in cu)
        ImageDraw.Draw(pk).rectangle((0, 0, bw, 3), fill=(*cl, 230))
        tab.alpha_composite(pk, (0, 0))
        im.paste(tab, (x0, y0), tab)

        # Çerçeve
        def _frame(d, _x0=x0, _y0=y0, _bw=bw, _bh=bh, _cu=cu, _sicak=sicak):
            d.rounded_rectangle([_x0, _y0, _x0+_bw, _y0+_bh], radius=16, outline=(18, 14, 36, 210), width=2)
            ic = (255, 228, 138, 175) if _sicak else (198, 212, 232, 125)
            d.rounded_rectangle([_x0+2, _y0+2, _x0+_bw-2, _y0+_bh-2], radius=14, outline=ic, width=1)
        _overlay(im, _frame)

        # Taç (1. için bloğun üstünde)
        if vi == 0:
            _tac(draw, cx, y0 - 17, 70, (255, 210, 68))

        # Sıra rozeti
        rb  = 16 if vi == 0 else 14
        ry0 = y0 + 14
        ri  = Image.new("RGBA", (rb * 2, rb * 2), (0, 0, 0, 0))
        rd  = ImageDraw.Draw(ri)
        rd.ellipse((0, 0, rb*2, rb*2), fill=(8, 12, 28, 238))
        rd.ellipse((0, 0, rb*2, rb*2), outline=(*cu, 255), width=2)
        im.paste(ri, (cx - rb, ry0), ri)
        rk = str(vi + 1)
        tw_, th_ = _wh(draw, rk, fr)
        draw.text((cx - tw_ // 2, ry0 + rb - th_ // 2 - 1), rk, font=fr, fill=(*C_METIN, 255))

        # Etiket
        et_y = ry0 + rb * 2 + 5
        _cx(draw, cx, et_y, etik, fB11, (28, 20, 6, 255) if sicak else (18, 28, 48, 255))

        # Avatar
        av_y = et_y + 18
        av_d = av_r * 2
        av   = await _indir(urls[vi], (av_d, av_d))
        if av:
            m  = _daire(av_d)
            yu = Image.new("RGBA", (av_d, av_d), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx - av_r, av_y), yu)
        else:
            draw.ellipse([cx-av_r, av_y, cx+av_r, av_y+av_d], fill=(30, 40, 62, 255))

        def _av_brd(d, _cx=cx, _r=av_r, _y=av_y, _d=av_d, _cu=cu):
            d.ellipse([_cx-_r-3, _y-3, _cx+_r+3, _y+_d+3], outline=(*_cu, 235), width=2)
        _overlay(im, _av_brd)

        # İsim
        isim_y = av_y + av_d + 7
        isim   = _temizle(str(satirlar[vi]["username"]), 18 if vi == 0 else 14)
        _cx(draw, cx, isim_y, isim, fi, c_yaz)

        # Skor
        _, ih  = _wh(draw, isim, fi)
        skor_y = isim_y + ih + 5
        skor   = f"{int(satirlar[vi]['bakiye']):,}"
        _cx(draw, cx, skor_y, skor, fs, c_sk,
            shadow=(*ALTIN_GOLGE, 180) if sicak else (15, 20, 38, 160))

    # ── Liste paneli ─────────────────────────────────────────────
    list_bot = LIST_Y + _LIST_H

    def _liste_panel(d):
        d.rounded_rectangle([MARGIN, LIST_Y, W-MARGIN, list_bot], radius=18, fill=(11, 17, 38, 240))
        d.rounded_rectangle([MARGIN, LIST_Y, W-MARGIN, list_bot], radius=18,
                             outline=(72, 88, 130, 138), width=1)
        d.line([(MARGIN+18, LIST_Y+2), (W-MARGIN-18, LIST_Y+2)], fill=(195, 162, 65, 195), width=2)
    _overlay(im, _liste_panel)

    sol0   = MARGIN + 14
    rank_w = 30
    av_r_l = 11
    av_x0  = sol0 + rank_w + 8
    isim_x = av_x0 + av_r_l * 2 + 9
    sag_x  = W - MARGIN - 16
    max_iw = sag_x - isim_x - 62

    for j in range(3, n):
        idx = j - 3
        ry  = LIST_Y + 12 + idx * (LIST_ROW_H + LIST_GAP)
        cy  = ry + LIST_ROW_H // 2

        if idx > 0:
            def _sep(d, _ly=ry - LIST_GAP // 2 - 1):
                d.line([(MARGIN+16, _ly), (W-MARGIN-16, _ly)], fill=(*C_SEP, 78), width=1)
            _overlay(im, _sep)

        # Sıra no
        rno = str(j + 1)
        tw_, th_ = _wh(draw, rno, fB12)
        draw.text((sol0 + (rank_w - tw_) // 2, cy - th_ // 2), rno, font=fB12, fill=(*C_SOLUK, 255))

        # Avatar
        cx_av = av_x0 + av_r_l
        av_d  = av_r_l * 2
        av    = await _indir(urls[j], (av_d, av_d))
        if av:
            m  = _daire(av_d)
            yu = Image.new("RGBA", (av_d, av_d), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx_av - av_r_l, cy - av_r_l), yu)
        else:
            draw.ellipse([cx_av-av_r_l, cy-av_r_l, cx_av+av_r_l, cy+av_r_l], fill=(40, 52, 78, 255))

        # İsim
        isim = _kisalt(draw, fI13, _temizle(str(satirlar[j]["username"])), max_iw)
        _, th_ = _wh(draw, isim, fI13)
        draw.text((isim_x, cy - th_ // 2), isim, font=fI13, fill=(*C_METIN, 255))

        # Skor
        skor = f"{int(satirlar[j]['bakiye']):,}"
        _rx(draw, sag_x, cy, skor, fM12, (*ALTIN_YAZ, 255), shadow=(*ALTIN_GOLGE, 155))

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli v%s — %d kişi, %dx%d", GORSEL_SURUM, n, W, H)
    return buf
