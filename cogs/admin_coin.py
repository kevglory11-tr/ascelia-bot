"""cogs/admin_coin.py — Admin coin komutları. Yardım menüsünde gözükmez."""

import discord
from discord.ext import commands
from discord import app_commands

import database
from utils.logger import setup_logger
from config.settings import Settings

log      = setup_logger("admin_coin")
settings = Settings()
M2B      = "<:m2bcoin:1480481551337783437>"
OK       = "<a:check:1478394670856933429>"
FAIL     = "<a:redx:1478394672012034088>"


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

    @app_commands.command(name="transfer", description="Başka bir kullanıcıya M2B Coin gönder.")
    @app_commands.describe(kullanici="Coin göndereceğin kullanıcı", miktar="Gönderilecek coin miktarı")
    async def transfer(self, interaction: discord.Interaction,
                       kullanici: discord.Member, miktar: int):
        if kullanici.bot:
            await interaction.response.send_message(f"{FAIL} Bota coin gönderilemez!", ephemeral=True)
            return
        if kullanici.id == interaction.user.id:
            await interaction.response.send_message(f"{FAIL} Kendine coin gönderemezsin!", ephemeral=True)
            return
        if miktar < 1:
            await interaction.response.send_message(f"{FAIL} Minimum transfer 1 Coin!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < miktar:
            embed = discord.Embed(
                title=f"{FAIL} Yetersiz Bakiye",
                description=f"Bakiyen: **{kayit['bakiye']:,}** {M2B}",
                color=0xE74C3C,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        view  = TransferOnayView(interaction.user.id, kullanici.id, miktar)
        embed = discord.Embed(
            title=f"{M2B} Transfer Onayı",
            description=(
                f"👤 Alıcı: {kullanici.mention}\n"
                f"💸 Miktar: **{miktar:,}** {M2B}\n\n"
                "Transferi onaylıyor musun?"
            ),
            color=0xFFD700,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCoinCog(bot))
