"""utils/mac_gorseli.py — Sinematik animasyonlu maç banner GIF üretici."""

import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H       = 640, 240
LOGO_BOY   = (150, 150)
FRAMES     = 40        # toplam frame
FPS_MS     = 40        # ms / frame (~25fps)
BG_COLOR   = (15, 15, 20)
GOLD       = (255, 200, 0)
WHITE      = (240, 240, 240)
DARK_GREY  = (40, 40, 50)


def _logo_indir(url: str) -> Image.Image:
    try:
        r   = requests.get(url, timeout=6)
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img = img.resize(LOGO_BOY, Image.LANCZOS)
        return img
    except Exception:
        img = Image.new("RGBA", LOGO_BOY, (60, 60, 70, 255))
        return img


def _font(size: int):
    yollar = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for y in yollar:
        try:
            return ImageFont.truetype(y, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _ciz_yildiz_arkaplan(draw, t):
    """Hareketli parıldayan arka plan noktaları."""
    import random
    rng = random.Random(42)
    for _ in range(60):
        x  = rng.randint(0, W)
        y  = rng.randint(0, H)
        r  = rng.randint(1, 2)
        br = int(80 + 60 * math.sin(t * 0.3 + rng.random() * 6))
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(br, br, br+20, 255))


def _logo_glow(logo: Image.Image, renk=(255,200,0), siddet=18) -> Image.Image:
    """Logo etrafına parlayan halo ekle."""
    glow_layer = Image.new("RGBA", (LOGO_BOY[0]+siddet*2, LOGO_BOY[1]+siddet*2), (0,0,0,0))
    mask       = logo.split()[3] if logo.mode == "RGBA" else logo.convert("RGBA").split()[3]
    colored    = Image.new("RGBA", LOGO_BOY, renk + (180,))
    glow_layer.paste(colored, (siddet, siddet), mask)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(siddet // 2))
    glow_layer.paste(logo, (siddet, siddet), logo)
    return glow_layer


def mac_banner_olustur(ev_logo_url: str, dep_logo_url: str, ev_isim: str, dep_isim: str) -> io.BytesIO:
    ev_logo  = _logo_indir(ev_logo_url)
    dep_logo = _logo_indir(dep_logo_url)

    f_isim = _font(22)
    f_vs   = _font(56)
    f_vs_s = _font(32)

    kareler = []

    for frame in range(FRAMES):
        t        = frame / FRAMES  # 0.0 → 1.0
        ease_t   = 1 - (1 - t) ** 3  # ease-out cubic

        bg = Image.new("RGBA", (W, H), BG_COLOR + (255,))
        draw = ImageDraw.Draw(bg)

        # Yıldız arka plan
        _ciz_yildiz_arkaplan(draw, frame)

        # Ortadaki çizgi / ışık huzmesi
        if t > 0.4:
            huz_alpha = int(min(255, (t - 0.4) / 0.3 * 180))
            huz_w     = int(W * 0.6)
            huz_x     = (W - huz_w) // 2
            for dy in range(-4, 5):
                a = max(0, huz_alpha - abs(dy) * 30)
                draw.line([(huz_x, H//2 + dy), (huz_x + huz_w, H//2 + dy)],
                          fill=(255, 220, 80, a), width=1)

        # Logo pozisyonları — iki yandan gelir
        logo_y = (H - LOGO_BOY[1]) // 2 - 10

        # Sol logo (ev) — soldan gelir
        hedef_sol = 35
        baslangic_sol = -LOGO_BOY[0] - 20
        sol_x = int(baslangic_sol + (hedef_sol - baslangic_sol) * ease_t)

        # Sağ logo (dep) — sağdan gelir
        hedef_sag = W - 35 - LOGO_BOY[0]
        baslangic_sag = W + 20
        sag_x = int(baslangic_sag + (hedef_sag - baslangic_sag) * ease_t)

        # Glow efekti — gelişe göre artar
        glow_siddet = int(ease_t * 20)
        ev_glow  = _logo_glow(ev_logo,  (100, 150, 255), max(4, glow_siddet))
        dep_glow = _logo_glow(dep_logo, (255, 80,  80),  max(4, glow_siddet))

        g = glow_siddet
        bg.paste(ev_glow,  (sol_x - g, logo_y - g), ev_glow)
        bg.paste(dep_glow, (sag_x - g, logo_y - g), dep_glow)

        # VS yazısı — ortada belirir, önce büyükçe sonra yerleşir
        if t > 0.5:
            vs_t      = (t - 0.5) / 0.5  # 0→1 ikinci yarıda
            vs_ease   = 1 - (1 - vs_t) ** 2
            vs_alpha  = int(vs_ease * 255)
            vs_scale  = 1.4 - 0.4 * vs_ease  # büyükten normale
            vs_size   = int(56 * vs_scale)
            f_vs_cur  = _font(vs_size)

            # Yanıp sönme son 8 frame'de
            if frame > FRAMES - 8:
                flash = frame % 2 == 0
                vs_alpha = 255 if flash else 160

            vs_text = "VS"
            bbox    = draw.textbbox((0,0), vs_text, font=f_vs_cur)
            vs_w    = bbox[2] - bbox[0]
            vs_h    = bbox[3] - bbox[1]
            vx      = (W - vs_w) // 2
            vy      = (H - vs_h) // 2 - 8

            # Gölge
            draw.text((vx+3, vy+3), vs_text, font=f_vs_cur, fill=(0,0,0,vs_alpha//2))
            # VS
            draw.text((vx, vy), vs_text, font=f_vs_cur,
                      fill=(int(GOLD[0]), int(GOLD[1]), int(GOLD[2]), vs_alpha))

        # Takım isimleri
        if t > 0.6:
            isim_alpha = int(min(255, (t - 0.6) / 0.3 * 255))
            for isim, cx in [(ev_isim, hedef_sol + LOGO_BOY[0]//2),
                             (dep_isim, hedef_sag + LOGO_BOY[0]//2)]:
                bbox = draw.textbbox((0,0), isim, font=f_isim)
                tw   = bbox[2] - bbox[0]
                draw.text((cx - tw//2 + 1, H - 30), isim, font=f_isim,
                          fill=(0,0,0,isim_alpha//2))
                draw.text((cx - tw//2, H - 31), isim, font=f_isim,
                          fill=(WHITE[0], WHITE[1], WHITE[2], isim_alpha))

        kareler.append(bg.convert("RGB"))

    # Son 5 frame'i beklet (kapanışta dur)
    for _ in range(5):
        kareler.append(kareler[-1])

    buf = io.BytesIO()
    kareler[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=kareler[1:],
        duration=FPS_MS,
        loop=0,
        optimize=False,
    )
    buf.seek(0)
    return buf
