"""
cogs/hazine.py — Goblin Hazinesi.
1-5 saat aralığında belirlenen kanala embed atar.
İlk reaksiyona basan 1-200 coin kazanır. Tek kişi açabilir.
"""

import random
import asyncio
import discord
from discord.ext import commands

import database
from utils.logger import setup_logger
from config.coin_settings import (
    HAZINE_KANAL_ID,
    HAZINE_MIN_SAAT, HAZINE_MAX_SAAT,
    HAZINE_MIN_COIN, HAZINE_MAX_COIN,
)

log = setup_logger("hazine")
HAZINE_EMOJI = "💰"

# Kapalı sandık görseli
SANDIK_KAPALI_URL = "https://i.imgur.com/placeholder_kapali.jpg"
# Açık sandık görseli
SANDIK_ACIK_URL   = "https://i.imgur.com/placeholder_acik.jpg"

# Görselleri Discord'a yüklü değilse attachment olarak kullan
import os
SANDIK_KAPALI_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "sandik_kapali.jpg")
SANDIK_ACIK_PATH   = os.path.join(os.path.dirname(__file__), "..", "assets", "sandik_acik.jpg")


class HazineCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot         = bot
        self.aktif_mesaj = None
        self.bot.loop.create_task(self._dongu())

    async def _dongu(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            bekleme = random.randint(
                HAZINE_MIN_SAAT * 3600,
                HAZINE_MAX_SAAT * 3600,
            )
            saat = bekleme // 3600
            dk   = (bekleme % 3600) // 60
            log.info(f"Sonraki hazine: {saat}s {dk}dk sonra")
            await asyncio.sleep(bekleme)
            await self._gonder()

    async def _gonder(self):
        if not HAZINE_KANAL_ID:
            log.warning("HAZINE_KANAL_ID ayarlanmamış!")
            return
        kanal = self.bot.get_channel(HAZINE_KANAL_ID)
        if not kanal:
            log.error(f"Kanal bulunamadı: {HAZINE_KANAL_ID}")
            return

        embed = discord.Embed(
            title="🎁 M2Board'ın Gizemli Hazinesi Belirdi!",
            description=(
                "**M2Board'ın gizemli hazinesi belirdi!**\n\n"
                f"> **{HAZINE_EMOJI}** emojisine tıkla, hazine sandığını hızlı olan kapar!\n\n"
                "⏳ Sandık **60 saniye** sonra kaybolur!"
            ),
            color=0xFFD700,
        )
        embed.set_footer(text="M2Board Coin Sistemi • Hazineyi ilk açan kazanır!")

        try:
            # Kapalı sandık görselini dosya olarak gönder
            with open(SANDIK_KAPALI_PATH, "rb") as f:
                dosya  = discord.File(f, filename="sandik_kapali.jpg")
                embed.set_image(url="attachment://sandik_kapali.jpg")
                mesaj  = await kanal.send(file=dosya, embed=embed)

            await mesaj.add_reaction(HAZINE_EMOJI)
            self.aktif_mesaj = mesaj

            await asyncio.sleep(60)
            if self.aktif_mesaj and self.aktif_mesaj.id == mesaj.id:
                try:
                    await mesaj.delete()
                except Exception:
                    pass
                self.aktif_mesaj = None

                # Süre doldu embed
                embed_bos = discord.Embed(
                    title="💨 Hazine Kayboldu!",
                    description="Kimse açmadı... Hazine karanlığa geri döndü.",
                    color=0x95A5A6,
                )
                await kanal.send(embed=embed_bos, delete_after=15)
                log.info("Hazine süresi doldu.")

        except Exception as e:
            log.error(f"Hazine gönderilemedi: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return
        if not self.aktif_mesaj:
            return
        if reaction.message.id != self.aktif_mesaj.id:
            return
        if str(reaction.emoji) != HAZINE_EMOJI:
            return

        # Kilitle — sadece ilk kişi geçer
        mesaj            = self.aktif_mesaj
        self.aktif_mesaj = None

        coin        = random.randint(HAZINE_MIN_COIN, HAZINE_MAX_COIN)
        yeni_bakiye = await database.add_coins(user.id, user.display_name, coin)

        try:
            await mesaj.delete()
        except Exception:
            pass

        # Açık sandık görseli ile kazanma embed'i
        embed = discord.Embed(
            title="🎉 Hazine Sandığı Açıldı!",
            description=(
                f"**M2Board gizemli hazinesinden {coin} <a:coin:1478390167310958734> kazandın, "
                f"baya hızlısın vesselam** {user.mention} 🎊\n\n"
                f"💰 Yeni bakiyen: **{yeni_bakiye:,} M2B Coin**"
            ),
            color=0xFFD700,
        )
        embed.set_footer(text="M2Board Coin Sistemi • /bakiye ile bakiyeni gör")

        try:
            with open(SANDIK_ACIK_PATH, "rb") as f:
                dosya = discord.File(f, filename="sandik_acik.jpg")
                embed.set_image(url="attachment://sandik_acik.jpg")
                await mesaj.channel.send(file=dosya, embed=embed)
        except Exception:
            embed.set_thumbnail(url=user.display_avatar.url)
            await mesaj.channel.send(embed=embed)

        log.info(f"Hazine: {user} → {coin} coin")


async def setup(bot: commands.Bot):
    await bot.add_cog(HazineCog(bot))
