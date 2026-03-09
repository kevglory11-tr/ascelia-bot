"""cogs/status.py — Tam status yönetim sistemi."""

import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config.settings import Settings
from utils.permissions import is_admin, yetki_yok_mesaji

log = logging.getLogger("cog.status")

TIP_MAP = {
    "playing":   discord.ActivityType.playing,
    "watching":  discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
}
TIP_EMOJI = {"playing": "🎮", "watching": "📺", "listening": "🎧", "competing": "⚔️"}
TIP_TR    = {"playing": "Oynuyor", "watching": "İzliyor", "listening": "Dinliyor", "competing": "Rekabet Ediyor"}


class StatusCog(commands.Cog, name="Status"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()
        self.rotasyon_aktif = True
        self._rol_gorevi_aktif = False

    async def cog_load(self) -> None:
        self.dongu.change_interval(minutes=self.settings.status_aralik_dakika)
        self.dongu.start()
        log.info(f"Status rotasyonu başlatıldı ({self.settings.status_aralik_dakika}dk aralık)")

    async def cog_unload(self) -> None:
        self.dongu.cancel()

    async def _set(self, tip: str, metin: str) -> None:
        await self.bot.change_presence(
            activity=discord.Activity(type=TIP_MAP.get(tip, discord.ActivityType.playing), name=metin)
        )

    @tasks.loop(minutes=3)
    async def dongu(self) -> None:
        if not self.rotasyon_aktif:
            return
        tip, metin = random.choice(self.settings.status_listesi)
        await self._set(tip, metin)

    @dongu.before_loop
    async def _bekle(self) -> None:
        await self.bot.wait_until_ready()
        await self._set("watching", "⚔️ Ascelia Bot | /yardım")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        yeni = set(after.roles) - set(before.roles)
        if not yeni:
            return
        for rol in yeni:
            anahtar = rol.name.lower()
            if anahtar not in self.settings.rol_status_map:
                continue
            tip, metin = self.settings.rol_status_map[anahtar]
            # Ayrı task olarak çalıştır — event listener bloklanmasın
            asyncio.create_task(self._rol_status_goster(rol.name, tip, metin))
            break

    async def _rol_status_goster(self, rol_adi: str, tip: str, metin: str) -> None:
        if self._rol_gorevi_aktif:
            return  # Zaten bir rol status görevi çalışıyor
        self._rol_gorevi_aktif = True
        self.rotasyon_aktif = False
        await self._set(tip, metin)
        log.info(f"Rol status → [{rol_adi}] {metin}")
        await asyncio.sleep(self.settings.rol_status_sure)
        self._rol_gorevi_aktif = False
        self.rotasyon_aktif = True

    @app_commands.command(name="status", description="[ADMIN] Botun statusunu değiştirir")
    @app_commands.describe(tip="Aktivite tipi", metin="Status metni")
    @app_commands.choices(tip=[
        app_commands.Choice(name="🎮 Oynuyor",  value="playing"),
        app_commands.Choice(name="📺 İzliyor",  value="watching"),
        app_commands.Choice(name="🎧 Dinliyor", value="listening"),
        app_commands.Choice(name="⚔️ Rekabet",  value="competing"),
    ])
    async def status_cmd(self, interaction: discord.Interaction, tip: str, metin: str) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        self.rotasyon_aktif = False
        await self._set(tip, metin)
        embed = discord.Embed(
            title="✅  Status Güncellendi",
            description=f"{TIP_EMOJI.get(tip,'🎮')} **{TIP_TR.get(tip,tip)}** → `{metin}`\n\n*Rotasyon durduruldu. `/status-oto` ile geri dön.*",
            color=self.settings.renkler["altin"],
        )
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="status-oto", description="[ADMIN] Otomatik dönen statusa geri döner")
    async def status_oto(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        self.rotasyon_aktif = True
        tip, metin = random.choice(self.settings.status_listesi)
        await self._set(tip, metin)
        embed = discord.Embed(
            title="🔄  Otomatik Rotasyon Aktif",
            description=f"Her **{self.settings.status_aralik_dakika} dakikada** bir değişir.\nİlk status: {TIP_EMOJI.get(tip,'🎮')} `{metin}`",
            color=self.settings.renkler["yesil"],
        )
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="status-listesi", description="[ADMIN] Tüm statusları gösterir")
    async def status_listesi(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        durum = "✅ Aktif" if self.rotasyon_aktif else "⏸️ Durduruldu"
        embed = discord.Embed(
            title="🎮  Status Paneli",
            description=f"Rotasyon: **{durum}** | Aralık: **{self.settings.status_aralik_dakika}dk**\n\u200b",
            color=self.settings.renkler["altin"],
        )
        liste = "\n".join(f"`{i:02}.` {TIP_EMOJI.get(t,'🎮')} `{t:<9}` {m}" for i, (t, m) in enumerate(self.settings.status_listesi, 1))
        embed.add_field(name=f"📋  Liste ({len(self.settings.status_listesi)})", value=liste, inline=False)
        rol_satir = "\n".join(f"`{r:<15}` → {TIP_EMOJI.get(t,'🎮')} {m}" for r, (t, m) in self.settings.rol_status_map.items())
        embed.add_field(name="🎭  Rol → Status", value=rol_satir or "*Tanımlanmamış*", inline=False)
        embed.set_footer(text="Düzenlemek için config/settings.py → status_listesi")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatusCog(bot))
