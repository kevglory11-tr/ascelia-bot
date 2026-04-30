# utils/profil_karti.py — Profil karti v3: portrait, geometric rhombus bg

import io
import os
import glob
import math
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KART_W  = 360
KART_H  = 490
AV_SIZE = 96
PAD     = 18

STAT_COL_END = 140   # sol stat sütununun bittigi x
BAR_X        = STAT_COL_END + 14
BAR_W        = KART_W - BAR_X - PAD   # 188px


# ── Font keşfi (Railway + Windows) ────────────────────────────────────────────

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
            direct = os.path.join(d, name)
            if os.path.exists(direct):
                return direct
        for d in dirs:
            if not os.path.isdir(d):
                continue
            matches = glob.glob(os.path.join(d, "**", name), recursive=True)
            if matches:
                return matches[0]
    return None


_BOLD  = _find_font_path(["DejaVuSans-Bold.ttf",    "LiberationSans-Bold.ttf",
                           "FreeSansBold.ttf",        "Ubuntu-B.ttf",  "arialbd.ttf"])
_PLAIN = _find_font_path(["DejaVuSans.ttf",          "LiberationSans-Regular.ttf",
                           "FreeSans.ttf",            "Ubuntu-R.ttf",  "arial.ttf"])


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = _BOLD if bold else _PLAIN
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ── Yardimcılar ───────────────────────────────────────────────────────────────

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


def _rotated_rect(cx: float, cy: float, w: float, h: float, angle_deg: float) -> list:
    rad     = math.radians(angle_deg)
    cos_a   = math.cos(rad)
    sin_a   = math.sin(rad)
    hw, hh  = w / 2, h / 2
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    return [(int(cx + x * cos_a - y * sin_a), int(cy + x * sin_a + y * cos_a))
            for x, y in corners]


# ── Arka plan ─────────────────────────────────────────────────────────────────

def _build_bg(renk_hex: str) -> Image.Image:
    r, g, b = _parse_hex(renk_hex)
    acc     = _accent(renk_hex)

    # Cok karanlik taban
    base = (max(r // 9, 7), max(g // 9, 7), max(b // 7 + 4, 12))
    img  = Image.new("RGBA", (KART_W, KART_H), (*base, 255))

    # Geometrik rhombus katmanlar — sag tarafa yogunlastirilmis
    shapes = [
        # cx_r  cy_r   w    h   ang  alpha  r+   g+   b+
        (0.80,  0.24,  300, 480,  45,   52,   70,  50, 115),
        (0.62,  0.12,  230, 390,  45,   38,   55,  38,  90),
        (0.96,  0.65,  270, 440,  45,   35,   60,  45, 105),
        (0.48,  0.07,  160, 300,  45,   28,   40,  28,  68),
        (0.88,  0.90,  210, 350,  45,   22,   65,  48, 108),
        (0.32,  0.58,  120, 240,  45,   16,   28,  20,  50),
    ]
    for cx_r, cy_r, sw, sh, ang, alpha, ra, ga, ba in shapes:
        pts   = _rotated_rect(KART_W * cx_r, KART_H * cy_r, sw, sh, ang)
        layer = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
        col   = (min(acc[0] + ra, 255), min(acc[1] + ga, 255), min(acc[2] + ba, 255), alpha)
        ImageDraw.Draw(layer).polygon(pts, fill=col)
        img = Image.alpha_composite(img, layer)

    # Sol tarafi biraz karatarak stat okunakliligini artir
    vignette = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
    v_draw   = ImageDraw.Draw(vignette)
    for x in range(STAT_COL_END + 20):
        a = int(60 * (1 - x / (STAT_COL_END + 20)))
        v_draw.line([(x, 0), (x, KART_H)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, vignette)

    return img


# ── XP bar ────────────────────────────────────────────────────────────────────

def _xp_bar(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
             exp: int, gereken: int, acc: tuple) -> None:
    oran = min(exp / max(gereken, 1), 1.0)
    dolu = int(w * oran)
    r    = h // 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=(12, 12, 24, 210))
    if dolu > r * 2:
        draw.rounded_rectangle([x, y, x + dolu, y + h], radius=r, fill=(*acc, 255))
        sw = max(dolu - 6, 0)
        if sw:
            draw.rounded_rectangle([x + 3, y + 2, x + 3 + sw, y + h // 2],
                                   radius=2, fill=(255, 255, 255, 50))


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

    # ── Arkaplan ──────────────────────────────────────────────
    if arka_plan_url:
        raw = await _fetch(arka_plan_url, (KART_W, KART_H))
    else:
        raw = None

    if raw:
        kart = raw.convert("RGBA").filter(ImageFilter.GaussianBlur(2))
        kart = Image.alpha_composite(kart, Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 135)))
    else:
        kart = _build_bg(renk_hex)

    draw = ImageDraw.Draw(kart)

    # ── Fontlar ───────────────────────────────────────────────
    fn_name  = _font(22, bold=True)
    fn_label = _font(10, bold=False)
    fn_stat  = _font(28, bold=True)
    fn_sub   = _font(11, bold=False)
    fn_xp    = _font(10, bold=False)
    fn_bio   = _font(10, bold=False)

    WHITE  = (255, 255, 255, 255)
    MUTED  = (165, 165, 195, 210)
    ACCENT = (*acc, 235)

    # ── Avatar ────────────────────────────────────────────────
    av_x  = PAD
    av_y  = PAD
    av_cx = av_x + AV_SIZE // 2
    av_cy = av_y + AV_SIZE // 2

    # Avatar golgesi
    shadow = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 0))
    sr = AV_SIZE // 2 + 9
    ImageDraw.Draw(shadow).ellipse([av_cx - sr, av_cy - sr, av_cx + sr, av_cy + sr],
                                   fill=(0, 0, 0, 90))
    kart = Image.alpha_composite(kart, shadow)
    draw = ImageDraw.Draw(kart)

    # Accent halka
    ring_r = AV_SIZE // 2 + 3
    draw.ellipse([av_cx - ring_r, av_cy - ring_r, av_cx + ring_r, av_cy + ring_r],
                 outline=(*acc, 255), width=3)

    # Avatar gorsel
    av_img = await _fetch(avatar_url, (AV_SIZE, AV_SIZE))
    if av_img:
        circle = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        circle.paste(av_img.convert("RGBA"), (0, 0), _circle_mask(AV_SIZE))
        kart.paste(circle, (av_x, av_y), circle)
    else:
        draw.ellipse([av_x, av_y, av_x + AV_SIZE, av_y + AV_SIZE], fill=(55, 55, 78, 200))

    # Rozet badge (avatar alt-sag kosesi)
    badge_cx = av_x + AV_SIZE - 2
    badge_cy = av_y + AV_SIZE - 2
    br = 12
    draw.ellipse([badge_cx - br, badge_cy - br, badge_cx + br, badge_cy + br],
                 fill=(*acc, 230), outline=(255, 255, 255, 160), width=2)

    # ── Kullanici adi (avatar sagi) ───────────────────────────
    tx     = av_x + AV_SIZE + 12
    name_y = av_y + 10
    draw.text((tx, name_y), kullanici_adi[:18], font=fn_name, fill=WHITE)

    # Bio (kullanici adi altinda)
    if bio:
        draw.text((tx, name_y + 28), bio[:34], font=fn_bio, fill=MUTED)

    # Aktif rozet pill
    if aktif_rozet:
        rozet_y = name_y + (46 if bio else 32)
        rtxt    = aktif_rozet[:22]
        bbox    = draw.textbbox((0, 0), rtxt, font=fn_sub)
        pw      = bbox[2] - bbox[0] + 16
        ph      = 18
        pill    = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2,
                                               fill=(*acc, 48), outline=(*acc, 150), width=1)
        kart.paste(pill, (tx, rozet_y), pill)
        draw.text((tx + 8, rozet_y + 3), rtxt, font=fn_sub, fill=ACCENT)

    # ── Yatay ayirac ──────────────────────────────────────────
    div_y = av_y + AV_SIZE + 16
    draw.rectangle([(PAD, div_y), (KART_W - PAD, div_y + 1)], fill=(255, 255, 255, 28))

    # ── Sol sütun statlar ─────────────────────────────────────
    stats = [
        ("LVL",      str(level)),
        ("COINS",    f"{bakiye:,}"),
        ("SIRALAMA", f"#{siralama:,}"),
    ]

    sy      = div_y + 18
    stat_gap = 58

    for lbl, val in stats:
        draw.text((PAD, sy),      lbl, font=fn_label, fill=MUTED)
        draw.text((PAD, sy + 13), val, font=fn_stat,  fill=WHITE)
        sy += stat_gap

    # ── Sag sutun: XP bar (son stat ile ayni dikey hiza) ─────
    xp_top_y = div_y + 18 + stat_gap * (len(stats) - 1)  # son statin y'si

    oran    = int(min(exp / max(gereken_exp, 1), 1.0) * 100)
    xp_left = f"{exp:,} / {gereken_exp:,}"
    xp_pct  = f"%{oran}"

    draw.text((BAR_X, xp_top_y), xp_left, font=fn_xp, fill=WHITE)
    bbox = draw.textbbox((0, 0), xp_pct, font=fn_xp)
    draw.text((BAR_X + BAR_W - (bbox[2] - bbox[0]), xp_top_y), xp_pct, font=fn_xp, fill=MUTED)

    bar_y = xp_top_y + 14
    _xp_bar(draw, BAR_X, bar_y, BAR_W, 14, exp, gereken_exp, acc)

    total_lbl = f"TOTAL EXP: {exp:,}"
    draw.text((BAR_X, bar_y + 18), total_lbl, font=fn_label, fill=MUTED)

    # ── Alt accent seridi ─────────────────────────────────────
    draw.rectangle([(0, KART_H - 5), (KART_W, KART_H)], fill=(*acc, 230))

    # ── Cikti ─────────────────────────────────────────────────
    buf = io.BytesIO()
    kart.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
