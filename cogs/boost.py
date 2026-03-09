"""
cogs/boost.py — Sunucu boost ödülleri.
Boost yapıldığında anında 250 coin verilir.
Süre kontrolü: bot her başladığında ve günlük olarak kontrol eder.
"""

import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timezone, timedelta

import database
from utils.logger import setup_logger
from config.coin_settings import BOOST_ODULLER

log = setup_logger("boost")


def _boost_gun(baslangic) -> int:
    """Boost başlangıcından kaç gün geçti."""
    if not baslangic:
        return 0
    gecen = datetime.now(timezone.utc) - baslangic.replace(tzinfo=timezone.utc)
    return gecen.days


class BoostCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.boost_kontrol.start()

    def cog_unload(self):
        self.boost_kontrol.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Boost başladığında ilk ödülü ver."""
        if before.premium_since is None and after.premium_since is not None:
            # Yeni boost
            try:
                kayit = await database.ensure_user(after.id, after.display_name)
                yeni_bakiye = await database.add_coins(after.id, after.display_name, 250)
                await database.update_boost(after.id, 1)

                log.info(f"Boost ödülü: {after} → 250 coin (Lv1)")

                # Bildirim DM
                try:
                    embed = discord.Embed(
                        title="⚜️ Takviye Ödülü!",
                        description=(
                            f"Sunucuyu Takviye ettiğin için **250 M2Board Coin** kazandın! 🎉\n"
                            f"💰 Yeni bakiyen: **{yeni_bakiye:,} Coin**\n\n"
                            "Takviyeni uzun süre tutarsan daha büyük ödüller kazanırsın!"
                        ),
                        color=0xff73fa,
                    )
                    await after.send(embed=embed)
                except Exception:
                    pass

            except Exception as e:
                log.error(f"boost on_member_update hatası: {e}", exc_info=True)

        elif before.premium_since is not None and after.premium_since is None:
            # Boost bitti
            try:
                await database.update_boost(after.id, 0)
                log.info(f"Boost bitti: {after}")
            except Exception as e:
                log.error(f"boost bitti hatası: {e}", exc_info=True)

    @tasks.loop(hours=24)
    async def boost_kontrol(self):
        """Her gün boost süre ödüllerini kontrol et."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            for member in guild.premium_subscribers:
                try:
                    kayit = await database.ensure_user(member.id, member.display_name)
                    mevcut_seviye = kayit["boost_seviye"] or 1
                    gun           = _boost_gun(kayit["boost_baslangic"])

                    for odul in sorted(BOOST_ODULLER, key=lambda x: x["seviye"], reverse=True):
                        if odul["seviye"] <= mevcut_seviye:
                            break
                        if gun >= odul["gun"] and odul["gun"] > 0:
                            # Yeni seviye kazandı
                            await database.add_coins(member.id, member.display_name, odul["coin"])
                            await database.update_boost(member.id, odul["seviye"])

                            log.info(f"Boost ödülü: {member} → Lv{odul['seviye']} ({odul['coin']} coin)")

                            try:
                                embed = discord.Embed(
                                    title=f"⚜️ Takviye Ödülü — Seviye {odul['seviye']}!",
                                    description=(
                                        f"**{odul['gun']} gün** takviyeni koruduğun için ödül kazandın!\n"
                                        f"🏆 Unvan: **{odul['unvan']}**\n"
                                        f"💰 **+{odul['coin']:,} M2Board Coin**"
                                    ),
                                    color=0xff73fa,
                                )
                                await member.send(embed=embed)
                            except Exception:
                                pass
                            break

                except Exception as e:
                    log.error(f"boost_kontrol üye hatası ({member}): {e}", exc_info=True)

    @boost_kontrol.before_loop
    async def before_boost_kontrol(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BoostCog(bot))
