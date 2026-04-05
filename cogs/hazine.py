"""cogs/hazine.py — Goblin Hazinesi. 1-5 saat aralığında tek kişi açar."""

import random, asyncio, os
import discord
from discord.ext import commands

import database
from utils.logger import setup_logger
from config.coin_settings import (
    HAZINE_KANAL_ID, HAZINE_MIN_SAAT, HAZINE_MAX_SAAT,
    HAZINE_MIN_COIN, HAZINE_MAX_COIN,
)

log            = setup_logger("hazine")
HAZINE_EMOJI   = "💰"
M2B            = "<:m2bcoin:1480481551337783437>"
OK             = "<a:check:1478394670856933429>"
COIN_ANIM      = "<a:coin:1478390167310958734>"

SANDIK_KAPALI = os.path.join(os.path.dirname(__file__), "..", "assets", "sandik_kapali.jpg")
SANDIK_ACIK   = os.path.join(os.path.dirname(__file__), "..", "assets", "sandik_acik.jpg")


class HazineCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot              = bot
        self.aktif_mesaj      = None
        self.kalan_sure       = 0
        self.indirilen_toplam = 0
        self.unique_yazanlar  = set()
        self.bot.loop.create_task(self._dongu())

    async def _dongu(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                self.kalan_sure       = random.randint(int(HAZINE_MIN_SAAT * 3600), int(HAZINE_MAX_SAAT * 3600))
                self.indirilen_toplam = 0
                self.unique_yazanlar  = set()
                log.info(f"Sonraki hazine: {self.kalan_sure//3600}s {(self.kalan_sure%3600)//60}dk sonra")
                while self.kalan_sure > 0:
                    await asyncio.sleep(1)
                    self.kalan_sure -= 1
                await self._gonder()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Hazine döngüsü hatası, 60sn sonra tekrar deneniyor: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _gonder(self):
        if not HAZINE_KANAL_ID:
            log.warning("HAZINE_KANAL_ID ayarlanmamış!")
            return
        kanal = self.bot.get_channel(HAZINE_KANAL_ID)
        if not kanal:
            try:
                kanal = await self.bot.fetch_channel(HAZINE_KANAL_ID)
            except Exception as e:
                log.error(f"Kanal fetch edilemedi: {HAZINE_KANAL_ID} — {e}")
                return
        if not kanal:
            log.error(f"Kanal bulunamadı: {HAZINE_KANAL_ID}")
            return
        log.info(f"Hazine kanalı bulundu: #{kanal.name}")

        embed = discord.Embed(
            title="🎁 M2Board'ın Gizemli Hazinesi Belirdi!",
            description=(
                "**M2Board'ın gizemli hazinesi belirdi!**\n\n"
                f"> {HAZINE_EMOJI} emojisine tıkla, hazine sandığını hızlı olan kapar!\n\n"
                "⏳ Sandık **60 saniye** sonra kaybolur!"
            ),
            color=0xFFD700,
        )
        embed.set_footer(text="M2Board Coin Sistemi • Hazineyi ilk açan kazanır!")

        for deneme in range(3):
            try:
                with open(SANDIK_KAPALI, "rb") as f:
                    dosya = discord.File(f, filename="sandik_kapali.jpg")
                    embed.set_image(url="attachment://sandik_kapali.jpg")
                    mesaj = await kanal.send(file=dosya, embed=embed)
                break
            except discord.errors.DiscordServerError as e:
                log.warning(f"Discord 503, {deneme+1}. deneme: {e}")
                if deneme < 2:
                    await asyncio.sleep(10)
                else:
                    log.error("3 denemede de gönderilemedi, atlanıyor.")
                    return
        try:
            await mesaj.add_reaction(HAZINE_EMOJI)
            self.aktif_mesaj = mesaj

            await asyncio.sleep(60)
            if self.aktif_mesaj and self.aktif_mesaj.id == mesaj.id:
                try:
                    await mesaj.delete()
                except Exception:
                    pass
                self.aktif_mesaj = None
                embed_bos = discord.Embed(
                    title="💨 Hazine Kayboldu!",
                    description="Kimse açmadı... Hazine karanlığa geri döndü.",
                    color=0x95A5A6,
                )
                await kanal.send(embed=embed_bos, delete_after=15)
        except Exception as e:
            log.error(f"Hazine gönderilemedi: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or not self.aktif_mesaj:
            return
        if payload.message_id != self.aktif_mesaj.id:
            return
        if str(payload.emoji) != HAZINE_EMOJI:
            return

        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)

        mesaj            = self.aktif_mesaj
        self.aktif_mesaj = None

        coin        = random.randint(HAZINE_MIN_COIN, HAZINE_MAX_COIN)
        yeni_bakiye = await database.add_coins(user.id, user.display_name, coin)

        # Gem drop (%5 → 3 gem, %25 → 1 gem, %70 → yok)
        gem_drop = 0
        rng = random.random()
        if rng < 0.05:
            gem_drop = 3
        elif rng < 0.30:
            gem_drop = 1

        if gem_drop > 0:
            await database.add_gem(
                user.id, gem_drop,
                tip="hazine_drop",
                aciklama="Hazine avı gem dropu"
            )

        try:
            await mesaj.delete()
        except Exception:
            pass

        gem_satir = f"\n💎 **+{gem_drop} Gem** de düştü! (Şanslısın!)" if gem_drop > 0 else ""

        embed = discord.Embed(
            title=f"{OK} Hazine Sandığı Açıldı!",
            description=(
                f"**M2Board gizemli hazinesinden {coin} {M2B} kazandın,\n"
                f"baya hızlısın vesselam** {user.mention} 🎊{gem_satir}\n\n"
            ),
            color=0xFFD700,
        )
        embed.set_footer(text="M2Board Coin Sistemi • /bakiye ile bakiyeni gör")

        try:
            with open(SANDIK_ACIK, "rb") as f:
                dosya = discord.File(f, filename="sandik_acik.jpg")
                embed.set_image(url="attachment://sandik_acik.jpg")
                await mesaj.channel.send(file=dosya, embed=embed)
        except Exception:
            embed.set_thumbnail(url=user.display_avatar.url)
            await mesaj.channel.send(embed=embed)

        log.info(f"Hazine: {user} → {coin} coin" + (f" + {gem_drop} gem" if gem_drop else ""))


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.kalan_sure <= 0:
            return
        if self.indirilen_toplam >= 1800:
            return

        self.unique_yazanlar.add(message.author.id)

        if len(self.unique_yazanlar) >= 5:
            indirim = random.randint(300, 600)
            kalan_indirilebilir = 1800 - self.indirilen_toplam
            indirim = min(indirim, kalan_indirilebilir, self.kalan_sure - 10)
            if indirim > 0:
                self.kalan_sure       -= indirim
                self.indirilen_toplam += indirim
                self.unique_yazanlar  = set()
                log.info(
                    f"Hazine {indirim//60}dk erken gelecek! "
                    f"(Toplam indirim: {self.indirilen_toplam//60}dk, "
                    f"Kalan: {self.kalan_sure//3600}s {(self.kalan_sure%3600)//60}dk)"
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(HazineCog(bot))
    