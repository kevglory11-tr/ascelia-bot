"""cogs/gunluk_giris.py — /günlük-giriş komutu."""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta

import database
from utils.logger import setup_logger
from config.coin_settings import GUNLUK_COIN

log       = setup_logger("gunluk_giris")
TR_OFFSET = timedelta(hours=3)
M2B       = "<:m2bcoin:1480481551337783437>"
OK        = "<a:check:1478394670856933429>"
FAIL      = "❌"
COIN_ANIM = "<a:coin:1478390167310958734>"


def _bugun_tr() -> str:
    return (datetime.now(timezone.utc) + TR_OFFSET).strftime("%Y-%m-%d")


def _seri_bonusu(seri: int) -> tuple[int, str]:
    """(bonus_miktar, açıklama) döndürür."""
    if seri == 7:
        return 5, "🎉 **1. hafta tamamlandı!** +5 Coin bonus!"
    elif seri >= 14:
        return 10, "🏆 **2+ hafta serisi!** +10 Coin bonus!"
    return 0, ""


class GunlukGirisCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _gunluk_giris(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            kayit  = await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bugun  = _bugun_tr()
            son    = str(kayit["son_giris"]) if kayit["son_giris"] else None

            if son == bugun:
                embed = discord.Embed(
                    title=f"{FAIL} Bugünkü Ödülünü Zaten Aldın!",
                    description=(
                        f"Yarın **00:00 TR** saatinde tekrar kullanabilirsin.\n\n"
                        f"{M2B} Bakiyen: **{kayit['bakiye']:,} M2B Coin**"
                    ),
                    color=0xE74C3C,
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                await interaction.followup.send(embed=embed)
                return

            coin      = GUNLUK_COIN
            yeni_seri = await database.set_son_giris(interaction.user.id, bugun)

            # Haftalık seri bonusu
            seri_bonus, seri_mesaj = _seri_bonusu(yeni_seri)

            # Luminary kalıcı bonusu
            user_row       = await database.get_user(interaction.user.id)
            luminary_bonus = user_row["luminary_bonus"] if user_row and "luminary_bonus" in user_row.keys() else 0

            # Giriş Takviyesi perki
            giris_takviyesi = await database.get_aktif_perk(interaction.user.id, "giris_takviyesi")
            perk_bonus      = 5 if giris_takviyesi else 0

            toplam      = coin + seri_bonus + luminary_bonus + perk_bonus
            yeni_bakiye = await database.add_coins(
                interaction.user.id, interaction.user.display_name, toplam,
                aciklama=f"Günlük giriş (seri: {yeni_seri})"
            )

            # Açıklama satırları
            satirlar = [f"{COIN_ANIM} {interaction.user.mention} **{coin} M2B Coin** kazandı!"]
            if seri_mesaj:
                satirlar.append(seri_mesaj)
            if luminary_bonus > 0:
                satirlar.append(f"👑 **Luminary bonusu:** +{luminary_bonus} Coin")
            if perk_bonus > 0:
                satirlar.append(f"☀️ **Giriş Takviyesi perki:** +{perk_bonus} Coin")
            satirlar.append(f"\n{M2B} Yeni bakiyen: **{yeni_bakiye:,} M2B Coin**")
            satirlar.append(f"🔥 Giriş seriniz: **{yeni_seri} gün**")
            satirlar.append("📅 Yarın tekrar gel!")

            embed = discord.Embed(
                title=f"{OK} Günlük Giriş Ödülü!",
                description="\n".join(satirlar),
                color=0x2ECC71,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="/bakiye · /market · /günlük-görev · /gem-mağaza")
            await interaction.followup.send(embed=embed)
            log.info(f"Günlük: {interaction.user} → +{toplam} coin (seri: {yeni_seri})")

        except Exception as e:
            log.error(f"günlük-giriş hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)

    @app_commands.command(name="günlük-giriş", description="Günlük 50 M2B Coin kazan!")
    async def gunluk_giris(self, interaction: discord.Interaction):
        await self._gunluk_giris(interaction)

    @app_commands.command(name="günlük", description="Günlük 50 M2B Coin kazan!")
    async def gunluk(self, interaction: discord.Interaction):
        await self._gunluk_giris(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunlukGirisCog(bot))
