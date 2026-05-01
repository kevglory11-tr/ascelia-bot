# utils/profil_karti.py — Profil karti v4: 640x860 HD, geometric bg, portrait

import io
import os
import glob
import math
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KART_W  = 640
KART_H  = 860
AV_SIZE = 172
PAD     = 36


# ── Font keşfi ────────────────────────────────────────────────────────────────

def _find_font_path(names: list[str]) -> str | None:
    dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/run/current-system/sw/share/fonts",
        "/nix/store",
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


_BOLD  = _find_font_path(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
                           "FreeSansBold.ttf",     "Ubuntu-B.ttf",  "arialbd.ttf"])
_PLAIN = _find_font_path(["DejaVuSans.ttf",       "LiberationSans-Regular.ttf",
                           "FreeSans.ttf",          "Ubuntu-R.ttf",  "arial.ttf"])


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = _BOLD if bold else _PLAIN
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ── Renk yardımcıları ─────────────────────────────────────────────────────────

def _parse_hex(h: str) -> tuple[int, int, int]:
    try:
        h = h.strip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
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
    """
    Accent rengin karanlik tureviyle shape rengi uretir.
    Her kanal max 155'te kisitlanir — cok parlak/beyaz olmasi onlenir.
    """
    r = min(acc[0] // 4 + dr, 155)
    g = min(acc[1] // 4 + dg, 155)
    b = min(acc[2] // 4 + db, 155)
    return (r, g, b)


# ── Layer-based composite yardimci ────────────────────────────────────────────

def _paste_layer(base: Image.Image, draw_fn) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Yeni bir RGBA layer olusturur, draw_fn ile cizer, base ile composite eder."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d     = ImageDraw.Draw(layer)
    draw_fn(d)
    result = Image.alpha_composite(base, layer)
    return result, ImageDraw.Draw(result)


# ── Geometrik arka plan ───────────────────────────────────────────────────────

def _rotated_rect(cx: float, cy: float, w: float, h: float, ang: float) -> list:
    rad    = math.radians(ang)
    ca, sa = math.cos(rad), math.sin(rad)
    hw, hh = w / 2, h / 2
    return [(int(cx + x * ca - y * sa), int(cy + x * sa + y * ca))
            for x, y in [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]]


def _build_bg(renk_hex: str) -> Image.Image:
    r, g, b = _parse_hex(renk_hex)
    acc     = _accent(renk_hex)

    # Cok karanlik taban — kanal basina max 20
    base_r = min(max(r // 10, 6),  20)
    base_g = min(max(g // 10, 6),  20)
    base_b = min(max(b // 8 + 4, 10), 22)
    img    = Image.new("RGBA", (KART_W, KART_H), (base_r, base_g, base_b, 255))

    # Geometrik rhombus katmanlar — sag tarafa yogun, max 155 renk
    # (cx_r, cy_r, genislik, yukseklik, aci, alpha, dr, dg, db)
    shapes = [
        (0.80, 0.24, 640, 980,  45, 42, 60,  40, 110),
        (0.62, 0.12, 460, 780,  45, 30, 50,  32,  88),
        (0.96, 0.65, 560, 870,  45, 28, 55,  40,  98),
        (0.47, 0.08, 330, 620,  45, 22, 38,  26,  66),
        (0.88, 0.92, 440, 710,  45, 18, 58,  46, 102),
        (0.28, 0.62, 250, 500,  45, 13, 25,  18,  50),
    ]
    for cx_r, cy_r, sw, sh, ang, alpha, dr, dg, db in shapes:
        pts   = _rotated_rect(KART_W * cx_r, KART_H * cy_r, sw, sh, ang)
        sc    = _shape_col(acc, dr, dg, db)
        layer = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(pts, fill=(*sc, alpha))
        img = Image.alpha_composite(img, layer)

    # Sol vignette — stat alani okunakliligini arttirir
    vig_w = PAD + 240
    vig   = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
    vd    = ImageDraw.Draw(vig)
    for xi in range(vig_w):
        a = int(75 * (1.0 - xi / vig_w))
        vd.line([(xi, 0), (xi, KART_H)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, vig)

    return img


# ── Yardimci cizimler ─────────────────────────────────────────────────────────

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


def _draw_xp_bar(kart: Image.Image, x: int, y: int, w: int, h: int,
                 exp: int, gereken: int, acc: tuple) -> Image.Image:
    oran = min(exp / max(gereken, 1), 1.0)
    dolu = int(w * oran)
    r    = h // 2

    # Arkaplan — semi-transparent, layer ile composite
    def draw_bg(d):
        d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=(10, 10, 22, 200))
    kart, _ = _paste_layer(kart, draw_bg)

    # Dolu kisim + shine — tam opak
    if dolu > r * 2:
        def draw_fill(d):
            d.rounded_rectangle([x, y, x + dolu, y + h], radius=r, fill=(*acc, 255))
            sw = max(dolu - 10, 0)
            if sw:
                d.rounded_rectangle([x + 5, y + 3, x + 5 + sw, y + h // 2],
                                    radius=2, fill=(255, 255, 255, 55))
        kart, _ = _paste_layer(kart, draw_fill)

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
        def draw_overlay(d):
            d.rectangle([(0, 0), (KART_W, KART_H)], fill=(0, 0, 0, 145))
        kart, _ = _paste_layer(kart, draw_overlay)
    else:
        kart = _build_bg(renk_hex)

    # ── Fontlar ───────────────────────────────────────────────
    fn_name  = _font(42, bold=True)    # kullanici adi
    fn_label = _font(20, bold=False)   # stat baslik
    fn_stat  = _font(52, bold=True)    # stat deger
    fn_sub   = _font(22, bold=False)   # rozet pill / bio
    fn_xp    = _font(22, bold=False)   # xp sayilar
    fn_xpl   = _font(18, bold=False)   # xp alt etiket

    WHITE  = (255, 255, 255, 255)
    MUTED  = (160, 160, 195, 215)
    ACCENT = (*acc, 240)

    # ── Avatar ────────────────────────────────────────────────
    av_x  = PAD
    av_y  = PAD
    av_cx = av_x + AV_SIZE // 2
    av_cy = av_y + AV_SIZE // 2

    # Golge
    def draw_shadow(d):
        sr = AV_SIZE // 2 + 10
        d.ellipse([av_cx - sr, av_cy - sr, av_cx + sr, av_cy + sr],
                  fill=(0, 0, 0, 95))
    kart, draw = _paste_layer(kart, draw_shadow)

    # Accent halka
    ring_r = AV_SIZE // 2 + 4
    draw.ellipse([av_cx - ring_r, av_cy - ring_r, av_cx + ring_r, av_cy + ring_r],
                 outline=(*acc, 255), width=4)

    # Avatar gorsel
    av_img = await _fetch(avatar_url, (AV_SIZE, AV_SIZE))
    if av_img:
        circle = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        circle.paste(av_img.convert("RGBA"), (0, 0), _circle_mask(AV_SIZE))
        kart.paste(circle, (av_x, av_y), circle)
        draw = ImageDraw.Draw(kart)
    else:
        draw.ellipse([av_x, av_y, av_x + AV_SIZE, av_y + AV_SIZE], fill=(55, 55, 78, 255))

    # Badge (alt-sag kose, accent rengi)
    badge_cx = av_x + AV_SIZE - 4
    badge_cy = av_y + AV_SIZE - 4
    br = 15
    def draw_badge(d):
        d.ellipse([badge_cx - br, badge_cy - br, badge_cx + br, badge_cy + br],
                  fill=(*acc, 230))
    kart, _ = _paste_layer(kart, draw_badge)
    draw = ImageDraw.Draw(kart)
    draw.ellipse([badge_cx - br, badge_cy - br, badge_cx + br, badge_cy + br],
                 outline=(255, 255, 255, 160), width=2)

    # ── Kullanici adi + bio + rozet (avatar sagi) ─────────────
    tx     = av_x + AV_SIZE + 18
    name_y = av_y + 16
    draw.text((tx, name_y), kullanici_adi[:17], font=fn_name, fill=WHITE)

    cur_y = name_y + 52
    if bio:
        draw.text((tx, cur_y), bio[:32], font=fn_sub, fill=MUTED)
        cur_y += 30

    if aktif_rozet:
        rtxt = aktif_rozet[:22]
        bbox = draw.textbbox((0, 0), rtxt, font=fn_sub)
        pw   = bbox[2] - bbox[0] + 20
        ph   = 26
        def draw_pill(d):
            d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2,
                                 fill=(*acc, 45), outline=(*acc, 155), width=1)
        pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2,
                                               fill=(*acc, 45), outline=(*acc, 155), width=1)
        kart.paste(pill, (tx, cur_y), pill)
        draw = ImageDraw.Draw(kart)
        draw.text((tx + 10, cur_y + 4), rtxt, font=fn_sub, fill=ACCENT)

    # ── Yatay ayirac 1 ────────────────────────────────────────
    div1_y = av_y + AV_SIZE + 24
    def draw_div1(d):
        d.rectangle([(PAD, div1_y), (KART_W - PAD, div1_y + 2)], fill=(255, 255, 255, 25))
    kart, draw = _paste_layer(kart, draw_div1)

    # ── Sol sütun statlar (büyük font, tek sütun) ─────────────
    stats = [
        ("LVL",      str(level)),
        ("COINS",    f"{bakiye:,}"),
        ("SIRALAMA", f"#{siralama:,}"),
    ]

    sy       = div1_y + 28
    stat_gap = 126   # her stat için ayrilan dikey alan

    for lbl, val in stats:
        draw.text((PAD, sy),      lbl, font=fn_label, fill=MUTED)
        draw.text((PAD, sy + 24), val, font=fn_stat,  fill=WHITE)
        sy += stat_gap

    # ── Yatay ayirac 2 ────────────────────────────────────────
    div2_y = div1_y + 28 + stat_gap * len(stats) + 10
    def draw_div2(d):
        d.rectangle([(PAD, div2_y), (KART_W - PAD, div2_y + 2)], fill=(255, 255, 255, 25))
    kart, draw = _paste_layer(kart, draw_div2)

    # ── EXP Bolumu (tam genislik) ─────────────────────────────
    xp_y     = div2_y + 30
    bar_x    = PAD
    bar_w    = KART_W - PAD * 2
    bar_h    = 28

    # "EXP" sol, oran ve yuzde sag
    oran_pct = int(min(exp / max(gereken_exp, 1), 1.0) * 100)
    xp_left  = f"EXP  {exp:,} / {gereken_exp:,}"
    xp_right = f"%{oran_pct}"
    draw.text((bar_x, xp_y), xp_left, font=fn_xp, fill=MUTED)
    bbox = draw.textbbox((0, 0), xp_right, font=fn_xp)
    draw.text((bar_x + bar_w - (bbox[2] - bbox[0]), xp_y), xp_right, font=fn_xp, fill=ACCENT)

    kart = _draw_xp_bar(kart, bar_x, xp_y + 30, bar_w, bar_h, exp, gereken_exp, acc)
    draw = ImageDraw.Draw(kart)

    # TOTAL EXP alt etiketi
    draw.text((bar_x, xp_y + 30 + bar_h + 8),
              f"TOTAL EXP: {exp:,}", font=fn_xpl, fill=MUTED)

    # ── Alt accent seridi ─────────────────────────────────────
    def draw_stripe(d):
        d.rectangle([(0, KART_H - 6), (KART_W, KART_H)], fill=(*acc, 235))
    kart, _ = _paste_layer(kart, draw_stripe)

    # ── Cikti — transparan pikseller beyaz yerine karanliga composite edilir ──
    dark_bg = Image.new("RGBA", (KART_W, KART_H), (8, 8, 14, 255))
    final   = Image.alpha_composite(dark_bg, kart)
    buf = io.BytesIO()
    final.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
