"""cogs/atam.py — /atam komutu. Yalnızca yetkili kullanıcılara özel."""

import os
import discord
from discord.ext import commands
from discord import app_commands

from utils.logger import setup_logger

log = setup_logger("atam")

IZINLI_KULLANICILAR = {
    1102062306147438622,
    426329850123386880,
    846115619728261131,
}

VIDEO_YOLU = os.path.join(os.path.dirname(__file__), "..", "assets", "atam.mp4")


class AtamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="atam", description="🇹🇷")
    async def atam(self, interaction: discord.Interaction):
        if interaction.user.id not in IZINLI_KULLANICILAR:
            await interaction.response.send_message("❌ Bu komutu kullanma yetkin yok.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            with open(VIDEO_YOLU, "rb") as f:
                dosya = discord.File(f, filename="atam.mp4")
                await interaction.followup.send(file=dosya)
            log.info(f"/atam: {interaction.user}")
        except Exception as e:
            log.error(f"/atam hatası: {e}", exc_info=True)
            await interaction.followup.send("❌ Video gönderilemedi.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AtamCog(bot))
