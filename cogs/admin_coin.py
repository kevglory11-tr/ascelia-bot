"""cogs/admin_coin.py — Admin coin komutları. Yardım menüsünde gözükmez."""

import discord
from discord.ext import commands
from discord import app_commands

import database
from utils.logger import setup_logger
from config.settings import Settings

log       = setup_logger("admin_coin")
settings  = Settings()
M2B       = "<:m2bcoin:1480481551337783437>"
OK        = "<a:check:1478394670856933429>"
FAIL      = "<a:redx:1478394672012034088>"
COIN_ANIM = "<a:coin:1478390167310958734>"


def _admin_kontrol(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    rol = discord.utils.get(interaction.guild.roles, name=settings.admin_rol_adi)
    return bool(rol and rol in interaction.user.roles)


class AdminCoinCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin-coin-ekle", description="[Admin] Kullanıcıya coin ekle.")
    @app_commands.describe(kullanici="Coin eklenecek kullanıcı", miktar="Eklenecek coin miktarı")
    async def admin_coin_ekle(self, interaction: discord.Interaction,
                               kullanici: discord.Member, miktar: int):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message(f"{FAIL} Bu komutu kullanma yetkin yok!", ephemeral=True)
            return
        if miktar <= 0:
            await interaction.response.send_message(f"{FAIL} Miktar 0'dan büyük olmalı!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        yeni = await database.add_coins(kullanici.id, kullanici.display_name, miktar)

        embed = discord.Embed(
            title=f"{OK} Coin Eklendi",
            description=(
                f"👤 Kullanıcı: {kullanici.mention}\n"
                f"➕ Eklenen: **{miktar:,}** {M2B}\n"
                f"{M2B} Yeni bakiye: **{yeni:,} M2B Coin**"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text=f"İşlemi yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Admin coin ekle: {interaction.user} → {kullanici} +{miktar}")

    @app_commands.command(name="admin-coin-sil", description="[Admin] Kullanıcıdan coin sil.")
    @app_commands.describe(kullanici="Coin silinecek kullanıcı", miktar="Silinecek coin miktarı")
    async def admin_coin_sil(self, interaction: discord.Interaction,
                              kullanici: discord.Member, miktar: int):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message(f"{FAIL} Bu komutu kullanma yetkin yok!", ephemeral=True)
            return
        if miktar <= 0:
            await interaction.response.send_message(f"{FAIL} Miktar 0'dan büyük olmalı!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        kayit = await database.ensure_user(kullanici.id, kullanici.display_name)

        if kayit["bakiye"] < miktar:
            embed = discord.Embed(
                title=f"{FAIL} Yetersiz Bakiye",
                description=f"Kullanıcının bakiyesi: **{kayit['bakiye']:,}** {M2B}",
                color=0xE74C3C,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await database.remove_coins(kullanici.id, miktar)
        kayit_yeni = await database.ensure_user(kullanici.id, kullanici.display_name)

        embed = discord.Embed(
            title=f"{OK} Coin Silindi",
            description=(
                f"👤 Kullanıcı: {kullanici.mention}\n"
                f"➖ Silinen: **{miktar:,}** {M2B}\n"
                f"{M2B} Yeni bakiye: **{kayit_yeni['bakiye']:,} M2B Coin**"
            ),
            color=0xE74C3C,
        )
        embed.set_footer(text=f"İşlemi yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Admin coin sil: {interaction.user} → {kullanici} -{miktar}")

    @app_commands.command(name="admin-tum-coinleri-sil", description="[Admin] Tüm kullanıcıların coinlerini sıfırla.")
    async def admin_tum_coinleri_sil(self, interaction: discord.Interaction):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message(f"{FAIL} Bu komutu kullanma yetkin yok!", ephemeral=True)
            return

        view = TumCoinSilOnayView()
        await interaction.response.send_message(
            "⚠️ **Tüm kullanıcıların coinleri sıfırlanacak!** Emin misin?",
            view=view, ephemeral=True
        )

    @app_commands.command(name="işlemler", description="[Admin] Kullanıcının coin geçmişini görüntüle.")
    @app_commands.describe(kullanici="Geçmişi görülecek kullanıcı", adet="Kaç işlem gösterilsin (max 20)")
    async def islemler(self, interaction: discord.Interaction,
                       kullanici: discord.Member, adet: int = 10):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message(f"{FAIL} Bu komutu kullanma yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        adet = min(adet, 20)

        async with database.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT miktar, tip, aciklama, zaman
                   FROM coin_log WHERE discord_id=$1
                   ORDER BY zaman DESC LIMIT $2""",
                kullanici.id, adet
            )
            bakiye_row = await conn.fetchrow(
                "SELECT bakiye, toplam_kazanilan, giris_serisi FROM coins WHERE discord_id=$1",
                kullanici.id
            )

        if not rows:
            await interaction.followup.send("Bu kullanıcıya ait işlem kaydı yok.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Coin Geçmişi — {kullanici.display_name}",
            color=0x3498DB,
        )
        if bakiye_row:
            embed.add_field(name=f"{M2B} Bakiye",          value=f"{bakiye_row['bakiye']:,} coin",            inline=True)
            embed.add_field(name="📈 Toplam Kazanılan",    value=f"{bakiye_row['toplam_kazanilan']:,} coin",   inline=True)
            embed.add_field(name="🔥 Giriş Serisi",        value=f"{bakiye_row['giris_serisi']} gün",         inline=True)

        gecmis = ""
        from datetime import timezone, timedelta
        TR = timedelta(hours=3)
        for r in rows:
            zaman_tr = (r["zaman"].astimezone(timezone.utc) + TR).strftime("%d.%m %H:%M")
            isaret   = "+" if r["tip"] == "kazanc" else "-"
            aciklama = r["aciklama"] or r["tip"]
            gecmis  += f"`{zaman_tr}` {isaret}{r['miktar']:,} coin — {aciklama}\n"

        embed.add_field(name=f"Son {adet} İşlem", value=gecmis or "—", inline=False)
        embed.set_thumbnail(url=kullanici.display_avatar.url)
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"İşlemler: {interaction.user} → {kullanici}")

    @app_commands.command(name="coin-sıralaması", description="[Admin] Tüm sunucunun coin sıralamasını göster.")
    @app_commands.describe(sayfa="Sayfa numarası (her sayfada 10 kişi)")
    async def coin_siralaması(self, interaction: discord.Interaction, sayfa: int = 1):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        limit  = 10
        offset = (sayfa - 1) * limit

        async with database.pool.acquire() as conn:
            toplam = await conn.fetchval("SELECT COUNT(*) FROM coins WHERE bakiye > 0")
            rows   = await conn.fetch(
                "SELECT username, bakiye, giris_serisi FROM coins WHERE bakiye > 0 ORDER BY bakiye DESC LIMIT $1 OFFSET $2",
                limit, offset
            )

        if not rows:
            await interaction.followup.send("Henüz coin sahibi kimse yok!", ephemeral=True)
            return

        toplam_sayfa = max(1, (toplam + limit - 1) // limit)
        embed = discord.Embed(
            title=f"{COIN_ANIM} Coin Sıralaması — Sayfa {sayfa}/{toplam_sayfa}",
            description="",
            color=0xFFD700,
        )

        madalyalar = [
            "<a:gold:1478525208766709833>",
            "<a:silver:1478525216069259487>",
            "<a:bronze:1478525229583302656>",
        ]
        siralama = ""
        for i, row in enumerate(rows):
            gercek_sira = offset + i + 1
            madalya     = madalyalar[i] if sayfa == 1 and i < 3 else f"`{gercek_sira}.`"
            seri_text   = f" 🔥 {row['giris_serisi']} gün" if row["giris_serisi"] >= 3 else ""
            siralama   += f"{madalya} **{row['username']}** — {row['bakiye']:,} {M2B}{seri_text}\n"

        embed.description = siralama
        embed.set_footer(text=f"Toplam {toplam} kullanıcı • /coin-sıralaması [sayfa]")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Coin sıralaması görüntülendi: {interaction.user} (sayfa {sayfa})")


class TumCoinSilOnayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="Evet, Sıfırla", style=discord.ButtonStyle.danger)
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with database.pool.acquire() as conn:
            await conn.execute("UPDATE coins SET bakiye = 0, toplam_kazanilan = 0, son_giris = NULL")
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="✅ Tüm coinler sıfırlandı.", view=self
        )

    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary)
    async def iptal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ İptal edildi.", view=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCoinCog(bot))
