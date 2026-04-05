"""
utils/siralama_gorseli.py — M2B Coin Sıralama Görseli (v4)
Tasarım: Mobile leaderboard stili — büyük avatarlar, taç, koyu minimal tema.
"""
from __future__ import annotations

import io, os, re, asyncio
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from utils.logger import setup_logger

log = setup_logger("siralama_gorseli")

GORSEL_SURUM = 14

_KOK      = Path(__file__).resolve().parent.parent
ARKA_YOLU = _KOK / "assets" / "siralama_arka.png"
_BOT_FONT = _KOK / "assets" / "font.ttf"

# ── Tuval ───────────────────────────────────────────────────────
W = 720
H = 590

# ── Renkler ─────────────────────────────────────────────────────
BG         = (11, 13, 26)
BG_TOP3    = (18, 22, 44, 210)
BG_LIST    = (15, 19, 38, 245)
C_METIN    = (232, 238, 255)
C_SOLUK    = (105, 122, 165)
C_SEP      = (32, 44, 80)
ALTIN      = (255, 210, 48)
ALTIN_DRK  = (190, 145, 15)

# Top-3 ring + skor renkleri
_T3 = [
    ((255, 210, 48),  (255, 220, 80)),   # 1. altın
    ((100, 135, 255), (130, 165, 255)),  # 2. mavi
    ((48,  210, 138), (72,  228, 158)),  # 3. yeşil
]

# Liste satır ring renkleri (4-10)
_LR = [
    (255, 210, 48),   # 4
    (100, 135, 255),  # 5
    (48,  210, 138),  # 6
    (175, 120, 255),  # 7
    (255, 148, 72),   # 8
    (72,  205, 225),  # 9
    (175, 175, 175),  # 10
]

MARGIN = 22

# Top-3 düzeni (x_merkez, av_r, av_üst)
_TOP3_POS = [
    (W // 2, 52, 90),    # 1. merkez — büyük
    (168,    38, 112),   # 2. sol
    (W-168,  38, 112),   # 3. sağ
]

LIST_Y    = 292
ROW_H     = 36
ROW_GAP   = 2
LIST_ROWS = 7
_LIST_H   = 14 + LIST_ROWS * ROW_H + (LIST_ROWS - 1) * ROW_GAP + 16

# ── Font listeleri ───────────────────────────────────────────────
_FI = [r"C:\Windows\Fonts\segoeui.ttf",
       "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_FB = [r"C:\Windows\Fonts\segoeuib.ttf",
       r"C:\Windows\Fonts\arialbd.ttf",
       "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
if _BOT_FONT.is_file():
    _FB.insert(0, str(_BOT_FONT))
_FM = [r"C:\Windows\Fonts\consola.ttf",
       r"C:\Windows\Fonts\cour.ttf",
       "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
       "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]


def _f(paths, size):
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()


# ── Yardımcılar ─────────────────────────────────────────────────

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


def _temizle(s, mx=28):
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.strip())
    return s if len(s) <= mx else s[:mx - 1] + "…"


async def _indir(url, boyut):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status != 200: return None
                return Image.open(io.BytesIO(await r.read())).convert("RGBA").resize(boyut, Image.LANCZOS)
    except: return None


def _cx(draw, cx, y, t, font, fill, shadow=None):
    w, _ = _wh(draw, t, font)
    x = cx - w // 2
    if shadow: draw.text((x + 1, y + 1), t, font=font, fill=shadow)
    draw.text((x, y), t, font=font, fill=fill)


def _rx(draw, rx, cy, t, font, fill, shadow=None):
    tw, th = _wh(draw, t, font)
    x, y = rx - tw, cy - th // 2
    if shadow: draw.text((x + 1, y + 1), t, font=font, fill=shadow)
    draw.text((x, y), t, font=font, fill=fill)


def _overlay(im, fn):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(ov))
    im.alpha_composite(ov)


def _tac(draw, cx, y, renk):
    """Altın taç — 3 tepe, orta daha yüksek."""
    w, h = 38, 20
    half = w // 2
    polys = []
    for i in range(3):
        bx     = cx - half + (i + 0.5) * (w / 3)
        tepe_y = y + (0 if i == 1 else 5)
        polys += [(bx - 5, y + h), (bx, tepe_y), (bx + 5, y + h)]
    draw.polygon(polys, fill=(*renk[:3], 255), outline=(135, 85, 10, 210))
    # Taç tabanı
    draw.rectangle([cx - half, y + h - 3, cx + half, y + h], fill=(*renk[:3], 200))


def _arka():
    if ARKA_YOLU.is_file():
        try:
            return Image.open(ARKA_YOLU).convert("RGBA").resize((W, H), Image.LANCZOS)
        except Exception as e:
            log.warning("siralama_arka.png: %s", e)
    img = Image.new("RGBA", (W, H))
    px  = img.load()
    for y in range(H):
        for x in range(W):
            t  = y / H
            r  = int(BG[0] + t * 5)
            g  = int(BG[1] + t * 4)
            b  = int(BG[2] + t * 8)
            px[x, y] = (min(255, r), min(255, g), min(255, b), 255)
    return img


async def siralama_gorseli_olustur(bot, satirlar):
    n = min(len(satirlar), 10)

    async def av_url(uid):
        try:
            u = await bot.fetch_user(int(uid))
            return u.display_avatar.url
        except: return "https://cdn.discordapp.com/embed/avatars/0.png"

    urls = await asyncio.gather(*[av_url(satirlar[i]["discord_id"]) for i in range(n)])

    im   = _arka()
    draw = ImageDraw.Draw(im)

    fB22 = _f(_FB, 22)
    fB18 = _f(_FB, 18)
    fB15 = _f(_FB, 15)
    fB14 = _f(_FB, 14)
    fB12 = _f(_FB, 12)
    fI16 = _f(_FI, 16)
    fI14 = _f(_FI, 14)
    fI11 = _f(_FI, 11)
    fI10 = _f(_FI, 10)
    fM14 = _f(_FM, 14)

    # ── Başlık ──────────────────────────────────────────────────
    _cx(draw, W // 2, 12, "M2B COIN SIRALAMASI", fB22, (*ALTIN, 255), shadow=(*ALTIN_DRK, 185))

    def _hline(d):
        for i in range(W - 2 * MARGIN):
            t = i / (W - 2 * MARGIN - 1)
            a = max(0, int(220 * (1 - abs(t - 0.5) * 2.2)))
            r = int(175 + t * 75)
            g = int(130 + t * 70)
            b = int(18 + t * 40)
            d.line([(MARGIN + i, 46), (MARGIN + i, 48)], fill=(r, g, b, a))
    _overlay(im, _hline)

    # ── Top 3 arka panel ────────────────────────────────────────
    def _top_bg(d):
        d.rounded_rectangle([MARGIN, 52, W - MARGIN, LIST_Y - 6],
                             radius=20, fill=BG_TOP3)
    _overlay(im, _top_bg)

    # ── Top 3 avatarlar ─────────────────────────────────────────
    for vi, (cx, av_r, av_top) in enumerate(_TOP3_POS):
        if vi >= n:
            continue
        ring_c, score_c = _T3[vi]
        av_d   = av_r * 2
        av_bot = av_top + av_d
        fi     = fB14 if vi == 0 else fB12
        fs     = fB18 if vi == 0 else fB15

        # Taç (sadece 1. için)
        if vi == 0:
            _tac(draw, cx, av_top - 22, ALTIN)

        # Avatar aura (hafif renkli ışıma)
        def _aura(d, _cx=cx, _r=av_r, _at=av_top, _d=av_d, _rc=ring_c):
            for i in range(6, 0, -1):
                d.ellipse([_cx - _r - i*2, _at - i*2,
                           _cx + _r + i*2, _at + _d + i*2],
                          fill=(*_rc[:3], i * 6))
        _overlay(im, _aura)

        # Avatar
        av = await _indir(urls[vi], (av_d, av_d))
        if av:
            m  = _daire(av_d)
            yu = Image.new("RGBA", (av_d, av_d), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx - av_r, av_top), yu)
        else:
            draw.ellipse([cx - av_r, av_top, cx + av_r, av_bot], fill=(26, 34, 65, 255))

        # Ring
        def _ring(d, _cx=cx, _r=av_r, _at=av_top, _d=av_d, _rc=ring_c):
            d.ellipse([_cx-_r-4, _at-4, _cx+_r+4, _at+_d+4],
                      outline=(8, 12, 28, 220), width=4)
            d.ellipse([_cx-_r-2, _at-2, _cx+_r+2, _at+_d+2],
                      outline=(*_rc[:3], 230), width=2)
        _overlay(im, _ring)

        # İsim
        isim   = _temizle(str(satirlar[vi]["username"]), 14 if vi == 0 else 11)
        isim_y = av_bot + 10
        _cx(draw, cx, isim_y, isim, fi, (*C_METIN, 255))

        # Skor
        _, ih  = _wh(draw, isim, fi)
        skor_y = isim_y + ih + 5
        skor   = f"{int(satirlar[vi]['bakiye']):,}"
        _cx(draw, cx, skor_y, skor, fs, (*score_c, 255),
            shadow=(*ALTIN_DRK, 160) if vi == 0 else None)

        # @handle
        _, sh   = _wh(draw, skor, fs)
        hand_y  = skor_y + sh + 4
        handle  = "@" + _temizle(str(satirlar[vi]["username"]), 12).lower()
        _cx(draw, cx, hand_y, handle, fI10, (*C_SOLUK, 185))

    # ── Liste ───────────────────────────────────────────────────
    list_bot = LIST_Y + _LIST_H

    def _lp(d):
        d.rounded_rectangle([MARGIN, LIST_Y, W - MARGIN, list_bot],
                             radius=18, fill=BG_LIST)
        d.rounded_rectangle([MARGIN, LIST_Y, W - MARGIN, list_bot],
                             radius=18, outline=(*C_SEP, 110), width=1)
    _overlay(im, _lp)

    rank_rx = MARGIN + 30    # rank sayısı sağ kenarı
    av_lx   = rank_rx + 10  # avatar sol
    av_r_l  = 20
    isim_x  = av_lx + av_r_l * 2 + 12
    sag_x   = W - MARGIN - 16
    max_iw  = sag_x - isim_x - 72

    for j in range(3, n):
        idx  = j - 3
        ry   = LIST_Y + 14 + idx * (ROW_H + ROW_GAP)
        cy   = ry + ROW_H // 2
        rc   = _LR[idx]

        # Satır ayırıcı
        if idx > 0:
            def _rsep(d, _ly=ry - 1):
                d.line([(MARGIN + 16, _ly), (W - MARGIN - 16, _ly)],
                       fill=(*C_SEP, 65), width=1)
            _overlay(im, _rsep)

        # Rank numarası (sağa yaslı, soluk)
        rno    = str(j + 1)
        rno_w, rno_h = _wh(draw, rno, fB14)
        draw.text((rank_rx - rno_w, cy - rno_h // 2), rno, font=fB14, fill=(*C_SOLUK, 190))

        # Avatar
        cx_av = av_lx + av_r_l
        av_d  = av_r_l * 2
        av    = await _indir(urls[j], (av_d, av_d))
        if av:
            m  = _daire(av_d)
            yu = Image.new("RGBA", (av_d, av_d), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx_av - av_r_l, cy - av_r_l), yu)
        else:
            draw.ellipse([cx_av - av_r_l, cy - av_r_l, cx_av + av_r_l, cy + av_r_l],
                         fill=(34, 44, 75, 255))

        # Avatar ring
        def _lr(d, _cx=cx_av, _r=av_r_l, _cy=cy, _rc=rc):
            d.ellipse([_cx-_r-2, _cy-_r-2, _cx+_r+2, _cy+_r+2],
                      outline=(*_rc[:3], 175), width=2)
        _overlay(im, _lr)

        # İsim + @handle (dikey ortalanmış)
        isim   = _kisalt(draw, fI16, _temizle(str(satirlar[j]["username"])), max_iw)
        handle = "@" + _temizle(str(satirlar[j]["username"]), 16).lower()
        _, ih  = _wh(draw, isim, fI16)
        _, hh  = _wh(draw, handle, fI10)
        total  = ih + 3 + hh
        ny     = cy - total // 2
        hy     = ny + ih + 3
        draw.text((isim_x, ny), isim,   font=fI16, fill=(*C_METIN, 255))
        draw.text((isim_x, hy), handle, font=fI10, fill=(*C_SOLUK, 175))

        # Skor
        skor = f"{int(satirlar[j]['bakiye']):,}"
        _rx(draw, sag_x, cy, skor, fM14, (*C_METIN, 255))

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli v%s — %d kişi, %dx%d", GORSEL_SURUM, n, W, H)
    return buf
