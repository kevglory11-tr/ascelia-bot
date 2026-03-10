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


    @app_commands.command(name="admin-tum-coinleri-sil", description="[Admin] Tüm kullanıcıların coinlerini sıfırla.")
    async def admin_tum_coinleri_sil(self, interaction: discord.Interaction):
        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        # Onay butonu
        view = TumCoinSilOnayView()
        await interaction.response.send_message(
            "⚠️ **Tüm kullanıcıların coinleri sıfırlanacak!** Emin misin?",
            view=view, ephemeral=True
        )


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
