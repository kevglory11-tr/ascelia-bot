"""
utils/profil_karti.py — Dinamik profil kartı üretici (Card1 stili).
"""

import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Font yükleme ────────────────────────────────────────────────────────────

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_BUNDLED_FONT = os.path.join(_ASSETS, "font.ttf")

_FONT_KALIN = [
    _BUNDLED_FONT,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]
_FONT_NORMAL = [
    _BUNDLED_FONT,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

def _font(boyut: int, kalin: bool = True) -> ImageFont.FreeTypeFont:
    for yol in (_FONT_KALIN if kalin else _FONT_NORMAL):
        if os.path.exists(yol):
            try:
                return ImageFont.truetype(yol, boyut)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Yardımcı fonksiyonlar ───────────────────────────────────────────────────

def _sayi_fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _daire_maske(boyut: int) -> Image.Image:
    m = Image.new("L", (boyut, boyut), 0)
    ImageDraw.Draw(m).ellipse((0, 0, boyut - 1, boyut - 1), fill=255)
    return m


def _yuvarlik_maske(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


async def _gorsel_indir(url: str, boyut: tuple) -> Image.Image | None:
    import aiohttp
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    data = await r.read()
                    img = Image.open(io.BytesIO(data)).convert("RGBA")
                    return img.resize(boyut, Image.LANCZOS)
    except Exception:
        return None


# ── Card1 ───────────────────────────────────────────────────────────────────

W, H    = 800, 280
AV_SIZE = 190   # Avatar boyutu
AV_X    = 16    # Avatar sol kenar
BAR_H   = 44    # XP bar yüksekliği
RADIUS  = 22    # Köşe yuvarlama

ACCENT  = (147, 51, 234)   # Mor vurgu


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

    # ── 1. Arka plan ────────────────────────────────────────
    if arka_plan_url:
        bg = await _gorsel_indir(arka_plan_url, (W, H))
    else:
        bg = None

    if bg is None:
        try:
            r, g, b = (int(renk_hex[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            r, g, b = 30, 30, 50
        bg = Image.new("RGBA", (W, H), (r, g, b, 255))
    else:
        bg = bg.convert("RGBA")
        bg = bg.filter(ImageFilter.GaussianBlur(radius=1))

    # Karartma katmanı
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    bg.paste(dark, (0, 0), dark)

    kart = bg.copy()
    draw = ImageDraw.Draw(kart, "RGBA")

    # Sol avatar paneli (hafif koyu)
    panel_w = AV_X + AV_SIZE + 18
    panel = Image.new("RGBA", (panel_w, H), (0, 0, 0, 90))
    kart.paste(panel, (0, 0), panel)

    # Panel sağ kenar çizgisi
    draw.line([(panel_w, 0), (panel_w, H)], fill=(*ACCENT, 160), width=2)

    # ── 2. Avatar ───────────────────────────────────────────
    av_y = (H - AV_SIZE) // 2
    avatar = await _gorsel_indir(avatar_url, (AV_SIZE, AV_SIZE))

    if avatar:
        avatar = avatar.convert("RGBA")
        daire  = _daire_maske(AV_SIZE)
        av_img = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        av_img.paste(avatar, (0, 0), daire)

        # Mor halka
        hk = AV_SIZE + 8
        halka = Image.new("RGBA", (hk, hk), (0, 0, 0, 0))
        ImageDraw.Draw(halka).ellipse((0, 0, hk - 1, hk - 1), fill=(*ACCENT, 220))
        kart.paste(halka, (AV_X - 4, av_y - 4), halka)
        kart.paste(av_img, (AV_X, av_y), av_img)
    else:
        draw.ellipse([AV_X, av_y, AV_X + AV_SIZE, av_y + AV_SIZE], fill=(60, 60, 80, 200))

    # ── 3. Yazılar ──────────────────────────────────────────
    f_buyuk = _font(38, kalin=True)
    f_orta  = _font(26, kalin=True)
    f_kucuk = _font(18, kalin=False)

    text_x = AV_X + AV_SIZE + 28

    # Kullanıcı adı
    draw.text(
        (text_x, 32),
        kullanici_adi[:22],
        font=f_buyuk,
        fill=(255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
    )

    # Aktif rozet
    rozet_y = 80
    if aktif_rozet:
        draw.text(
            (text_x, rozet_y),
            f"✦ {aktif_rozet[:30]}",
            font=f_kucuk,
            fill=(200, 160, 255, 220),
        )
        level_y = rozet_y + 28
    else:
        level_y = rozet_y + 4

    # LEVEL - X (sol)
    draw.text(
        (text_x, level_y),
        f"LEVEL — {level}",
        font=f_orta,
        fill=(255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
    )

    # XP metni (sağ hizalı, aynı y)
    xp_str  = f"{_sayi_fmt(exp)} / {_sayi_fmt(gereken_exp)} XP"
    xp_bbox = draw.textbbox((0, 0), xp_str, font=f_orta)
    xp_w    = xp_bbox[2] - xp_bbox[0]
    draw.text(
        (W - xp_w - 20, level_y),
        xp_str,
        font=f_orta,
        fill=(255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
    )

    # ── 4. XP Bar ───────────────────────────────────────────
    bar_x = text_x
    bar_y = H - BAR_H - 30
    bar_w = W - text_x - 20

    oran  = min(exp / gereken_exp, 1.0) if gereken_exp else 0
    dolu  = max(int(bar_w * oran), BAR_H)

    bar_img  = Image.new("RGBA", (bar_w, BAR_H), (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(bar_img, "RGBA")

    # Arka plan (yarı saydam beyaz)
    bar_draw.rounded_rectangle(
        (0, 0, bar_w - 1, BAR_H - 1),
        radius=BAR_H // 2,
        fill=(255, 255, 255, 45),
    )
    # Doluluk
    if exp > 0:
        bar_draw.rounded_rectangle(
            (0, 0, dolu, BAR_H - 1),
            radius=BAR_H // 2,
            fill=(*ACCENT, 255),
        )
    # Parlama şeridi
    bar_draw.rounded_rectangle(
        (4, 3, max(dolu - 4, 10), BAR_H // 2 - 2),
        radius=3,
        fill=(255, 255, 255, 55),
    )

    kart.paste(bar_img, (bar_x, bar_y), bar_img)

    # ── 5. Alt bilgi ────────────────────────────────────────
    alt_y = bar_y + BAR_H + 6

    draw.text(
        (text_x, alt_y),
        f"#{siralama:,}  RANK",
        font=f_kucuk,
        fill=(200, 200, 220, 200),
    )

    coin_str  = f"{bakiye:,} coin"
    coin_bbox = draw.textbbox((0, 0), coin_str, font=f_kucuk)
    coin_w    = coin_bbox[2] - coin_bbox[0]
    draw.text(
        (W - coin_w - 20, alt_y),
        coin_str,
        font=f_kucuk,
        fill=(255, 210, 60, 220),
    )

    # ── 6. Yuvarlak köşe maskesi ────────────────────────────
    maske  = _yuvarlik_maske(W, H, RADIUS)
    sonuc  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sonuc.paste(kart, (0, 0), maske)

    buf = io.BytesIO()
    sonuc.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
