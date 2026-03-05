"""utils/embeds.py — Tutarlı embed şablonları."""

import discord
from config.settings import Settings

_s = Settings()


def temel_embed(baslik: str, aciklama: str = "", renk: str = "altin", guild: discord.Guild | None = None) -> discord.Embed:
    embed = discord.Embed(title=baslik, description=aciklama, color=_s.renkler.get(renk, 0xC9A84C))
    embed.set_footer(
        text="Ascelia Bot • AWGames",
        icon_url=guild.icon.url if guild and guild.icon else None,
    )
    return embed


def dm_embed(baslik: str, aciklama: str, renk: str = "altin", guild: discord.Guild | None = None) -> discord.Embed:
    embed = temel_embed(baslik, aciklama, renk, guild)
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed


def basari_embed(mesaj: str) -> discord.Embed:
    return discord.Embed(description=f"✅  {mesaj}", color=0x2ECC71)


def hata_embed(mesaj: str) -> discord.Embed:
    return discord.Embed(description=f"❌  {mesaj}", color=0xE74C3C)
