"""
cogs/admin_coin.py — Admin coin komutları.
/admin-coin-ekle, /admin-coin-sil, /transfer
Yardım menüsünde gözükmez.
"""

import discord
from discord.ext import commands
from discord import app_commands

import database
from utils.logger import setup_logger
from config.settings import Settings

log      = setup_logger("admin_coin")
settings = Settings()


def _admin_kontrol(interaction: discord.Interaction) -> bool:
    """Kullanıcı admin rolüne sahip mi?"""
    if interaction.user.guild_permissions.administrator:
        return True
    rol = discord.utils.get(interaction.guild.roles, name=settings.admin_rol_adi)
    if rol and rol in interaction.user.roles:
        return True
    return False


class AdminCoinCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /admin-coin-ekle ──────────────────────────────────
    @app_commands.command(name="admin-coin-ekle", description="[Admin] Kullanıcıya coin ekle.")
    @app_commands.describe(kullanici="Coin eklenecek kullanıcı", miktar="Eklenecek coin miktarı")
    async def admin_coin_ekle(self, interaction: discord.Interaction,
                               kullanici: discord.Member, miktar: int):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message("❌ Bu komutu kullanma yetkin yok!", ephemeral=True)
            return
        if miktar <= 0:
            await interaction.response.send_message("❌ Miktar 0'dan büyük olmalı!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        yeni = await database.add_coins(kullanici.id, kullanici.display_name, miktar)

        embed = discord.Embed(
            title="<a:coin:1478390167310958734> Coin Eklendi",
            description=(
                f"👤 Kullanıcı: {kullanici.mention}\n"
                f"➕ Eklenen: **{miktar:,} Coin**\n"
                f"💰 Yeni bakiye: **{yeni:,} Coin**"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text=f"İşlemi yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Admin coin ekle: {interaction.user} → {kullanici} +{miktar}")

    # ── /admin-coin-sil ───────────────────────────────────
    @app_commands.command(name="admin-coin-sil", description="[Admin] Kullanıcıdan coin sil.")
    @app_commands.describe(kullanici="Coin silinecek kullanıcı", miktar="Silinecek coin miktarı")
    async def admin_coin_sil(self, interaction: discord.Interaction,
                              kullanici: discord.Member, miktar: int):
        if not _admin_kontrol(interaction):
            await interaction.response.send_message("❌ Bu komutu kullanma yetkin yok!", ephemeral=True)
            return
        if miktar <= 0:
            await interaction.response.send_message("❌ Miktar 0'dan büyük olmalı!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        kayit = await database.ensure_user(kullanici.id, kullanici.display_name)

        if kayit["bakiye"] < miktar:
            await interaction.followup.send(
                f"❌ Yetersiz bakiye! Kullanıcının bakiyesi: **{kayit['bakiye']:,} Coin**",
                ephemeral=True,
            )
            return

        basarili = await database.remove_coins(kullanici.id, miktar)
        if not basarili:
            await interaction.followup.send("❌ İşlem başarısız.", ephemeral=True)
            return

        kayit_yeni = await database.ensure_user(kullanici.id, kullanici.display_name)
        embed = discord.Embed(
            title="<a:coin:1478390167310958734> Coin Silindi",
            description=(
                f"👤 Kullanıcı: {kullanici.mention}\n"
                f"➖ Silinen: **{miktar:,} Coin**\n"
                f"💰 Yeni bakiye: **{kayit_yeni['bakiye']:,} Coin**"
            ),
            color=0xE74C3C,
        )
        embed.set_footer(text=f"İşlemi yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Admin coin sil: {interaction.user} → {kullanici} -{miktar}")

    # ── /transfer ─────────────────────────────────────────
    @app_commands.command(name="transfer", description="Başka bir kullanıcıya M2B Coin gönder.")
    @app_commands.describe(kullanici="Coin göndereceğin kullanıcı", miktar="Gönderilecek coin miktarı")
    async def transfer(self, interaction: discord.Interaction,
                       kullanici: discord.Member, miktar: int):
        if kullanici.bot:
            await interaction.response.send_message("❌ Bota coin gönderilemez!", ephemeral=True)
            return
        if kullanici.id == interaction.user.id:
            await interaction.response.send_message("❌ Kendine coin gönderemezsin!", ephemeral=True)
            return
        if miktar < 1:
            await interaction.response.send_message("❌ Minimum transfer miktarı 1 Coin!", ephemeral=True)
            return

        await interaction.response.defer()

        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < miktar:
            await interaction.followup.send(
                f"❌ Yetersiz bakiye! Bakiyen: **{kayit['bakiye']:,} Coin**",
                ephemeral=True,
            )
            return

        # Transfer onay
        view = TransferOnayView(interaction.user.id, kullanici.id, miktar)
        embed = discord.Embed(
            title="<a:coin:1478390167310958734> Transfer Onayı",
            description=(
                f"👤 Alıcı: {kullanici.mention}\n"
                f"💸 Miktar: **{miktar:,} M2B Coin**\n\n"
                "Transferi onaylıyor musun?"
            ),
            color=0xFFD700,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class TransferOnayView(discord.ui.View):
    def __init__(self, gonderen_id: int, alici_id: int, miktar: int):
        super().__init__(timeout=30)
        self.gonderen_id = gonderen_id
        self.alici_id    = alici_id
        self.miktar      = miktar

    @discord.ui.button(label="✅ Onayla", style=discord.ButtonStyle.success)
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.gonderen_id:
            await interaction.response.send_message("Bu onay sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        # Tekrar kontrol
        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < self.miktar:
            await interaction.followup.send("❌ Yetersiz bakiye!", ephemeral=True)
            return

        basarili = await database.remove_coins(interaction.user.id, self.miktar)
        if not basarili:
            await interaction.followup.send("❌ İşlem başarısız.", ephemeral=True)
            return

        alici = interaction.guild.get_member(self.alici_id)
        alici_isim = alici.display_name if alici else "Kullanıcı"
        yeni_alici = await database.add_coins(self.alici_id, alici_isim, self.miktar)
        yeni_gonderen = (await database.ensure_user(interaction.user.id, interaction.user.display_name))["bakiye"]

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        embed = discord.Embed(
            title="<a:coin:1478390167310958734> Transfer Tamamlandı!",
            description=(
                f"💸 **{self.miktar:,} M2B Coin** gönderildi!\n\n"
                f"👤 Alıcı: {alici.mention if alici else alici_isim}\n"
                f"💰 Alıcının yeni bakiyesi: **{yeni_alici:,} Coin**\n"
                f"💰 Senin yeni bakiyen: **{yeni_gonderen:,} Coin**"
            ),
            color=0x2ECC71,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Transfer: {interaction.user} → {alici_isim} {self.miktar} coin")

    @discord.ui.button(label="❌ İptal", style=discord.ButtonStyle.danger)
    async def iptal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.gonderen_id:
            await interaction.response.send_message("Bu onay sana ait değil!", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("❌ Transfer iptal edildi.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCoinCog(bot))
