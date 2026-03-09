"""
cogs/autoresponder.py — Otomatik cevap sistemi.

Özellikler:
  • Mesaj anahtar kelime eşleşmesi (büyük/küçük harf önemsiz)
  • Yoksayılacak kanal listesi
  • Bot kendi mesajlarına cevap vermez
  • Kelime listesi settings.py'den yönetilir
"""

import logging

import discord
from discord.ext import commands

from config.settings import Settings

log = logging.getLogger("cog.autoresponder")


class AutoresponderCog(commands.Cog, name="Autoresponder"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    @commands.Cog.listener()
    async def on_message(self, mesaj: discord.Message) -> None:
        # Botun kendi mesajlarını atla
        if mesaj.author.bot:
            return

        # DM'leri atla
        if not mesaj.guild:
            return

        # Yoksayılan kanalları atla
        if mesaj.channel.id in self.settings.autoresponder_ignore_kanal_idleri:
            return

        icerik = mesaj.content.lower()

        for anahtar, cevap in self.settings.autoresponder.items():
            if anahtar.lower() in icerik:
                embed = discord.Embed(
                    description=cevap,
                    color=self.settings.renkler["altin"],
                )
                embed.set_footer(
                    text="Metin2Board • AWGames | Otomatik yanıt",
                    icon_url=mesaj.guild.icon.url if mesaj.guild.icon else None,
                )
                try:
                    await mesaj.reply(embed=embed, mention_author=False)
                    log.debug(f"Autoresponder → '{anahtar}' | {mesaj.author} | #{mesaj.channel}")
                except discord.Forbidden:
                    pass
                break  # Sadece ilk eşleşen kelimeye cevap ver


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoresponderCog(bot))
