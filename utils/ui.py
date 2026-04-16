"""utils/ui.py — Ascelia modern UI kit.

Tutarlı, özgün ve ikon-odaklı embed bileşenleri.
Tüm coglar bu modülü kullanarak modern bir görünüme kavuşur.
"""

from __future__ import annotations

import discord
from typing import Iterable, Optional


# ══════════════════════════════════════════════════════════════
#  PALET — temalı renkler (rol/bağlam bazlı)
# ══════════════════════════════════════════════════════════════
class Palette:
    # Marka
    GOLD        = 0xC9A84C   # birincil
    OBSIDIAN    = 0x1A1B26   # koyu arka plan hissi
    PARCHMENT   = 0xD9C69A   # ikincil
    # Durum
    SUCCESS     = 0x2ECC71
    ERROR       = 0xE74C3C
    WARNING     = 0xF39C12
    INFO        = 0x3498DB
    NEUTRAL     = 0x95A5A6
    # Tier
    TIER_LOW    = 0x95A5A6
    TIER_CHAOS  = 0xE67E22
    TIER_ELIT   = 0xC0392B
    # Nadirlik
    COMMON      = 0x9AA0A6
    UNCOMMON    = 0x2ECC71
    RARE        = 0x3498DB
    EPIC        = 0x9B59B6
    MYTHIC      = 0xE67E22


# ══════════════════════════════════════════════════════════════
#  IKONLAR — semantik emoji sabitleri
# ══════════════════════════════════════════════════════════════
class Icon:
    # Stat
    HP          = "❤️"
    ATK         = "⚔️"
    DEF         = "🛡️"
    SPD         = "💨"
    CRIT        = "💥"
    DODGE       = "🌀"
    # Ekonomi
    GOLD        = "🪙"
    GEM         = "💎"
    COIN        = "🟡"
    SHOP        = "🏪"
    CART        = "🛒"
    # Envanter
    BAG         = "🎒"
    WEAPON      = "🗡️"
    SHIELD      = "🛡️"
    BELT        = "👘"
    POTION      = "🧪"
    LOOT        = "📦"
    # Karakter
    DWARF       = "🧔"
    FAIRY       = "🧚"
    ORC         = "🐗"
    # Tier
    TIER_LOW    = "⬜"
    TIER_CHAOS  = "🟠"
    TIER_ELIT   = "🔴"
    # UI
    ARROW       = "➤"
    DIAMOND     = "◆"
    BULLET      = "•"
    SPARK       = "✨"
    CROWN       = "👑"
    TROPHY      = "🏆"
    FIRE        = "🔥"
    SKULL       = "💀"
    SCROLL      = "📜"
    UP          = "🔺"
    DOWN        = "🔻"
    CHECK       = "✅"
    CROSS       = "❌"
    LOCK        = "🔒"
    TARGET      = "🎯"
    BOOK        = "📖"


# ══════════════════════════════════════════════════════════════
#  AYIRICILAR & BARLAR
# ══════════════════════════════════════════════════════════════
DIVIDER_THIN = "─" * 30
DIVIDER_FAT  = "━" * 30
DIVIDER_DOT  = "· " * 15


def progress_bar(value: int, maximum: int, length: int = 12, style: str = "hp") -> str:
    """Modern Unicode ilerleme çubuğu."""
    if maximum <= 0:
        return "▱" * length
    ratio = max(0.0, min(1.0, value / maximum))
    filled = round(ratio * length)
    empty = length - filled

    if style == "hp":
        if ratio > 0.6:
            fill_ch = "🟩"
        elif ratio > 0.3:
            fill_ch = "🟨"
        else:
            fill_ch = "🟥"
        return fill_ch * filled + "⬛" * empty

    if style == "xp":
        return "🟦" * filled + "⬛" * empty

    # Minimalist sade çubuk
    return "▰" * filled + "▱" * empty


def stat_line(icon: str, label: str, value: str | int, accent: Optional[str] = None) -> str:
    """Tek satır stat gösterimi: `⚔️ Saldırı · 42 (+5)`"""
    core = f"{icon} **{label}** {Icon.BULLET} `{value}`"
    if accent:
        core += f" {accent}"
    return core


def kv_block(pairs: Iterable[tuple[str, str]]) -> str:
    """Markdown tablo benzeri key-value listesi."""
    return "\n".join(f"{Icon.ARROW} **{k}** {Icon.BULLET} {v}" for k, v in pairs)


# ══════════════════════════════════════════════════════════════
#  EMBED BUILDER
# ══════════════════════════════════════════════════════════════
def panel(
    title: str,
    body: str = "",
    *,
    color: int = Palette.GOLD,
    badge: Optional[str] = None,
    footer: str = "Ascelia • AWGames",
    guild: Optional[discord.Guild] = None,
    thumbnail: Optional[str] = None,
) -> discord.Embed:
    """Standart modern panel embedi.

    `badge` başlığın soluna yerleştirilen küçük rozet (emoji/kategori).
    """
    prefix = f"{badge}  " if badge else ""
    embed = discord.Embed(
        title=f"{prefix}{title}",
        description=body,
        color=color,
    )
    footer_icon = guild.icon.url if guild and guild.icon else None
    embed.set_footer(text=footer, icon_url=footer_icon)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


def success(message: str, *, title: str = "Başarılı") -> discord.Embed:
    return discord.Embed(
        title=f"{Icon.CHECK}  {title}",
        description=message,
        color=Palette.SUCCESS,
    )


def error(message: str, *, title: str = "Hata") -> discord.Embed:
    return discord.Embed(
        title=f"{Icon.CROSS}  {title}",
        description=message,
        color=Palette.ERROR,
    )


def warning(message: str, *, title: str = "Uyarı") -> discord.Embed:
    return discord.Embed(
        title=f"⚠️  {title}",
        description=message,
        color=Palette.WARNING,
    )


def info(message: str, *, title: str = "Bilgi") -> discord.Embed:
    return discord.Embed(
        title=f"ℹ️  {title}",
        description=message,
        color=Palette.INFO,
    )


# ══════════════════════════════════════════════════════════════
#  KARTLAR — tema odaklı hazır şablonlar
# ══════════════════════════════════════════════════════════════
def section(name: str, emoji: str = Icon.DIAMOND) -> str:
    """Embed içinde başlık bölümü: `◆ Ekipman`"""
    return f"**{emoji} {name}**"


def header_banner(text: str) -> str:
    """Kutulu başlık bandı (description üstüne konur)."""
    return f"```ansi\n\u001b[1;33m{text}\u001b[0m\n```"


TIER_BADGE = {
    "low":   f"{Icon.TIER_LOW} **Low**",
    "chaos": f"{Icon.TIER_CHAOS} **Chaos**",
    "elit":  f"{Icon.TIER_ELIT} **Elit**",
}

TIER_COLOR = {
    "low":   Palette.TIER_LOW,
    "chaos": Palette.TIER_CHAOS,
    "elit":  Palette.TIER_ELIT,
}

RARITY_COLOR = {
    "yaygın":   Palette.COMMON,
    "uncommon": Palette.UNCOMMON,
    "nadir":    Palette.RARE,
    "efsanevi": Palette.EPIC,
    "mitik":    Palette.MYTHIC,
}
