# utils/profil_karti.py — Profil karti uretici v2
# Tamamen yeniden tasarlandi: modern layout, bio kart icinde, accent renk sistemi.

import io
import os
import glob
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KART_W   = 960
KART_H   = 300
AV_SIZE  = 112   # avatar diameter
PAD      = 20    # genel kenar boslugu
LEFT_BAR = 4     # sol accent cubugu genisligi
TEXT_X   = PAD + LEFT_BAR + AV_SIZE + 22   # metin baslangiç x


# ── Font bulma (Railway + Windows destekli) ────────────────────────────────────

def _find_font_path(names: list[str]) -> str | None:
    dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/run/current-system/sw/share/fonts",
        "/nix/store",
        "C:/Windows/Fonts",
    ]
    for name in names:
        # Direct check first (fast)
        for d in dirs:
            direct = os.path.join(d, name)
            if os.path.exists(direct):
                return direct
        # Recursive search
        for d in dirs:
            if not os.path.isdir(d):
                continue
            matches = glob.glob(os.path.join(d, "**", name), recursive=True)
            if matches:
                return matches[0]
    return None


_FONT_BOLD_PATH  = _find_font_path([
    "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
    "FreeSansBold.ttf", "Ubuntu-B.ttf", "arialbd.ttf",
])
_FONT_PLAIN_PATH = _find_font_path([
    "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
    "FreeSans.ttf", "Ubuntu-R.ttf", "arial.ttf",
])


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD_PATH if bold else _FONT_PLAIN_PATH
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ── Yardimci fonksiyonlar ──────────────────────────────────────────────────────

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


def _parse_hex(renk_hex: str) -> tuple[int, int, int]:
    try:
        h = renk_hex.strip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return (43, 45, 49)


def _accent(renk_hex: str) -> tuple[int, int, int]:
    r, g, b = _parse_hex(renk_hex)
    m = max(r, g, b)
    if m < 90:
        f = 200 / max(m, 1)
        r, g, b = min(int(r * f), 255), min(int(g * f), 255), min(int(b * f), 255)
    return (r, g, b)


def _build_background(renk_hex: str) -> Image.Image:
    r, g, b = _parse_hex(renk_hex)
    # Cok karanlik yap, hafif gradient
    dr = max(r // 6, 10)
    dg = max(g // 6, 10)
    db = max(b // 6 + 8, 15)
    img = Image.new("RGBA", (KART_W, KART_H), (dr, dg, db, 255))
    # Sola dogru hafif aydinlanma
    draw = ImageDraw.Draw(img)
    for x in range(200):
        a = int(14 * (1 - x / 200))
        draw.line([(x + LEFT_BAR, 0), (x + LEFT_BAR, KART_H)], fill=(255, 255, 255, a))
    return img


def _draw_xp_bar(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
                  exp: int, gereken: int, acc: tuple):
    oran = min(exp / max(gereken, 1), 1.0)
    dolu = int(w * oran)
    r = h // 2
    # Arkaplan
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=(20, 20, 35, 220))
    # Dolu kisim
    if dolu > r:
        draw.rounded_rectangle([x, y, x + dolu, y + h], radius=r, fill=(*acc, 255))
        # Parlama
        shine_w = max(dolu - 6, 0)
        if shine_w > 0:
            draw.rounded_rectangle([x + 3, y + 2, x + 3 + shine_w, y + h // 2],
                                   radius=2, fill=(255, 255, 255, 40))


# ── Ana fonksiyon ──────────────────────────────────────────────────────────────

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
        bg = await _fetch(arka_plan_url, (KART_W, KART_H))
    else:
        bg = None

    if bg:
        kart = bg.convert("RGBA").filter(ImageFilter.GaussianBlur(3))
        # Karanlik overlay
        overlay = Image.new("RGBA", (KART_W, KART_H), (0, 0, 0, 150))
        kart.paste(overlay, (0, 0), overlay)
    else:
        kart = _build_background(renk_hex)

    draw = ImageDraw.Draw(kart)

    # ── Sol accent cubugu ──────────────────────────────────────
    draw.rectangle([(0, 0), (LEFT_BAR - 1, KART_H)], fill=(*acc, 255))

    # ── Sol karanlik panel (avatar alani) ─────────────────────
    panel_w = PAD + LEFT_BAR + AV_SIZE + 14
    panel = Image.new("RGBA", (panel_w, KART_H), (0, 0, 0, 90))
    kart.paste(panel, (0, 0), panel)

    # ── Avatar ────────────────────────────────────────────────
    av_x = LEFT_BAR + PAD
    av_y = (KART_H - AV_SIZE) // 2   # dikey ortalama

    # Dis halka (accent rengi, 3px)
    ring_r = AV_SIZE // 2 + 4
    ring_cx = av_x + AV_SIZE // 2
    ring_cy = av_y + AV_SIZE // 2
    draw.ellipse(
        [ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r],
        outline=(*acc, 255), width=3
    )

    av_img = await _fetch(avatar_url, (AV_SIZE, AV_SIZE))
    if av_img:
        circle = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        circle.paste(av_img.convert("RGBA"), (0, 0), _circle_mask(AV_SIZE))
        kart.paste(circle, (av_x, av_y), circle)
    else:
        draw.ellipse([av_x, av_y, av_x + AV_SIZE, av_y + AV_SIZE], fill=(60, 60, 80, 200))

    # ── Metin alani ───────────────────────────────────────────
    fn_name  = _font(24, bold=True)
    fn_sub   = _font(12, bold=False)
    fn_label = _font(10, bold=False)
    fn_val   = _font(19, bold=True)
    fn_xp    = _font(11, bold=False)

    WHITE  = (255, 255, 255, 255)
    MUTED  = (180, 180, 200, 200)
    ACCENT = (*acc, 230)

    tx = TEXT_X
    ty = 22

    # Kullanici adi
    isim = kullanici_adi[:22]
    draw.text((tx, ty), isim, font=fn_name, fill=WHITE)
    ty += 32

    # Bio (kart icinde, accent rengiyle)
    if bio:
        bio_display = bio[:52]
        draw.text((tx, ty), bio_display, font=fn_sub, fill=MUTED)
        ty += 20

    # Aktif rozet (pill seklinde)
    if aktif_rozet:
        rozet_txt = aktif_rozet[:32]
        bbox = draw.textbbox((0, 0), rozet_txt, font=fn_sub)
        pill_w = bbox[2] - bbox[0] + 20
        pill_h = 20
        # Pill arkaplan
        pill_img = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
        ImageDraw.Draw(pill_img).rounded_rectangle(
            [0, 0, pill_w - 1, pill_h - 1], radius=pill_h // 2,
            fill=(*acc, 60), outline=(*acc, 160), width=1
        )
        kart.paste(pill_img, (tx, ty), pill_img)
        draw.text((tx + 10, ty + 3), rozet_txt, font=fn_sub, fill=ACCENT)
        ty += 26

    # ── Yatay ayirac ──────────────────────────────────────────
    sep_y = 148
    draw.rectangle([(LEFT_BAR, sep_y), (KART_W - PAD, sep_y + 1)], fill=(255, 255, 255, 35))

    # ── Istatistik satirlari ───────────────────────────────────
    stat_y = sep_y + 14
    stats = [
        ("COINS",  f"{bakiye:,}"),
        ("SIRALAMA", f"#{siralama:,}"),
        ("LEVEL",  str(level)),
    ]
    col_w = 140
    for i, (lbl, val) in enumerate(stats):
        sx = tx + i * col_w
        draw.text((sx, stat_y),      lbl, font=fn_label, fill=MUTED)
        draw.text((sx, stat_y + 14), val, font=fn_val,   fill=WHITE)

    # Dikey ayirac satirlarda
    for i in range(1, len(stats)):
        dx = tx + i * col_w - 12
        draw.rectangle([(dx, stat_y), (dx + 1, stat_y + 36)], fill=(255, 255, 255, 25))

    # ── EXP bar ───────────────────────────────────────────────
    bar_y = KART_H - 50
    bar_x = tx
    bar_w = KART_W - tx - PAD
    bar_h = 14

    draw.text((bar_x, bar_y - 16), "EXP", font=fn_label, fill=MUTED)
    oran = int(min(exp / max(gereken_exp, 1), 1.0) * 100)
    xp_txt = f"{exp:,} / {gereken_exp:,}  •  %{oran}"
    bbox = draw.textbbox((0, 0), xp_txt, font=fn_xp)
    draw.text((bar_x + bar_w - (bbox[2] - bbox[0]), bar_y - 16),
              xp_txt, font=fn_xp, fill=MUTED)

    _draw_xp_bar(draw, bar_x, bar_y, bar_w, bar_h, exp, gereken_exp, acc)

    # ── Alt accent seridi ──────────────────────────────────────
    draw.rectangle([(0, KART_H - 5), (KART_W, KART_H)], fill=(*acc, 220))

    # ── Cikti ─────────────────────────────────────────────────
    buf = io.BytesIO()
    kart.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
