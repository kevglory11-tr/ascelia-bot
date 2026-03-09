"""
cogs/gunluk_giris.py — /günlük-giriş komutu.
TR saatine göre (UTC+3) günde 1 kez, 1-50 coin.
"""

import random
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta

import database
from utils.logger import setup_logger
from config.coin_settings import GUNLUK_MIN_COIN, GUNLUK_MAX_COIN

log = setup_logger("gunluk_giris")
TR_OFFSET = timedelta(hours=3)


def _bugun_tr() -> str:
    return (datetime.now(timezone.utc) + TR_OFFSET).strftime("%Y-%m-%d")


class GunlukGirisCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="günlük-giriş", description="Günlük 1–50 M2B Coin kazan!")
    async def gunluk_giris(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            kayit  = await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bugun  = _bugun_tr()
            son    = str(kayit["son_giris"]) if kayit["son_giris"] else None

            if son == bugun:
                yarin_tr  = (datetime.now(timezone.utc) + TR_OFFSET + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0)
                embed = discord.Embed(
                    title="⏰ Bugünkü Ödülünü Aldın!",
                    description=(
                        f"Zaten aldın. Yarın **00:00 TR** saatinde tekrar kullanabilirsin.\n"
                        f"💰 Bakiyen: **{kayit['bakiye']:,} Coin**"
                    ),
                    color=0xE74C3C,
                )
                await interaction.followup.send(embed=embed)
                return

            coin        = random.randint(GUNLUK_MIN_COIN, GUNLUK_MAX_COIN)
            yeni_bakiye = await database.add_coins(interaction.user.id, interaction.user.display_name, coin)
            await database.set_son_giris(interaction.user.id)

            embed = discord.Embed(
                title="✅ Günlük Giriş Ödülü!",
                description=(
                    f"🎉 {interaction.user.mention} **{coin} M2B Coin** kazandı!\n\n"
                    f"💰 Yeni bakiyen: **{yeni_bakiye:,} Coin**\n"
                    f"📅 Yarın tekrar gel!"
                ),
                color=0x2ECC71,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="/kasa · /market")
            await interaction.followup.send(embed=embed)
            log.info(f"Günlük: {interaction.user} → +{coin} coin")

        except Exception as e:
            log.error(f"günlük-giriş hatası: {e}", exc_info=True)
            await interaction.followup.send("Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunlukGirisCog(bot))
