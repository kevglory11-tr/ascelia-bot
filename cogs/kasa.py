"""cogs/kasa.py — /bakiye ve /sıralama komutları."""

import discord
from discord.ext import commands
from discord import app_commands

import database
from utils.logger import setup_logger
from utils.siralama_gorseli import GORSEL_SURUM, siralama_gorseli_olustur

log    = setup_logger("kasa")
M2B    = "<:m2bcoin:1480481551337783437>"
FAIL   = "<a:redx:1478394672012034088>"
TROPHY = "<a:bildirim:1478390691334979645>"


class KasaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bakiye", description="M2B Coin bakiyeni görüntüle.")
    @app_commands.describe(kullanici="Başka birinin bakiyesine bak (opsiyonel)")
    async def bakiye(self, interaction: discord.Interaction, kullanici: discord.Member = None):
        await interaction.response.defer()
        hedef = kullanici or interaction.user
        try:
            kayit  = await database.ensure_user(hedef.id, hedef.display_name)
            bakiye = kayit["bakiye"]
            toplam = kayit["toplam_kazanilan"]

            async with database.pool.acquire() as conn:
                sira = await conn.fetchval(
                    "SELECT COUNT(*) + 1 FROM coins WHERE bakiye > $1", bakiye
                )

            embed = discord.Embed(
                title=f"{M2B} {hedef.display_name} — Bakiye",
                color=0xFFD700,
            )
            embed.set_thumbnail(url=hedef.display_avatar.url)
            embed.add_field(name=f"{M2B} Bakiye",       value=f"**{bakiye:,}** M2B Coin", inline=True)
            embed.add_field(name="📈 Toplam Kazanılan",  value=f"**{toplam:,}** Coin",     inline=True)
            embed.add_field(name="🏆 Sıralama",          value=f"**#{sira}**",             inline=True)
            embed.add_field(
                name="📅 Son Giriş",
                value=str(kayit["son_giris"]) if kayit["son_giris"] else "Henüz yapılmadı",
                inline=False,
            )
            embed.set_footer(text="/günlük-giriş · /market · /sıralama")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f"bakiye hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)

    @app_commands.command(name="sıralama", description="En zengin 10 M2B Coin sahibini gör.")
    async def siralama(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            liste = await database.get_leaderboard(10)
            if not liste:
                await interaction.followup.send("Henüz kayıtlı kimse yok!", ephemeral=True)
                return

            buf = await siralama_gorseli_olustur(self.bot, liste)

            dosya = discord.File(buf, filename="siralama.png")
            embed = discord.Embed(
                title=f"{M2B} M2B Coin — Sıralama",
                description="En zengin 10 kullanıcı.",
                color=0xFFD700,
            )
            embed.set_image(url="attachment://siralama.png")
            embed.set_footer(text=f"Hizalama v{GORSEL_SURUM} · /bakiye ile kendi bakiyeni gör")
            await interaction.followup.send(
                content=f"📊 Görsel sıralama (hizalama **v{GORSEL_SURUM}**).",
                embed=embed,
                file=dosya,
            )
        except Exception as e:
            log.error(f"sıralama hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(KasaCog(bot))
