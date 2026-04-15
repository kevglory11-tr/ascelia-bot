"""cogs/referans.py — Referans/davet sistemi. Davet eden + doğrulanan ödül alır."""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

import database
from utils.logger import setup_logger

log       = setup_logger("referans")
OK        = "<a:check:1478394670856933429>"
COIN_ANIM = "<a:coin:1478390167310958734>"
M2B       = "<:m2bcoin:1480481551337783437>"

# Ödüller
DAVET_EDEN_ODUL  = 100   # Davet eden kişiye coin
DAVET_EDILEN_ODUL = 50   # Yeni üyeye coin


class ReferansCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._invite_cache: dict[str, int] = {}  # invite_code → uses
        self._pending: dict[int, int] = {}        # yeni_uye_id → davet_eden_id

    async def cog_load(self):
        self.bot.loop.create_task(self._cache_invites())

    async def _cache_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self._invite_cache = {inv.code: inv.uses for inv in invites}
                log.info(f"Davet cache yüklendi: {len(self._invite_cache)} davet")
            except discord.Forbidden:
                log.warning("Davetleri çekme yetkisi yok!")
            except Exception as e:
                log.error(f"Davet cache hatası: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        try:
            invites_now = await member.guild.invites()
        except Exception as e:
            log.error(f"Davetler alınamadı: {e}")
            return

        davet_eden = None
        for inv in invites_now:
            eski_uses = self._invite_cache.get(inv.code, 0)
            if inv.uses > eski_uses and inv.inviter:
                davet_eden = inv.inviter.id
                break

        # Cache güncelle
        self._invite_cache = {inv.code: inv.uses for inv in invites_now}

        if davet_eden and davet_eden != member.id:
            self._pending[member.id] = davet_eden
            log.info(f"Referans tespit: {member} ← davet eden: {davet_eden}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Çıkan kişinin pending kaydını temizle
        self._pending.pop(member.id, None)
        # Davet cache güncelle
        try:
            invites = await member.guild.invites()
            self._invite_cache = {inv.code: inv.uses for inv in invites}
        except Exception:
            pass

    async def referans_odul_ver(self, member: discord.Member):
        """Doğrulama sonrası çağrılır — ikisine de ödül verir."""
        davet_eden_id = self._pending.pop(member.id, None)
        if not davet_eden_id:
            return

        guild = member.guild

        # Davet edene ödül
        davet_eden = guild.get_member(davet_eden_id)
        if davet_eden:
            await database.add_coins(
                davet_eden.id, davet_eden.display_name, DAVET_EDEN_ODUL,
                aciklama=f"Referans ödülü: {member.display_name} davet edildi"
            )
            # DB'ye referans kaydı
            async with database.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO referans_log (davet_eden_id, davet_edilen_id, odul_coin)
                       VALUES ($1, $2, $3)""",
                    davet_eden_id, member.id, DAVET_EDEN_ODUL
                )
            try:
                await davet_eden.send(
                    f"{OK} **Referans ödülü!** {member.display_name} senin davetin ile katılıp doğrulandı.\n"
                    f"{COIN_ANIM} **+{DAVET_EDEN_ODUL} M2B Coin** hesabına eklendi!"
                )
            except Exception:
                pass
            log.info(f"Referans ödülü: {davet_eden} → +{DAVET_EDEN_ODUL} coin")

        # Yeni üyeye ödül
        await database.add_coins(
            member.id, member.display_name, DAVET_EDILEN_ODUL,
            aciklama="Referans bonusu: davetli üye"
        )
        try:
            await member.send(
                f"{OK} **Hoş geldin bonusu!** Bir davet ile katıldığın için:\n"
                f"{COIN_ANIM} **+{DAVET_EDILEN_ODUL} M2B Coin** hesabına eklendi!"
            )
        except Exception:
            pass
        log.info(f"Referans bonus: {member} → +{DAVET_EDILEN_ODUL} coin")

    # ── /referanslarım komutu ────────────────────────────────────
    @app_commands.command(name="referanslarım", description="Kaç kişi davet ettiğini ve kazandığın ödülleri gör.")
    async def referanslarim(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with database.pool.acquire() as conn:
            sayi = await conn.fetchval(
                "SELECT COUNT(*) FROM referans_log WHERE davet_eden_id=$1",
                interaction.user.id
            ) or 0
            toplam_coin = await conn.fetchval(
                "SELECT COALESCE(SUM(odul_coin), 0) FROM referans_log WHERE davet_eden_id=$1",
                interaction.user.id
            ) or 0

        embed = discord.Embed(
            title="📨 Referanslarım",
            description=(
                f"👥 **Davet ettiğin kişi:** {sayi}\n"
                f"{M2B} **Kazandığın toplam:** {toplam_coin} M2B Coin"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="Sunucuya birini davet et, doğrulanınca ödül kazan!")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /referans-sıralama komutu ────────────────────────────────
    @app_commands.command(name="referans-sıralama", description="En çok davet eden kişileri gör.")
    async def referans_siralama(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with database.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT davet_eden_id, COUNT(*) as sayi, SUM(odul_coin) as toplam
                   FROM referans_log GROUP BY davet_eden_id
                   ORDER BY sayi DESC LIMIT 10"""
            )

        if not rows:
            await interaction.followup.send("Henüz referans kaydı yok.", ephemeral=True)
            return

        madalya = ["🥇", "🥈", "🥉"]
        satirlar = []
        for i, row in enumerate(rows):
            uye = interaction.guild.get_member(row["davet_eden_id"])
            isim = uye.display_name if uye else f"Kullanıcı#{row['davet_eden_id']}"
            emo = madalya[i] if i < 3 else f"`{i+1}.`"
            satirlar.append(f"{emo} **{isim}** — {row['sayi']} davet · {row['toplam']} {M2B}")

        embed = discord.Embed(
            title="📨 Referans Sıralaması",
            description="\n".join(satirlar),
            color=0x2ECC71,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReferansCog(bot))
