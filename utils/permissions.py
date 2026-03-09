"""utils/permissions.py — Yetki kontrolleri."""

import discord
from config.settings import Settings


def is_admin(interaction: discord.Interaction, settings: Settings) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    hedef = settings.admin_rol_adi.lower()
    return any(r.name.lower() == hedef for r in interaction.user.roles)


async def yetki_yok_mesaji(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="❌  Yetersiz Yetki",
        description="Bu komutu kullanmak için gerekli yetkiye sahip değilsin.",
        color=0xE74C3C,
    )
    embed.set_footer(text="Ascelia Bot • AWGames")
    await interaction.response.send_message(embed=embed, ephemeral=True)
