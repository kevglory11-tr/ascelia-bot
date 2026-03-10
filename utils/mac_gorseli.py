"""utils/mac_gorseli.py — İki takım logosunu VS ile birleştir."""

import io
import requests
from PIL import Image, ImageDraw, ImageFont

def _logo_indir(url: str, boyut=(180, 180)) -> Image.Image:
    try:
        r = requests.get(url, timeout=5)
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img = img.resize(boyut, Image.LANCZOS)
        return img
    except Exception:
        # Hata olursa boş gri kare döndür
        img = Image.new("RGBA", boyut, (60, 60, 60, 255))
        return img

def mac_banner_olustur(ev_logo_url: str, dep_logo_url: str, ev_isim: str, dep_isim: str) -> io.BytesIO:
    W, H      = 600, 220
    LOGO_BOY  = (160, 160)
    banner    = Image.new("RGBA", (W, H), (30, 30, 34, 255))
    draw      = ImageDraw.Draw(banner)

    # Logoları indir
    ev_logo  = _logo_indir(ev_logo_url,  LOGO_BOY) if ev_logo_url  else Image.new("RGBA", LOGO_BOY, (60,60,60,255))
    dep_logo = _logo_indir(dep_logo_url, LOGO_BOY) if dep_logo_url else Image.new("RGBA", LOGO_BOY, (60,60,60,255))

    # Logoları yapıştır
    logo_y = (H - LOGO_BOY[1]) // 2
    banner.paste(ev_logo,  (30, logo_y),  ev_logo)
    banner.paste(dep_logo, (W - 30 - LOGO_BOY[0], logo_y), dep_logo)

    # VS yazısı
    try:
        font_vs   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        font_isim = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        font_vs   = ImageFont.load_default()
        font_isim = ImageFont.load_default()

    # VS
    vs_text = "VS"
    bbox    = draw.textbbox((0,0), vs_text, font=font_vs)
    vs_w    = bbox[2] - bbox[0]
    vs_h    = bbox[3] - bbox[1]
    draw.text(((W - vs_w)//2, (H - vs_h)//2 - 10), vs_text, font=font_vs, fill=(255, 215, 0, 255))

    # Takım isimleri
    for text, x_center in [(ev_isim, 110), (dep_isim, W - 110)]:
        bbox  = draw.textbbox((0,0), text, font=font_isim)
        t_w   = bbox[2] - bbox[0]
        draw.text((x_center - t_w//2, H - 28), text, font=font_isim, fill=(220, 220, 220, 255))

    buf = io.BytesIO()
    banner.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
