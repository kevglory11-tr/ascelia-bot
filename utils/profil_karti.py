"""
utils/profil_karti.py — Card1 layout, statik ve animasyonlu çıktı.
Banner GIF → animasyonlu kart. Animasyonlu avatar → animasyonlu kart.
Banner GIF varsa avatara göre önceliklidir.
"""

import io
import logging
from io import BytesIO
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

_CARD1  = Path(__file__).parent.parent / "assets" / "card1"
_ASSETS = Path(__file__).parent.parent
_FONT   = str(_CARD1 / "levelfont.otf")

log = logging.getLogger("profil_karti")

_GIF_MAX_FRAMES = 24
_GIF_FRAME_MS   = 83   # ~12 fps


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _fmt(n: int) -> str:
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:     return f"{n/1_000_000:.1f}M"
    if n >= 1_000:         return f"{n/1_000:.1f}K"
    return str(n)


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else _ASSETS / path


def _solid(renk_hex: str) -> Image.Image:
    try:
        r, g, b = (int(renk_hex[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        r, g, b = 30, 30, 50
    return Image.new("RGB", (638, 159), (r, g, b))


# ── Görsel getirme ────────────────────────────────────────────────────────────

async def _fetch_bytes(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://discord.com"}
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                return await r.read()
    raise ValueError(f"Gorsel indirilemedi: {url}")


async def _fetch(url: str) -> Image.Image:
    return Image.open(BytesIO(await _fetch_bytes(url)))


# ── Frame çıkarma ─────────────────────────────────────────────────────────────

def _extract_frames(data: bytes, max_frames: int = _GIF_MAX_FRAMES) -> list[Image.Image]:
    """GIF bytes'tan eşit aralıklı frame'ler çıkarır (avatar için)."""
    with Image.open(BytesIO(data)) as img:
        n     = getattr(img, "n_frames", 1)
        count = min(max_frames, n)
        idxs  = [int(i * n / count) for i in range(count)]
        frames = []
        for i in idxs:
            img.seek(i)
            frames.append(img.convert("RGB").copy())
    return frames


def _load_local_gif_frames(path: str) -> list[Image.Image]:
    """Yerel GIF dosyasından tüm frame'leri yükler (banner için)."""
    resolved = _resolve(path)
    log.info(f"Banner GIF: {resolved} (var: {resolved.exists()})")
    with Image.open(resolved) as gif:
        n = getattr(gif, "n_frames", 1)
        log.info(f"Banner frame sayisi: {n}")
        frames = []
        for i in range(n):
            gif.seek(i)
            frames.append(gif.convert("RGB").copy())
    return frames


# ── Kart katmanları ───────────────────────────────────────────────────────────

def _build_card_base(level: int, exp: int, gereken_exp: int):
    """
    Avatar'dan bağımsız, her frame için ortak katmanları döndürür.
    Bir kez yüklenir, tüm frame'lerde yeniden kullanılır.
    """
    overlay  = Image.open(_CARD1 / "overlay1.png")
    mask_img = Image.open(_CARD1 / "mask_circle.jpg").convert("L").resize((170, 170))
    curved   = Image.open(_CARD1 / "curvedoverlay.png").convert("L")

    bar_exp = max((exp / gereken_exp) * 420 if gereken_exp else 0, 50)
    bar_im  = Image.new("RGB", (490, 51), (0, 0, 0))
    bd      = ImageDraw.Draw(bar_im, "RGBA")
    bd.rounded_rectangle((0, 0, 420, 50), 30, fill=(255, 255, 255, 50))
    if exp:
        bd.rounded_rectangle((0, 0, int(bar_exp), 50), 30, fill=(255, 255, 255, 255))

    return overlay, bar_im, mask_img, curved


def _mask_avatar(avatar: Image.Image) -> Image.Image:
    """Avatar'ı siyah zemin üzerine alpha ile yapıştırır."""
    av = Image.new("RGB", avatar.size, (0, 0, 0))
    try:
        av.paste(avatar, mask=avatar.convert("RGBA").split()[3])
    except Exception:
        av.paste(avatar, (0, 0))
    return av


async def _load_static_bg(arka_plan_url: str | None, renk_hex: str) -> Image.Image:
    """Statik arka planı 638×159 RGB olarak döndürür. GIF URL'si solid'e düşer."""
    if not arka_plan_url or arka_plan_url.endswith(".gif"):
        return _solid(renk_hex)
    try:
        img = (
            await _fetch(arka_plan_url)
            if arka_plan_url.startswith("http")
            else Image.open(_resolve(arka_plan_url))
        )
        if img.width < 100 or img.height < 50:
            raise ValueError("Gecersiz gorsel")
        return img.convert("RGB").resize((638, 159))
    except Exception:
        return _solid(renk_hex)


# ── Frame birleştirme ─────────────────────────────────────────────────────────

def _composite_frame(
    bg:          Image.Image,
    av_masked:   Image.Image,
    overlay:     Image.Image,
    bar_im:      Image.Image,
    mask_img:    Image.Image,
    curved:      Image.Image,
    kullanici_adi: str,
    level:       int,
    exp:         int,
    gereken_exp: int,
    f40:         ImageFont.FreeTypeFont,
    f30:         ImageFont.FreeTypeFont,
) -> Image.Image:
    """Bir arka plan ve avatar ile tam kart frame'i oluşturur, RGB döndürür."""
    TEXT = (255, 255, 255)

    canvas = Image.new("RGBA", overlay.size)
    canvas.paste(bg.convert("RGB").resize((638, 159)), (0, 0))
    canvas = canvas.resize(overlay.size)
    canvas.paste(overlay, (0, 0), overlay)

    draw = ImageDraw.Draw(canvas)
    draw.text((205, (327 / 2) + 20), kullanici_adi[:20],
              font=f40, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    canvas.paste(bar_im, (190, 235))

    level_y = (327 / 2) + 125
    draw.text((197, level_y), f"LEVEL - {_fmt(level)}",
              font=f30, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))
    xp_str = f"{_fmt(exp)}/{_fmt(gereken_exp)}"
    xp_w   = draw.textlength(xp_str, font=f30)
    draw.text((638 - xp_w - 50, level_y), xp_str,
              font=f30, fill=TEXT, stroke_width=1, stroke_fill=(0, 0, 0))

    canvas.paste(av_masked, (13, 65), mask_img)

    # curved mask → RGBA → RGB (GIF yalnızca RGB/P destekler)
    final = Image.new("RGBA", canvas.size)
    final.paste(canvas, (0, 0), curved)
    final = final.resize((505, 259), Image.LANCZOS)
    out = Image.new("RGB", final.size, (30, 30, 50))
    out.paste(final, mask=final.split()[3])
    return out


def _save_gif(frames: list[Image.Image]) -> io.BytesIO:
    buf = io.BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:],
                   loop=0, duration=_GIF_FRAME_MS, optimize=False)
    buf.seek(0)
    log.info(f"GIF kaydedildi: {len(frames)} frame, {buf.getbuffer().nbytes:,} byte")
    return buf


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
) -> tuple[io.BytesIO, bool]:
    """
    Profil kartı üretir.
    Returns (BytesIO, is_animated).
    Öncelik: banner GIF > avatar GIF > statik PNG.
    """
    is_banner_gif = bool(
        arka_plan_url
        and not arka_plan_url.startswith("http")
        and arka_plan_url.endswith(".gif")
    )
    is_avatar_gif = avatar_url.endswith(".gif")

    overlay, bar_im, mask_img, curved = _build_card_base(level, exp, gereken_exp)
    f40 = ImageFont.truetype(_FONT, 40)
    f30 = ImageFont.truetype(_FONT, 30)

    # Avatar yükle — GIF ise frame listesi çıkar, değilse tek frame
    if is_avatar_gif:
        av_bytes  = await _fetch_bytes(avatar_url)
        av_frames = _extract_frames(av_bytes)
        av_static = _mask_avatar(av_frames[0].resize((170, 170)))
    else:
        av_raw    = await _fetch(avatar_url)
        av_static = _mask_avatar(av_raw.resize((170, 170)))
        av_frames = None

    def make_frame(bg: Image.Image, av: Image.Image) -> Image.Image:
        return _composite_frame(bg, av, overlay, bar_im, mask_img, curved,
                                kullanici_adi, level, exp, gereken_exp, f40, f30)

    # 1. Banner GIF → banner frame'leri, avatar sabit
    if is_banner_gif:
        try:
            banner_frames = _load_local_gif_frames(arka_plan_url)
            if banner_frames:
                return _save_gif([make_frame(f, av_static) for f in banner_frames]), True
        except Exception as e:
            log.error(f"Banner GIF yuklenemedi: {e}", exc_info=True)

    # Statik arka plan (banner GIF yoksa veya yüklenemediyse)
    bg = await _load_static_bg(arka_plan_url, renk_hex)

    # 2. Avatar GIF → avatar frame'leri, arka plan sabit
    if is_avatar_gif and av_frames and len(av_frames) > 1:
        frames = [make_frame(bg, _mask_avatar(f.resize((170, 170)))) for f in av_frames]
        return _save_gif(frames), True

    # 3. Tamamen statik
    buf = io.BytesIO()
    make_frame(bg, av_static).save(buf, "PNG")
    buf.seek(0)
    return buf, False
