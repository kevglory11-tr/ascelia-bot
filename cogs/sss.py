"""cogs/sss.py — /sss komutu."""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from config.settings import Settings

log = logging.getLogger("cog.sss")


class SSSCog(commands.Cog, name="SSS"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    @app_commands.command(name="sss", description="Sıkça sorulan sorular sayfasını açar")
    async def sss(self, interaction: discord.Interaction) -> None:
        s = self.settings
        embed = discord.Embed(
            title="<a:bildirim:1478390691334979645>  Sıkça Sorulan Sorular",
            description=(
                "Oyuna dair sıkça sorulan sorulara aşağıdaki linkten ulaşabilirsin!\n\n"
                f"<a:whitearrow:1478394670856933429> **[Tıkla ve Keşfet →]({s.sss_url})**"
            ),
            color=s.renkler["altin"],
        )
        embed.set_image(url=s.gif_url)
        embed.set_footer(text=f"Ascelia Bot • AWGames | {s.site_url}")
        await interaction.response.send_message(embed=embed)
        log.info(f"/sss — {interaction.user}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SSSCog(bot))
