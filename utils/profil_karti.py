# utils/profil_karti.py — Profil karti v6
# Yatay (horizontal) layout: 800x250 cikti
# Supersampling: 1600x500 render → LANCZOS → 800x250 HD

import io
import os
import glob
import math
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Boyutlar ──────────────────────────────────────────────────────────────────
SCALE    = 2
OUT_W    = 800
OUT_H    = 250
KART_W   = OUT_W * SCALE   # 1600  (render genisligi)
KART_H   = OUT_H * SCALE   # 500   (render yuksekligi)

PAD      = 40              # kenar boslugu (render px)
LEFT_BAR = 8               # sol accent cubugu (render px)
AV_SIZE  = 224             # avatar capu (render px) → display 112px
TEXT_X   = LEFT_BAR + PAD + AV_SIZE + 44   # metin baslangic x = 316


# ── Font ──────────────────────────────────────────────────────────────────────

def _find_font(names: list[str]) -> str | None:
    dirs = [
        "/usr/share/fonts", "/usr/local/share/fonts",
        "/run/current-system/sw/share/fonts", "/nix/store",
        "C:/Windows/Fonts",
    ]
    for name in names:
        for d in dirs:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        for d in dirs:
            if not os.path.isdir(d):
                continue
            hits = glob.glob(os.path.join(d, "**", name), recursive=True)
            if hits:
                return hits[0]
    return None


_BOLD  = _find_font(["DejaVuSans-Bold.ttf",    "LiberationSans-Bold.ttf",
                      "FreeSansBold.ttf",        "Ubuntu-B.ttf",  "arialbd.ttf"])
_PLAIN = _find_font(["DejaVuSans.ttf",          "LiberationSans-Regular.ttf",
                      "FreeSans.ttf",            "Ubuntu-R.ttf",  "arial.ttf"])


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = _BOLD if bold else _PLAIN
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ── Renk ──────────────────────────────────────────────────────────────────────

def _parse_hex(h: str) -> tuple[int, int, int]:
    try:
        h = h.strip("#")
        return int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return (43, 45, 49)


def _accent(h: str) -> tuple[int, int, int]:
    r, g, b = _parse_hex(h)
    m = max(r, g, b)
    if m < 90:
        f = 200 / max(m, 1)
        r, g, b = min(int(r * f), 255), min(int(g * f), 255), min(int(b * f), 255)
    return (r, g, b)


def _shape_col(acc: tuple, dr: int, dg: int, db: int) -> tuple:
    # Her kanal max 148 → kumulatif overlayde beyazlasma olmaz
    return (
        min(acc[0] // 4 + dr, 148),
        min(acc[1] // 4 + dg, 148),
        min(acc[2] // 4 + db, 148),
    )


# ── Layer-safe composite ───────────────────────────────────────────────────────

def _composite(base: Image.Image, draw_fn) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    out = Image.alpha_composite(base, layer)
    return out, ImageDraw.Draw(out)


# ── Geometrik arka plan ───────────────────────────────────────────────────────

def _rotated_rect(cx: float, cy: float, w: float, h: float, ang: float) -> list:
    rad    = math.radians(ang)
    ca, sa = math.cos(rad), math.sin(rad)
    hw, hh = w / 2, h / 2
    return [
        (int(cx + x * ca - y * sa), int(cy + x * sa + y * ca))
        for x, y in [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    ]


def _build_bg(renk_hex: str) -> Image.Image:
    r, g, b = _parse_hex(renk_hex)
    acc     = _accent(renk_hex)

    base = (max(r // 10, 6), max(g // 10, 6), max(b // 8 + 3, 10))
    img  = Image.new("RGBA", (KART_W, KART_H), (*base, 255))

    # Sag tarafa yogunlastirilmis rhombus katmanlar (yatay kart icin ayarli)
    shapes = [
        # cx_r   cy_r   w     h    ang   alpha  dr   dg   db
        (0.82,  0.45,  700,  900,  45,    42,   60,  40, 108),
        (0.68,  0.20,  500,  700,  45,    28,   50,  32,  86),
        (0.95,  0.70,  600,  800,  45,    26,   55,  40,  96),
        (0.55,  0.10,  400,  600,  45,    18,   38,  26,  64),
        (0.90,  0.90,  480,  680,  45,    16,   56,  44, 100),
        (0.42,  0.80,  300,  500,  45,    12,   24,  18,  48),
    ]
    for cx_r, cy_r, sw, sh, ang, alpha, dr, dg, db in shapes:
        sc    = _shape_col(acc, dr, dg, db)
        pts   = _rotated_rect(KART_W * cx_r, KART_H * cy_r, sw, sh, ang)
        layer = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(pts, fill=(*sc, alpha))
        img = Image.alpha_composite(img, layer)

    # Sol vignette — avatar + metin alani okunaklilik icin kararti
    vig_w = TEXT_X + 200
    vig   = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
    vd    = ImageDraw.Draw(vig)
    for xi in range(vig_w):
        a = int(78 * (1.0 - xi / vig_w))
        vd.line([(xi, 0), (xi, KART_H)], fill=(0, 0, 0, a))
    return Image.alpha_composite(img, vig)


# ── Yardimcilar ───────────────────────────────────────────────────────────────

async def _fetch(url: str, size: tuple | None = None) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    img = Image.open(io.BytesIO(await r.read())).convert("RGBA")
                    if size:
                        img = img.resize(size, Image.LANCZOS)
                    return img
    except Exception:
        return None


def _circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _xp_bar(kart: Image.Image, x: int, y: int, w: int, h: int,
             exp: int, gereken: int, acc: tuple) -> Image.Image:
    """Sade XP bar: ince dark track + solid accent dolgu."""
    oran = min(exp / max(gereken, 1), 1.0)
    dolu = int(w * oran)
    r    = h // 2

    def bg(d):
        d.rounded_rectangle([x, y, x + w, y + h], radius=r,
                             fill=(255, 255, 255, 18))
    kart, _ = _composite(kart, bg)

    if dolu > r:
        def fill(d):
            d.rounded_rectangle([x, y, x + dolu, y + h], radius=r,
                                 fill=(*acc, 255))
        kart, _ = _composite(kart, fill)

    return kart


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

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
    bio:           str | None = None,
) -> io.BytesIO:

    acc = _accent(renk_hex)

    # ── Arka plan ─────────────────────────────────────────────
    if arka_plan_url:
        raw = await _fetch(arka_plan_url, (KART_W, KART_H))
    else:
        raw = None

    if raw:
        kart = raw.convert("RGBA").filter(ImageFilter.GaussianBlur(3))
        def ov(d): d.rectangle([(0, 0), (KART_W, KART_H)], fill=(0, 0, 0, 148))
        kart, _ = _composite(kart, ov)
    else:
        kart = _build_bg(renk_hex)

    # ── Sol accent cubugu ──────────────────────────────────────
    def left_bar(d):
        d.rectangle([(0, 0), (LEFT_BAR, KART_H)], fill=(*acc, 255))
    kart, draw = _composite(kart, left_bar)

    # ── Fontlar (render boyutu, display = yarisina indirgenir) ─
    fn_name  = _font(52, bold=True)    # display ≈ 26 px
    fn_sub   = _font(26, bold=False)   # display ≈ 13 px  (bio / rozet)
    fn_label = _font(24, bold=False)   # display ≈ 12 px  (stat baslik)
    fn_val   = _font(48, bold=True)    # display ≈ 24 px  (stat deger)
    fn_xp    = _font(24, bold=False)   # display ≈ 12 px  (xp sayilar)
    fn_xpl   = _font(20, bold=False)   # display ≈ 10 px  (xp alt metin)

    WHITE  = (255, 255, 255, 255)
    MUTED  = (160, 160, 195, 215)
    ACCENT = (*acc, 238)

    # ── Avatar ────────────────────────────────────────────────
    av_x  = LEFT_BAR + PAD
    av_y  = (KART_H - AV_SIZE) // 2   # dikey ortalama: 138
    av_cx = av_x + AV_SIZE // 2        # 160
    av_cy = av_y + AV_SIZE // 2        # 250

    # Golge
    def shadow(d):
        sr = AV_SIZE // 2 + 14
        d.ellipse([av_cx - sr, av_cy - sr, av_cx + sr, av_cy + sr],
                  fill=(0, 0, 0, 90))
    kart, draw = _composite(kart, shadow)

    # Accent halka
    ring_r = AV_SIZE // 2 + 5
    draw.ellipse([av_cx - ring_r, av_cy - ring_r, av_cx + ring_r, av_cy + ring_r],
                 outline=(*acc, 255), width=5)

    av_img = await _fetch(avatar_url, (AV_SIZE, AV_SIZE))
    if av_img:
        circ = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        circ.paste(av_img.convert("RGBA"), (0, 0), _circle_mask(AV_SIZE))
        kart.paste(circ, (av_x, av_y), circ)
        draw = ImageDraw.Draw(kart)
    else:
        draw.ellipse([av_x, av_y, av_x + AV_SIZE, av_y + AV_SIZE],
                     fill=(55, 55, 78, 255))

    # ── Kullanici adi ─────────────────────────────────────────
    ty = 46
    draw.text((TEXT_X, ty), kullanici_adi[:22], font=fn_name, fill=WHITE)
    ty += 64

    # Bio
    if bio:
        draw.text((TEXT_X, ty), bio[:46], font=fn_sub, fill=MUTED)
        ty += 36

    # Aktif rozet pill
    if aktif_rozet:
        rtxt = aktif_rozet[:26]
        bbox = draw.textbbox((0, 0), rtxt, font=fn_sub)
        pw   = bbox[2] - bbox[0] + 24
        ph   = 30
        pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle(
            [0, 0, pw - 1, ph - 1], radius=ph // 2,
            fill=(*acc, 42), outline=(*acc, 148), width=1,
        )
        kart.paste(pill, (TEXT_X, ty), pill)
        draw = ImageDraw.Draw(kart)
        draw.text((TEXT_X + 12, ty + 5), rtxt, font=fn_sub, fill=ACCENT)
        ty += 40

    # ── Yatay ayirac 1 ────────────────────────────────────────
    sep1_y = 248
    def sep1(d):
        d.rectangle([(TEXT_X, sep1_y), (KART_W - PAD, sep1_y + 2)],
                    fill=(255, 255, 255, 22))
    kart, draw = _composite(kart, sep1)

    # ── Stat satiri ───────────────────────────────────────────
    stats   = [("LEVEL", str(level)), ("COINS", f"{bakiye:,}"), ("SIRALAMA", f"#{siralama:,}")]
    col_w   = 280
    stat_y  = sep1_y + 20

    for i, (lbl, val) in enumerate(stats):
        sx = TEXT_X + i * col_w
        draw.text((sx, stat_y),      lbl, font=fn_label, fill=MUTED)
        draw.text((sx, stat_y + 28), val, font=fn_val,   fill=WHITE)

    # Dikey ayiraclar
    def vert_divs(d):
        for i in range(1, len(stats)):
            dx = TEXT_X + i * col_w - 16
            d.rectangle([(dx, stat_y), (dx + 2, stat_y + 80)],
                        fill=(255, 255, 255, 20))
    kart, draw = _composite(kart, vert_divs)

    # ── Yatay ayirac 2 ────────────────────────────────────────
    sep2_y = stat_y + 90
    def sep2(d):
        d.rectangle([(TEXT_X, sep2_y), (KART_W - PAD, sep2_y + 2)],
                    fill=(255, 255, 255, 22))
    kart, draw = _composite(kart, sep2)

    # ── EXP bolumu ────────────────────────────────────────────
    bar_x = TEXT_X
    bar_w = KART_W - TEXT_X - PAD   # 1600 - 316 - 40 = 1244
    bar_h = 26
    xp_y  = sep2_y + 22

    pct     = int(min(exp / max(gereken_exp, 1), 1.0) * 100)
    xp_str  = f"{exp:,} / {gereken_exp:,}"
    pct_str = f"%{pct}"

    draw.text((bar_x, xp_y), xp_str, font=fn_xp, fill=MUTED)
    bbox = draw.textbbox((0, 0), pct_str, font=fn_xp)
    draw.text((bar_x + bar_w - (bbox[2] - bbox[0]), xp_y),
              pct_str, font=fn_xp, fill=WHITE)

    kart = _xp_bar(kart, bar_x, xp_y + 30, bar_w, bar_h, exp, gereken_exp, acc)
    draw = ImageDraw.Draw(kart)

    draw.text((bar_x, xp_y + 30 + bar_h + 10),
              f"TOTAL XP: {exp:,}", font=fn_xpl, fill=MUTED)

    # ── Alt accent seridi ─────────────────────────────────────
    def stripe(d):
        d.rectangle([(0, KART_H - 8), (KART_W, KART_H)], fill=(*acc, 228))
    kart, _ = _composite(kart, stripe)

    # ── Supersampling: 1600x500 → LANCZOS → 800x250 ───────────
    dark  = Image.new("RGBA", (KART_W, KART_H), (8, 8, 14, 255))
    final = Image.alpha_composite(dark, kart)
    final = final.resize((OUT_W, OUT_H), Image.LANCZOS)

    buf = io.BytesIO()
    final.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
