"""utils/mac_gorseli.py — Profesyonel sinematik futbol maç banner GIF."""

import io, math, random, os
import numpy as np
import requests
import imageio
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H     = 640, 260
M2B_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "m2board_logo.png")
LOGO_BOY = (85, 85)
FRAMES   = 52
FPS      = 22

def _font(size):
    for yol in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        try: return ImageFont.truetype(yol, size)
        except: continue
    return ImageFont.load_default()

def _logo_indir(url):
    try:
        r = requests.get(url, timeout=6)
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img = img.resize(LOGO_BOY, Image.LANCZOS)
        return img
    except:
        return Image.new("RGBA", LOGO_BOY, (60,60,70,255))

def _ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1-t)**3

def _stadyum(t, puls):
    """Gerçekçi futbol banner arka planı."""
    import os
    bg_path = os.path.join(os.path.dirname(__file__), "..", "assets", "mac_bg.png")
    try:
        bg = Image.open(bg_path).convert("RGBA").resize((W, H), Image.LANCZOS)
    except Exception:
        bg = Image.new("RGBA", (W, H), (10, 20, 40, 255))

    # Hafif karartma overlay — logolar ve yazı daha iyi görünsün
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 60))
    bg = Image.alpha_composite(bg, overlay)
    return bg

def _render_frame(ev_logo, dep_logo, ev_isim, dep_isim, frame):
    t    = frame / FRAMES
    puls = 0.5 + 0.5*math.sin(t*5)
    ease = _ease_out(t/0.58)

    bg   = _stadyum(t, puls)
    draw = ImageDraw.Draw(bg)

    logo_y  = H//2 - LOGO_BOY[1]//2 + 22
    sol_x   = int(-LOGO_BOY[0] + (48+LOGO_BOY[0])*ease)
    sag_x   = int(W + (W-48-LOGO_BOY[0]-W)*ease)

    # Çarpışma sarsıntısı
    if 0.56 < t < 0.70:
        s = int(math.sin((t-0.56)*58)*8*(1-(t-0.56)/0.14))
        sol_x += s; sag_x -= s

    cx_sol = sol_x + LOGO_BOY[0]//2
    cx_sag = sag_x + LOGO_BOY[0]//2
    cy_log = logo_y + LOGO_BOY[1]//2

    # Logo glow
    glow = Image.new("RGBA",(W,H),(0,0,0,0))
    gd   = ImageDraw.Draw(glow)
    for g in range(8,0,-1):
        fa = max(0, int(40+puls*22)-g*5)
        gr = 65+g*10
        gd.ellipse([cx_sol-gr,cy_log-gr,cx_sol+gr,cy_log+gr], fill=(30,80,255,fa))
        gd.ellipse([cx_sag-gr,cy_log-gr,cx_sag+gr,cy_log+gr], fill=(255,50,20,fa))
    glow_b = glow.filter(ImageFilter.GaussianBlur(16))
    bg = Image.alpha_composite(bg, glow_b)
    draw = ImageDraw.Draw(bg)

    # Alev parçacıkları
    for cx, seed_offset in [(cx_sol,0),(cx_sag,99)]:
        rng = random.Random(seed_offset + frame*3)
        for _ in range(26):
            s    = rng.random()
            life = (t*2.6+s*0.8) % 1.0
            fx   = cx + int(math.sin(s*14+t*6)*36*life)
            fy   = logo_y + LOGO_BOY[1] - int(life*95+s*14)
            fr   = max(1, int((1-life)*7))
            fa   = int((1-life)*240)
            if fa < 20: continue
            if life < 0.3:   fc=(255,230,60,fa)
            elif life < 0.6: fc=(255,130,10,fa)
            else:            fc=(195,20,5,fa)
            draw.ellipse([fx-fr,fy-fr,fx+fr,fy+fr], fill=fc)

    # Logoları yapıştır
    bg.paste(ev_logo,  (sol_x, logo_y), ev_logo.split()[3])
    bg.paste(dep_logo, (sag_x, logo_y), dep_logo.split()[3])

    # M2Board logosu — üst orta, daha büyük ve glow'lu
    try:
        m2b_src = Image.open(M2B_LOGO_PATH).convert("RGBA")
        # Banner genişliğinin %45'i kadar yap
        m2b_w = int(W * 0.52)
        m2b_h = int(m2b_w * m2b_src.height / m2b_src.width)
        m2b   = m2b_src.resize((m2b_w, m2b_h), Image.LANCZOS)
        mx    = (W - m2b_w) // 2
        my    = 2
        # Belirgin glow ekle
        for gb in [12, 7]:
            glow_l = Image.new("RGBA", (W, H), (0,0,0,0))
            glow_l.paste(m2b, (mx, my), m2b.split()[3])
            bg = Image.alpha_composite(bg, glow_l.filter(ImageFilter.GaussianBlur(gb)))
        bg.paste(m2b, (mx, my), m2b.split()[3])
    except Exception:
        pass

    draw = ImageDraw.Draw(bg)

    # Şok dalgası efekti kaldırıldı

    # VS yazısı — metalik gradient efekti
    f_vs = _font(48)
    if t > 0.37:
        vs_ease = _ease_out(min((t-0.37)/0.18, 1.0))
        pulse   = 1.0
        if frame > FRAMES - 12:
            pulse = 1.0 if (frame % 3) != 1 else 0.55

        bbox = draw.textbbox((0,0),"VS",font=f_vs)
        vw,vh = bbox[2]-bbox[0], bbox[3]-bbox[1]
        vx = (W-vw)//2
        vy = logo_y + LOGO_BOY[1]//2 - vh//2 + 16

        # Dış derin glow (turuncu-kırmızı halo)
        for blur_r, g_color, g_alpha in [
            (22, (255, 80, 0),   40),
            (14, (255, 160, 0),  60),
            (8,  (255, 220, 50), 80),
        ]:
            gl = Image.new("RGBA",(W,H),(0,0,0,0))
            gld = ImageDraw.Draw(gl)
            gld.text((vx,vy),"VS",font=f_vs,fill=(*g_color,int(vs_ease*pulse*g_alpha)))
            bg = Image.alpha_composite(bg, gl.filter(ImageFilter.GaussianBlur(blur_r)))
            draw = ImageDraw.Draw(bg)

        # Derin gölge
        draw.text((vx+4, vy+5), "VS", font=f_vs, fill=(20, 0, 0, int(vs_ease*200)))
        draw.text((vx+2, vy+3), "VS", font=f_vs, fill=(80, 10, 0, int(vs_ease*180)))

        # Ana metalik gradient (3 katman)
        a_base = int(vs_ease * pulse * 255)
        draw.text((vx, vy), "VS", font=f_vs, fill=(180, 60, 0,  int(a_base*0.9)))   # koyu turuncu alt
        draw.text((vx, vy-1), "VS", font=f_vs, fill=(255, 140, 0, int(a_base*0.95))) # turuncu orta
        draw.text((vx, vy-2), "VS", font=f_vs, fill=(255, 220, 80, int(a_base)))     # parlak sarı üst

        # İnce beyaz highlight (üst kenara)
        hl = Image.new("RGBA",(W,H),(0,0,0,0))
        hld = ImageDraw.Draw(hl)
        hld.text((vx, vy-3), "VS", font=f_vs, fill=(255,255,255,int(vs_ease*pulse*90)))
        bg = Image.alpha_composite(bg, hl.filter(ImageFilter.GaussianBlur(2)))
        draw = ImageDraw.Draw(bg)

    # Takım isimleri
    f_isim = _font(15)
    if t > 0.46:
        ia = _ease_out(min((t-0.46)/0.18,1.0))
        for isim, cx in [(ev_isim,cx_sol),(dep_isim,cx_sag)]:
            bbox = draw.textbbox((0,0),isim,font=f_isim)
            tw   = bbox[2]-bbox[0]
            pad  = 7
            # Panel
            panel = Image.new("RGBA",(tw+pad*2+2, 22),(0,0,0,int(ia*160)))
            bg.paste(panel, (cx-tw//2-pad, H-44), panel)
            draw.text((cx-tw//2+1,H-42),isim,font=f_isim,fill=(20,20,20,int(ia*180)))
            draw.text((cx-tw//2,  H-43),isim,font=f_isim,fill=(255,255,255,int(ia*230)))

    return np.array(bg.convert("RGB"))

def mac_banner_olustur(ev_logo_url, dep_logo_url, ev_isim, dep_isim):
    ev_logo  = _logo_indir(ev_logo_url)
    dep_logo = _logo_indir(dep_logo_url)

    kareler = [_render_frame(ev_logo,dep_logo,ev_isim,dep_isim,f) for f in range(FRAMES)]
    for _ in range(18):
        kareler.append(kareler[-1].copy())

    buf = io.BytesIO()
    imageio.mimsave(buf, kareler, format="GIF", fps=FPS, loop=0)
    buf.seek(0)
    return buf
