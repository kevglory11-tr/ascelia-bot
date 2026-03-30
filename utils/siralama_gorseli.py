"""
utils/siralama_gorseli.py — Gösterişli olimpik podyum + TOP 10 listesi (yükseklik dinamik).

assets/siralama_arka.png — opsiyonel; yoksa derin mor–lacivert + spot ışığı.
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

GORSEL_SURUM = 11

_PROJE_KOK = Path(__file__).resolve().parent.parent
ARKA_YOLU = _PROJE_KOK / "assets" / "siralama_arka.png"
_BOT_FONT = _PROJE_KOK / "assets" / "font.ttf"

GENISLIK = 840

PODYUM_GAP = 10
KAVIS = 16
PODYUM_TABAN_Y = 272

# Metalik gradyan uçları (daha canlı)
ALTIN_UST = (255, 232, 140)
ALTIN_ALT = (145, 95, 22)
GUM_UST = (248, 250, 255)
GUM_ALT = (95, 105, 128)
BRONZ_UST = (230, 175, 115)
BRONZ_ALT = (115, 68, 38)

C_KOYU = (12, 18, 35)
C_METIN = (252, 252, 255)
C_SOLUK = (156, 170, 195)
C_ALTIN_YAZI = (120, 72, 12)
C_PANEL = (10, 14, 28, 245)
C_AYIRICI = (70, 82, 108)

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

FONT_SAYI = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


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


def _gradyan_metalik(w: int, h: int, r: int, c_ust: tuple, c_alt: tuple, sicak: bool) -> Image.Image:
    """Dikey gradyan + üstte yatay metal parıltısı."""
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        tv = y / max(h - 1, 1)
        for x in range(w):
            rr = int(c_ust[0] + tv * (c_alt[0] - c_ust[0]))
            gg = int(c_ust[1] + tv * (c_alt[1] - c_ust[1]))
            bb = int(c_ust[2] + tv * (c_alt[2] - c_ust[2]))
            # Üst üçte parlama (merkeze doğru)
            ux = x / max(w - 1, 1)
            ust = max(0.0, 1.0 - y / max(h * 0.42, 1))
            parl = ust * (0.55 - 0.45 * abs(ux - 0.5) * 2)
            rr = min(255, int(rr + parl * (55 if sicak else 40)))
            gg = min(255, int(gg + parl * (45 if sicak else 48)))
            bb = min(255, int(bb + parl * (18 if sicak else 35)))
            px[x, y] = (rr, gg, bb, 255)
    maske = Image.new("L", (w, h), 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, w, h), radius=r, fill=255)
    img.putalpha(maske)
    return img


def _arka_sahne(w: int, h: int) -> Image.Image:
    """Derin lacivert + merkezde sıcak spot (altın tonu)."""
    img = Image.new("RGBA", (w, h))
    px = img.load()
    cx, cy = w * 0.5, h * 0.22
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / w
            dy = (y - cy) / h
            d = (dx * dx + dy * dy) ** 0.5
            koyu = 0.35 + 0.65 * min(1.0, d * 1.35)
            spot = max(0.0, 0.55 - d * 1.1)
            r = int(5 + koyu * 18 + spot * 45)
            g = int(7 + koyu * 16 + spot * 38)
            b = int(18 + koyu * 22 + spot * 12)
            px[x, y] = (r, g, b, 255)
    return img


def _vinyet(im: Image.Image) -> Image.Image:
    w, h = im.size
    v = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vx = v.load()
    for y in range(h):
        for x in range(w):
            t = max(abs(x / w - 0.5), abs(y / h - 0.45)) * 1.85
            a = min(120, int(t * 95))
            if a:
                vx[x, y] = (0, 0, 0, a)
    return Image.alpha_composite(im, v)


def _arka_hazirla(w: int, h: int) -> Image.Image:
    if ARKA_YOLU.is_file():
        try:
            return Image.open(ARKA_YOLU).convert("RGBA").resize((w, h), Image.LANCZOS)
        except Exception as e:
            log.warning("siralama_arka.png: %s", e)
    return _arka_sahne(w, h)


def _film_foto(im: Image.Image) -> Image.Image:
    if not ARKA_YOLU.is_file():
        return im
    f = Image.new("RGBA", im.size, (6, 10, 22, 95))
    return Image.alpha_composite(im, f)


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


def _metin_guvenli(s: str, max_len: int = 28) -> str:
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


def _golge_derin(im: Image.Image, x: int, y: int, w: int, h: int, r: int, opak: int = 110) -> None:
    for i, off in enumerate([(6, 8), (3, 4)]):
        s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        a = opak - i * 35
        ImageDraw.Draw(s).rounded_rectangle((0, 0, w, h), radius=r, fill=(0, 0, 0, a))
        im.paste(s, (x + off[0], y + off[1]), s)


def _parlama_merkez(im: Image.Image, cx: int, cy: int, rw: int, rh: int) -> None:
    g = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    gx, gy = rw // 2, rh // 2
    gp = g.load()
    for y in range(rh):
        for x in range(rw):
            d = (((x - gx) / max(rw, 1)) ** 2 + ((y - gy) / max(rh, 1)) ** 2) ** 0.5
            a = max(0, int(72 - d * 130))
            if a:
                gp[x, y] = (255, 215, 95, a)
    im.paste(g, (cx - rw // 2, cy - rh // 2), g)


def _yazi_parlak(draw: ImageDraw.ImageDraw, cx: int, y: int, t: str, font, ana: tuple, golge: tuple):
    bb = draw.textbbox((0, 0), t, font=font)
    w = bb[2] - bb[0]
    x = cx - w // 2
    draw.text((x + 2, y + 2), t, font=font, fill=(*golge[:3], 200))
    draw.text((x + 1, y + 1), t, font=font, fill=(*golge[:3], 240))
    draw.text((x, y), t, font=font, fill=ana)


def _orta(draw, cx: int, y: int, t: str, font, fill):
    bb = draw.textbbox((0, 0), t, font=font)
    draw.text((cx - (bb[2] - bb[0]) // 2, y), t, font=font, fill=fill)


def _sag(draw, rx: int, cy: int, t: str, font, fill):
    bb = draw.textbbox((0, 0), t, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((rx - w, cy - h // 2), t, font=font, fill=fill)


def _tac_ciz(draw: ImageDraw.ImageDraw, cx: int, tepe_y: int, gen: int, renk: tuple):
    """Basit altın taç — üç tepe."""
    half = gen / 2
    for i in range(3):
        bx = cx - half + (i + 0.5) * (gen / 3)
        draw.polygon(
            [(bx - 7, tepe_y + 9), (bx, tepe_y), (bx + 7, tepe_y + 9)],
            fill=(*renk, 255),
            outline=(160, 100, 30, 255),
        )


def _altin_cizgi(draw: ImageDraw.ImageDraw, cx: int, y: int, w: int) -> None:
    x0 = cx - w // 2
    for i in range(w):
        t = i / max(w - 1, 1)
        r = int(200 + t * 55)
        g = int(170 + t * 50)
        b = int(60 + t * 40)
        draw.line([(x0 + i, y), (x0 + i, y + 3)], fill=(r, g, b, 255))


def _panel_ciz(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, r: int) -> None:
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=C_PANEL)


def _hesapla_yukseklik() -> int:
    margin = 24
    ara_podyum_liste = 22
    liste_ust_pad = 14
    satir_h = 30
    gap = 2
    satir_sayisi = 7
    liste_alt_pad = 14
    liste_icerik = liste_ust_pad + satir_sayisi * satir_h + (satir_sayisi - 1) * gap + liste_alt_pad
    y_liste_bas = PODYUM_TABAN_Y + ara_podyum_liste
    y_alt = y_liste_bas + liste_icerik
    return y_alt + margin


async def siralama_gorseli_olustur(bot, satirlar: list) -> io.BytesIO:
    w = GENISLIK
    h = _hesapla_yukseklik()

    im = _arka_hazirla(w, h)
    im = _film_foto(im)
    if not ARKA_YOLU.is_file():
        im = _vinyet(im)
    draw = ImageDraw.Draw(im)

    f_bas = _font(FONT_KALIN, 15)
    f_alt = _font(FONT_ISIM, 9)
    f_etik = _font(FONT_KALIN, 9)
    f_samp = _font(FONT_KALIN, 9)
    f_ip = _font(FONT_ISIM, 12)
    f_sp = _font(FONT_KALIN, 11)
    f_skor_liste = _font(FONT_SAYI, 11)
    f_il = _font(FONT_ISIM, 12)
    f_sira = _font(FONT_KALIN, 11)
    f_rozet = _font(FONT_KALIN, 19)

    async def avatar_url(uid: int) -> str:
        try:
            u = await bot.fetch_user(uid)
            return u.display_avatar.url
        except Exception:
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    n = min(len(satirlar), 10)
    uids = [int(satirlar[i]["discord_id"]) for i in range(n)]
    urls = await asyncio.gather(*[avatar_url(uid) for uid in uids])

    margin = 24
    # Başlık — gösterişli
    t1 = "M2B COIN"
    t2 = "EN İYİLER"
    bb1 = draw.textbbox((0, 0), t1, font=f_bas)
    _yazi_parlak(draw, w // 2, 10, t1, f_bas, (255, 248, 225, 255), (100, 60, 15))
    bb2 = draw.textbbox((0, 0), t2, font=f_alt)
    draw.text(((w - (bb2[2] - bb2[0])) // 2, 32), t2, font=f_alt, fill=(200, 185, 220, 255))
    _altin_cizgi(draw, w // 2, 48, min(420, w - 80))

    podyum_ust = 56
    _panel_ciz(draw, margin, podyum_ust, w - margin, PODYUM_TABAN_Y + 8, 20)
    draw.rounded_rectangle(
        [margin, podyum_ust, w - margin, PODYUM_TABAN_Y + 8],
        radius=20,
        outline=(100, 85, 140, 100),
        width=1,
    )

    ic = w - 2 * margin
    ara = 2 * PODYUM_GAP
    blok = ic - ara
    w_sol, w_orta, w_sag = 216, 288, 216
    if w_sol + w_orta + w_sag != blok:
        w_orta = blok - w_sol - w_sag
    x_sol = margin
    x_orta = x_sol + w_sol + PODYUM_GAP
    x_sag = x_orta + w_orta + PODYUM_GAP

    h_orta, h_sol, h_sag = 162, 142, 132
    base = PODYUM_TABAN_Y

    _parlama_merkez(im, x_orta + w_orta // 2, base - h_orta // 2, w_orta + 120, h_orta + 100)

    podyum = [
        (x_sol, w_sol, h_sol, GUM_UST, GUM_ALT, 1, "İKİNCİ", (28, 38, 58), False),
        (x_sag, w_sag, h_sag, BRONZ_UST, BRONZ_ALT, 2, "ÜÇÜNCÜ", (72, 42, 22), False),
        (x_orta, w_orta, h_orta, ALTIN_UST, ALTIN_ALT, 0, "ŞAMPİYON", C_ALTIN_YAZI, True),
    ]

    for x0, ww, hh, cu, ca, vi, etik, sk_col, sicak in podyum:
        if vi >= n:
            continue
        y0 = base - hh
        _golge_derin(im, x0, y0, ww, hh, KAVIS)
        tab = _gradyan_metalik(ww, hh, KAVIS, cu, ca, sicak)
        parlak = Image.new("RGBA", (ww, 4), (0, 0, 0, 0))
        cl = tuple(min(255, c + 50) for c in cu)
        ImageDraw.Draw(parlak).rectangle((0, 0, ww, 4), fill=(*cl, 235))
        tab.alpha_composite(parlak, (0, 0))
        im.paste(tab, (x0, y0), tab)
        # Çift çerçeve: dış koyu, iç açık
        draw.rounded_rectangle([x0, y0, x0 + ww, y0 + hh], radius=KAVIS, outline=(20, 15, 35, 200), width=2)
        ic_renk = (255, 230, 160, 180) if sicak else (200, 210, 230, 140)
        draw.rounded_rectangle([x0 + 2, y0 + 2, x0 + ww - 2, y0 + hh - 2], radius=KAVIS - 2, outline=ic_renk, width=1)

        cx = x0 + ww // 2
        if vi == 0:
            _tac_ciz(draw, cx, y0 + 4, min(ww - 24, 100), (255, 210, 80))

        rb = 16
        ry0 = y0 + (28 if vi == 0 else 10)
        rz = Image.new("RGBA", (rb * 2, rb * 2), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rz)
        rd.ellipse((0, 0, rb * 2, rb * 2), fill=(*C_KOYU, 252))
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

        et_font = f_samp if vi == 0 else f_etik
        et_renk = (95, 55, 8, 255) if vi == 0 else (*C_KOYU, 255)
        _orta(draw, cx, y0 + (52 if vi == 0 else 42), etik, et_font, et_renk)

        r_av = 32 if vi == 0 else 25 if vi == 1 else 24
        av_y = y0 + (68 if vi == 0 else 56)
        boy = r_av * 2
        av = await _indir(urls[vi], (boy, boy))
        if av:
            m = _yuvarlak_maske(boy)
            yu = Image.new("RGBA", (boy, boy), (0, 0, 0, 0))
            yu.paste(av, (0, 0), m)
            im.paste(yu, (cx - r_av, av_y), yu)
        else:
            draw.ellipse([cx - r_av, av_y, cx + r_av, av_y + boy], fill=(32, 40, 58, 255))
        draw.ellipse(
            [cx - r_av - 3, av_y - 3, cx + r_av + 3, av_y + boy + 3],
            outline=(*cu, 250),
            width=2,
        )

        isim = _metin_guvenli(str(satirlar[vi]["username"]), 15)
        sk = f"{int(satirlar[vi]['bakiye']):,}"
        ty = av_y + boy + 5
        is_bb = draw.textbbox((0, 0), isim, font=f_ip)
        _orta(draw, cx, ty, isim, f_ip, (*C_KOYU, 255))
        sk_y = ty + (is_bb[3] - is_bb[1]) + 3
        bb = draw.textbbox((0, 0), sk, font=f_sp)
        wsk = bb[2] - bb[0]
        draw.text((cx - wsk // 2 + 1, sk_y + 1), sk, font=f_sp, fill=(35, 22, 5, 200))
        draw.text((cx - wsk // 2, sk_y), sk, font=f_sp, fill=(*sk_col, 255))

    yp = PODYUM_TABAN_Y + 22
    liste_ust_pad = 14
    satir_h = 30
    gap_i = 2
    satir_sayisi = 7
    liste_alt_pad = 14
    liste_icerik = liste_ust_pad + satir_sayisi * satir_h + (satir_sayisi - 1) * gap_i + liste_alt_pad
    y_alt = yp + liste_icerik

    _panel_ciz(draw, margin, yp, w - margin, y_alt, 18)
    draw.line([(margin + 20, yp + 2), (w - margin - 20, yp + 2)], fill=(210, 175, 90, 200), width=2)
    draw.rounded_rectangle(
        [margin, yp, w - margin, y_alt],
        radius=18,
        outline=(90, 100, 130, 150),
        width=1,
    )

    sol0 = margin + 16
    rank_w = 34
    av_r = 13
    av_x0 = sol0 + rank_w + 6
    isim_x = av_x0 + av_r * 2 + 10
    sag_x = w - margin - 18
    max_i = sag_x - isim_x - 50

    for j in range(3, n):
        idx = j - 3
        ry = yp + liste_ust_pad + idx * (satir_h + gap_i)

        if idx > 0:
            ly = ry - (gap_i + 1) // 2
            draw.line([(margin + 16, ly), (w - margin - 16, ly)], fill=(*C_AYIRICI, 100), width=1)

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
            draw.ellipse([cx - av_r, cy - av_r, cx + av_r, cy + av_r], fill=(48, 56, 72, 255))

        isim = _metin_guvenli(str(satirlar[j]["username"]), 42)
        isim = _kisalt_genislik(draw, f_il, isim, max_i)
        bb_i = draw.textbbox((0, 0), isim, font=f_il)
        ih = bb_i[3] - bb_i[1]
        draw.text((isim_x, ry + (satir_h - ih) // 2), isim, font=f_il, fill=(*C_METIN, 255))

        sk = f"{int(satirlar[j]['bakiye']):,}"
        _sag(draw, sag_x + 1, cy + 1, sk, f_skor_liste, (0, 0, 0, 160))
        _sag(draw, sag_x, cy, sk, f_skor_liste, (255, 215, 115, 255))

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    log.info("Sıralama görseli (v%s, gösterişli, kullanıcı=%s, h=%s)", GORSEL_SURUM, n, h)
    return buf
