# cogs/hatirlatici.py — Gunluk gorev hatirlatici sistemi
# Her gun 22:00 TR (19:00 UTC) saatinde hatirlatici atar.
# Opt-in: /hatirlatici-ac  /hatirlatici-kapat

import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

import database
from utils.logger import setup_logger

log = setup_logger("hatirlatici")

_TR_OFF = datetime.timedelta(hours=3)
_SAAT   = datetime.time(hour=19, minute=0, tzinfo=datetime.timezone.utc)  # 22:00 TR


class HatirlaticiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gunluk_hatirlatici.start()

    def cog_unload(self):
        self.gunluk_hatirlatici.cancel()

    @tasks.loop(time=_SAAT)
    async def gunluk_hatirlatici(self):
        await self._hatirlatici_gonder()

    @gunluk_hatirlatici.before_loop
    async def before_hatirlatici(self):
        await self.bot.wait_until_ready()

    async def _hatirlatici_gonder(self):
        bugun = (datetime.datetime.now(datetime.timezone.utc) + _TR_OFF).date().isoformat()
        try:
            kullanicilar = await database.get_hatirlatici_kullanicilari(bugun)
        except Exception as e:
            log.error(f"Hatırlatıcı listesi alınamadı: {e}")
            return

        basarili = 0
        for row in kullanicilar:
            try:
                user = self.bot.get_user(row["discord_id"])
                if not user:
                    user = await self.bot.fetch_user(row["discord_id"])
                await user.send(
                    "⏰ **Günlük Görev Hatırlatıcısı**\n"
                    "Bugün henüz günlük görevini yapmadın!\n"
                    "Sunucuya gel ve `/günlük-görev` komutu ile görevi tamamla. 🎯\n\n"
                    "*Hatırlatıcıyı kapatmak için `/hatırlatıcı-kapat` kullanabilirsin.*"
                )
                basarili += 1
            except Exception:
                pass

        if kullanicilar:
            log.info(f"Görev hatırlatıcısı gönderildi: {basarili}/{len(kullanicilar)} kullanıcı")

    @app_commands.command(name="hatırlatıcı-aç", description="Günlük görev hatırlatıcısını aç.")
    async def hatirlatici_ac(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await database.ensure_user(interaction.user.id, interaction.user.display_name)
        await database.set_hatirlatici(interaction.user.id, True)
        embed = discord.Embed(
            title="✅ Hatırlatıcı Açıldı!",
            description=(
                "Her gün saat **22:00 TR**'de günlük görevini yapmadıysan "
                "DM ile hatırlatılacaksın.\n\n"
                "Kapatmak için `/hatırlatıcı-kapat` kullanabilirsin."
            ),
            color=0x2ECC71,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="hatırlatıcı-kapat", description="Günlük görev hatırlatıcısını kapat.")
    async def hatirlatici_kapat(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await database.set_hatirlatici(interaction.user.id, False)
        embed = discord.Embed(
            title="✅ Hatırlatıcı Kapatıldı",
            description="Artık günlük görev hatırlatması almayacaksın.",
            color=0x95A5A6,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HatirlaticiCog(bot))
