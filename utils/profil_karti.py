# utils/profil_karti.py — Profil karti v5
# Supersampling: 700x940 render → LANCZOS → 350x470 HD cikti
# Teknik: yuksek cozunurluklu render, anti-aliased font, sade XP bar

import io
import os
import glob
import math
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Boyutlar ──────────────────────────────────────────────────────────────────
SCALE  = 2          # supersampling carpani
OUT_W  = 350        # Discord'da gorunecek genislik
OUT_H  = 470        # Discord'da gorunecek yukseklik
KART_W = OUT_W * SCALE   # 700 — render boyutu
KART_H = OUT_H * SCALE   # 940 — render boyutu
PAD    = 36         # i kenar bosugu (render px)
AV_SIZE = 192       # avatar capı (render px)


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
    # Kumulatif beyazlasmayi onlemek icin max 148/kanal
    return (
        min(acc[0] // 4 + dr, 148),
        min(acc[1] // 4 + dg, 148),
        min(acc[2] // 4 + db, 148),
    )


# ── Alpha-safe katman ─────────────────────────────────────────────────────────

def _composite(base: Image.Image, draw_fn) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Yeni RGBA layer yarat, ciz, base ile composite et."""
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

    # Sag tarafa yogunlastirilmis geometrik katmanlar
    shapes = [
        # cx_r  cy_r   w     h    ang  alpha  dr   dg   db
        (0.80, 0.24, 640,  980,  45,   40,   60,  40, 108),
        (0.62, 0.12, 460,  780,  45,   28,   50,  32,  86),
        (0.96, 0.65, 560,  870,  45,   26,   55,  40,  96),
        (0.47, 0.08, 330,  620,  45,   20,   38,  26,  64),
        (0.88, 0.92, 440,  710,  45,   16,   56,  44, 100),
        (0.28, 0.62, 250,  500,  45,   12,   24,  18,  48),
    ]
    for cx_r, cy_r, sw, sh, ang, alpha, dr, dg, db in shapes:
        sc    = _shape_col(acc, dr, dg, db)
        pts   = _rotated_rect(KART_W * cx_r, KART_H * cy_r, sw, sh, ang)
        layer = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(pts, fill=(*sc, alpha))
        img = Image.alpha_composite(img, layer)

    # Sol vignette — stat alti daha koyu, okunaklilik iyilesir
    vig_w = PAD + 300
    vig   = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
    vd    = ImageDraw.Draw(vig)
    for xi in range(vig_w):
        a = int(70 * (1.0 - xi / vig_w))
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
    """Sade XP bar: arka plan + solid accent dolgu."""
    oran = min(exp / max(gereken, 1), 1.0)
    dolu = int(w * oran)
    r    = h // 2

    # Arka plan: ince beyaz saydamlik
    def bg(d):
        d.rounded_rectangle([x, y, x + w, y + h], radius=r,
                             fill=(255, 255, 255, 18))
    kart, _ = _composite(kart, bg)

    # Dolgu: solid accent, ekstra efekt yok
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

    # ── Fontlar (render boyutu = 2× display) ──────────────────
    fn_name  = _font(44, bold=True)    # display ≈ 22 px
    fn_label = _font(22, bold=False)   # display ≈ 11 px  (stat baslık)
    fn_stat  = _font(56, bold=True)    # display ≈ 28 px  (stat deger)
    fn_sub   = _font(24, bold=False)   # display ≈ 12 px  (rozet / bio)
    fn_xp    = _font(24, bold=False)   # display ≈ 12 px  (xp sayilar)
    fn_xpl   = _font(20, bold=False)   # display ≈ 10 px  (xp alt etiket)

    WHITE  = (255, 255, 255, 255)
    MUTED  = (158, 158, 192, 215)
    ACCENT = (*acc, 238)

    draw = ImageDraw.Draw(kart)

    # ── Avatar ────────────────────────────────────────────────
    av_x  = PAD
    av_y  = PAD
    av_cx = av_x + AV_SIZE // 2   # 132
    av_cy = av_y + AV_SIZE // 2   # 132

    # Golge
    def shadow(d):
        sr = AV_SIZE // 2 + 14
        d.ellipse([av_cx - sr, av_cy - sr, av_cx + sr, av_cy + sr],
                  fill=(0, 0, 0, 90))
    kart, draw = _composite(kart, shadow)

    # Accent halka (4px render = 2px display)
    ring_r = AV_SIZE // 2 + 5
    draw.ellipse([av_cx - ring_r, av_cy - ring_r, av_cx + ring_r, av_cy + ring_r],
                 outline=(*acc, 255), width=4)

    av_img = await _fetch(avatar_url, (AV_SIZE, AV_SIZE))
    if av_img:
        circ = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        circ.paste(av_img.convert("RGBA"), (0, 0), _circle_mask(AV_SIZE))
        kart.paste(circ, (av_x, av_y), circ)
        draw = ImageDraw.Draw(kart)
    else:
        draw.ellipse([av_x, av_y, av_x + AV_SIZE, av_y + AV_SIZE], fill=(55, 55, 78, 255))

    # Rozet badge (avatar alt-sag kosesi)
    bx, by, br = av_x + AV_SIZE - 4, av_y + AV_SIZE - 4, 16
    def badge(d):
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=(*acc, 225))
    kart, draw = _composite(kart, badge)
    draw.ellipse([bx - br, by - br, bx + br, by + br],
                 outline=(255, 255, 255, 150), width=2)

    # ── Kullanici adi / bio / rozet pill ──────────────────────
    tx    = av_x + AV_SIZE + 22
    ty    = av_y + 16
    draw.text((tx, ty), kullanici_adi[:17], font=fn_name, fill=WHITE)

    pill_y = ty + 54
    if bio:
        draw.text((tx, pill_y - 20), bio[:30], font=fn_sub, fill=MUTED)
        pill_y += 28

    if aktif_rozet:
        rtxt = aktif_rozet[:20]
        bbox = draw.textbbox((0, 0), rtxt, font=fn_sub)
        pw   = bbox[2] - bbox[0] + 22
        ph   = 28
        pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle(
            [0, 0, pw - 1, ph - 1], radius=ph // 2,
            fill=(*acc, 42), outline=(*acc, 148), width=1,
        )
        kart.paste(pill, (tx, pill_y), pill)
        draw = ImageDraw.Draw(kart)
        draw.text((tx + 11, pill_y + 5), rtxt, font=fn_sub, fill=ACCENT)

    # ── Ayirac 1 ──────────────────────────────────────────────
    div1_y = av_y + AV_SIZE + 52
    def sep1(d):
        d.rectangle([(PAD, div1_y), (KART_W - PAD, div1_y + 2)],
                    fill=(255, 255, 255, 22))
    kart, draw = _composite(kart, sep1)

    # ── Statlar — sol sütun, tek kolon ────────────────────────
    stats    = [("LVL", str(level)), ("COINS", f"{bakiye:,}"), ("SIRALAMA", f"#{siralama:,}")]
    sy       = div1_y + 34
    stat_gap = 134

    for lbl, val in stats:
        draw.text((PAD, sy),      lbl, font=fn_label, fill=MUTED)
        draw.text((PAD, sy + 26), val, font=fn_stat,  fill=WHITE)
        sy += stat_gap

    # ── Ayirac 2 ──────────────────────────────────────────────
    div2_y = div1_y + 34 + stat_gap * len(stats) + 14
    def sep2(d):
        d.rectangle([(PAD, div2_y), (KART_W - PAD, div2_y + 2)],
                    fill=(255, 255, 255, 22))
    kart, draw = _composite(kart, sep2)

    # ── EXP bolumu — tam genislik, sade ───────────────────────
    xp_y  = div2_y + 32
    bar_x = PAD
    bar_w = KART_W - PAD * 2   # 628 px
    bar_h = 26

    pct    = int(min(exp / max(gereken_exp, 1), 1.0) * 100)
    xp_str = f"{exp:,} / {gereken_exp:,}"
    pct_str = f"%{pct}"

    draw.text((bar_x, xp_y), xp_str, font=fn_xp, fill=MUTED)
    bbox = draw.textbbox((0, 0), pct_str, font=fn_xp)
    draw.text((bar_x + bar_w - (bbox[2] - bbox[0]), xp_y), pct_str, font=fn_xp, fill=WHITE)

    kart = _xp_bar(kart, bar_x, xp_y + 34, bar_w, bar_h, exp, gereken_exp, acc)
    draw = ImageDraw.Draw(kart)

    draw.text((bar_x, xp_y + 34 + bar_h + 10),
              f"TOTAL XP: {exp:,}", font=fn_xpl, fill=MUTED)

    # ── Alt accent seridi ─────────────────────────────────────
    def stripe(d):
        d.rectangle([(0, KART_H - 8), (KART_W, KART_H)], fill=(*acc, 228))
    kart, _ = _composite(kart, stripe)

    # ── Supersampling: render 700x940 → LANCZOS → 350x470 ────
    dark  = Image.new("RGBA", (KART_W, KART_H), (8, 8, 14, 255))
    final = Image.alpha_composite(dark, kart)
    final = final.resize((OUT_W, OUT_H), Image.LANCZOS)

    buf = io.BytesIO()
    final.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
