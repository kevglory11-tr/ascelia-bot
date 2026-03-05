"""cogs/yardim.py — /yardım komutu — modern tasarım."""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from config.settings import Settings

log = logging.getLogger("cog.yardim")


class YardimCog(commands.Cog, name="Yardım"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    @app_commands.command(name="yardım", description="Botun tüm komutlarını gösterir")
    async def yardim(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        embed = discord.Embed(
            color=self.settings.renkler["altin"],
        )

        if guild and guild.icon:
            embed.set_author(name=f"{guild.name} — Komut Rehberi", icon_url=guild.icon.url)
        else:
            embed.set_author(name="<:settings:1478392476778631222>  Ascelia Bot — Tüm Komutlar")

        embed.description = (
            "```\n"
            "⚔️  Ascelia Bot — Tüm Komutlar\n"
            "```"
        )

        embed.add_field(
            name="<a:genel:1478389856874004592>  Genel",
            value=(
                "> <:dot1:1478383822625181879> `/yardım` — Bu menü\n"
                "> <:dot1:1478383822625181879> `/sss` — Sıkça sorulan sorular"
            ),
            inline=False,
        )

        embed.add_field(
            name="<a:ticket1:1478391380635287725>  Destek Sistemi",
            value=(
                "> <:dot2:1478383869534404712> `/ticket` — Yeni destek talebi oluştur"
            ),
            inline=False,
        )

        embed.add_field(
            name="<a:basvuru:1478389708932255775>  Başvuru Sistemi",
            value=(
                "> <:dot3:1478383947976282275> `/başvuru` — Moderatör veya İçerik Üreticisi başvurusu yap"
            ),
            inline=False,
        )

        embed.add_field(
            name="<a:bildirim:1478390691334979645>  Geri Bildirim",
            value=(
                "> <:dot4:1478383949620449290> `/öneri` — Sunucu için öneri gönder\n"
                "> <:dot4:1478383949620449290> `/şikayet` — Oyuncu hakkında şikayet bildir"
            ),
            inline=False,
        )

        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="\u200b",
            inline=False,
        )

        embed.add_field(
            name="<a:duyurular:1478387119499116695>  Admin — Duyurular",
            value=(
                "> <:dot5:1478383917424705740> `/duyuru` — Sunucudaki üyelere ayarlanabilir toplu mesaj göndermenizi sağlar."
            ),
            inline=False,
        )

        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(
            text="Ascelia Bot • AWGames | Bot Owner: Aselica | 🔹 Üye  🔸 Admin",
            icon_url=guild.icon.url if guild and guild.icon else None,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        log.info(f"/yardım — {interaction.user}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YardimCog(bot))
