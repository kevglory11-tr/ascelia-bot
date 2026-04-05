"""
utils/patron_gorseli.py — Patron savaş görseli üretici.
Her saldırıda Alastor görseli üzerine hasar efekti overlay oluşturur.
"""
from __future__ import annotations

import io, os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_KOK       = Path(__file__).resolve().parent.parent
PATRON_IMG = _KOK / "assets" / "patron.png"
_BOT_FONT  = _KOK / "assets" / "font.ttf"

_FB = [
    str(_BOT_FONT) if _BOT_FONT.is_file() else "",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_FI = [
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(paths, size):
    for p in paths:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hp_renk(oran: float) -> tuple:
    """HP oranına göre renk: yeşil → sarı → kırmızı."""
    if oran > 0.5:
        # Yeşil → Sarı
        t = (1 - oran) * 2
        r = int(t * 255)
        g = 200
        b = 0
    else:
        # Sarı → Kırmızı
        t = oran * 2
        r = 220
        g = int(t * 200)
        b = 0
    return (r, g, b)


def _perk_renk(crit: bool, guclu: bool, crit_hasar: bool) -> tuple:
    """Aktif perke göre hasar sayısı rengi."""
    if crit and crit_hasar:
        return (255, 80, 255)   # Mor — çift perk (kritik + kritik hasar)
    if crit:
        return (255, 165, 0)    # Turuncu — kritik şans
    if guclu:
        return (255, 80, 80)    # Kırmızı — güçlü darbe
    return (255, 255, 255)      # Beyaz — normal


def patron_gorseli_olustur(
    hp: int,
    max_hp: int,
    hasar: int,
    crit: bool,
    guclu_darbe: bool,
    crit_hasar: bool,
    kullanici_isim: str,
) -> io.BytesIO:
    """
    Patron PNG'si üzerine:
    - HP bar (renk değişken)
    - Hasar sayısı (perk renkli, eğik, gölgeli)
    - Kanlı çatlak overlay (crit ise daha yoğun)
    - Karartma efekti (HP azaldıkça artar)
    """
    W, H = 600, 400

    # ── Arka görsel ────────────────────────────────────────────
    if PATRON_IMG.is_file():
        try:
            base = Image.open(PATRON_IMG).convert("RGBA").resize((W, H), Image.LANCZOS)
        except Exception:
            base = Image.new("RGBA", (W, H), (20, 0, 0, 255))
    else:
        base = Image.new("RGBA", (W, H), (20, 0, 0, 255))

    # ── HP azaldıkça karartma ──────────────────────────────────
    hp_oran = hp / max_hp
    karanlik = int((1 - hp_oran) * 140)
    karanlik_ov = Image.new("RGBA", (W, H), (0, 0, 0, karanlik))
    base = Image.alpha_composite(base, karanlik_ov)

    # ── Kanlı kırmızı overlay (hasar anı) ─────────────────────
    kan_yogunluk = 80 if crit else 45
    kan_ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    kd = ImageDraw.Draw(kan_ov)

    # Köşelerden kırmızı vinyet
    for i in range(40):
        a = int((1 - i / 40) * kan_yogunluk)
        kd.rectangle([i, i, W - i, H - i], outline=(180, 0, 0, a), width=1)

    # Rastgele çatlak çizgileri
    sayi = 6 if crit else 3
    for _ in range(sayi):
        x1 = random.randint(0, W)
        y1 = random.randint(0, H // 2)
        x2 = x1 + random.randint(-80, 80)
        y2 = y1 + random.randint(20, 120)
        a  = random.randint(120, 200)
        kd.line([(x1, y1), (x2, y2)], fill=(200, 0, 0, a), width=random.randint(1, 3))
        # Dallanma
        x3 = x2 + random.randint(-30, 30)
        y3 = y2 + random.randint(10, 50)
        kd.line([(x2, y2), (x3, y3)], fill=(180, 0, 0, a - 40), width=1)

    base = Image.alpha_composite(base, kan_ov)

    draw = ImageDraw.Draw(base)

    # ── HP Bar ────────────────────────────────────────────────
    bar_x, bar_y = 20, H - 54
    bar_w, bar_h = W - 40, 22
    r_bar = 8

    # Arka plan
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                            radius=r_bar, fill=(30, 0, 0, 220))

    # Dolu kısım
    dolu_w = max(0, int((hp / max_hp) * bar_w))
    hp_r, hp_g, hp_b = _hp_renk(hp_oran)
    if dolu_w > r_bar * 2:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + dolu_w, bar_y + bar_h],
                                radius=r_bar, fill=(hp_r, hp_g, hp_b, 230))
    elif dolu_w > 0:
        draw.rectangle([bar_x, bar_y, bar_x + dolu_w, bar_y + bar_h],
                       fill=(hp_r, hp_g, hp_b, 230))

    # HP yazısı
    f_hp   = _font(_FB, 13)
    hp_txt = f"❤ {hp} / {max_hp}"
    tw, th = ImageDraw.Draw(Image.new("RGBA", (1,1))).textbbox((0,0), hp_txt, font=f_hp)[2:]
    draw.text((bar_x + bar_w // 2 - tw // 2, bar_y + bar_h // 2 - th // 2),
              hp_txt, font=f_hp, fill=(255, 255, 255, 255))

    # Bar çerçeve
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                            radius=r_bar, outline=(255, 255, 255, 80), width=1)

    # ── Hasar Sayısı ─────────────────────────────────────────
    f_hasar = _font(_FB, 52 if crit else 42)
    hasar_txt = f"-{hasar}"
    if crit:
        hasar_txt = f"💥 -{hasar}!"

    h_renk = _perk_renk(crit, guclu_darbe, crit_hasar)

    # Gölge
    draw.text((W // 2 - 2 + 3, 28 + 3), hasar_txt, font=f_hasar, fill=(0, 0, 0, 180))
    # Ana yazı
    draw.text((W // 2 - 2, 28), hasar_txt, font=f_hasar, fill=(*h_renk, 255))

    # ── Perk etiketi ─────────────────────────────────────────
    perk_etiket = ""
    if crit and crit_hasar:
        perk_etiket = "⚡ KRİTİK + HASAR ARTTI"
        et_renk     = (255, 80, 255)
    elif crit:
        perk_etiket = "⚡ KRİTİK VURUŞ"
        et_renk     = (255, 165, 0)
    elif guclu_darbe:
        perk_etiket = "💪 GÜÇLÜ DARBE"
        et_renk     = (255, 80, 80)

    if perk_etiket:
        f_et = _font(_FB, 16)
        tw2, _ = ImageDraw.Draw(Image.new("RGBA",(1,1))).textbbox((0,0), perk_etiket, font=f_et)[2:]
        # Pill arka plan
        px = W // 2 - tw2 // 2 - 8
        py = 86
        draw.rounded_rectangle([px, py, px + tw2 + 16, py + 24], radius=10,
                                fill=(*et_renk[:3], 55))
        draw.rounded_rectangle([px, py, px + tw2 + 16, py + 24], radius=10,
                                outline=(*et_renk[:3], 160), width=1)
        draw.text((px + 8, py + 4), perk_etiket, font=f_et, fill=(*et_renk, 255))

    # ── Kullanıcı adı (alt sol) ────────────────────────────
    f_isim = _font(_FI, 13)
    draw.text((bar_x + 2, bar_y - 22), f"⚔ {kullanici_isim}", font=f_isim,
              fill=(200, 200, 200, 210))

    # ── Hafif blur ile son rötuş ──────────────────────────
    # Sadece kan overlay'i blur'lanmış hissi için kenarları yumuşat
    final = base.convert("RGB")

    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
