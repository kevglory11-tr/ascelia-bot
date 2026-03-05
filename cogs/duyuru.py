# -*- coding: utf-8 -*-
"""cogs/duyuru.py — Toplu DM duyuru komutları (modal formlar)."""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config.settings import Settings
from utils.permissions import is_admin, yetki_yok_mesaji
from utils.dm_sender import herkese_gonder

log = logging.getLogger("cog.duyuru")


def _sosyal_view() -> discord.ui.View:
    settings = Settings()
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Web Sitesi",
        url=settings.site_url,
        style=discord.ButtonStyle.link,
        emoji=discord.PartialEmoji(name="m2board", id=1478635055336390827),
    ))
    view.add_item(discord.ui.Button(
        label="Discord",
        url=settings.discord_davet_url,
        style=discord.ButtonStyle.link,
        emoji=discord.PartialEmoji(name="dc", id=1478635275646140467),
    ))
    view.add_item(discord.ui.Button(
        label="Instagram",
        url="https://www.instagram.com/tmgamesatius",
        style=discord.ButtonStyle.link,
        emoji=discord.PartialEmoji(name="instagram", id=1478635152614625281),
    ))
    return view


def _duyuru_embed(guild, baslik, icerik, renk, tur_emoji, tur_adi, ekstra_alanlar=None):
    embed = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
    else:
        embed.set_author(name=guild.name)
    embed.add_field(name=f"{tur_emoji}  AWGames Bilgilendirme", value=f"\u200b\n**{baslik}**", inline=False)
    embed.add_field(name="\u200b", value=icerik, inline=False)
    if ekstra_alanlar:
        for ad, deger in ekstra_alanlar:
            embed.add_field(name=ad, value=f"```{deger}```", inline=True)
    embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.set_footer(text="Ascelia Bot • AWGames", icon_url=guild.icon.url if guild.icon else None)
    return embed


class DuyuruModal(discord.ui.Modal, title="Duyuru Gönder"):
    baslik = discord.ui.TextInput(label="Başlık", placeholder="Duyuru başlığını yazın...", max_length=200)
    icerik = discord.ui.TextInput(
        label="İçerik",
        placeholder="Duyuru metnini yazın. Enter ile alt satıra geçebilirsiniz...",
        style=discord.TextStyle.paragraph,
        max_length=1800,
    )
    video = discord.ui.TextInput(label="Video Linki (opsiyonel)", placeholder="https://...", required=False, max_length=300)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = _duyuru_embed(
            guild=interaction.guild, baslik=self.baslik.value, icerik=self.icerik.value,
            renk=self.cog.settings.renkler["altin"],
            tur_emoji="<a:duyurular:1478387119499116695>", tur_adi="Duyuru",
        )
        await self.cog._gonder_rapor(interaction, embed, "Duyuru", video_url=self.video.value.strip() or None)


class EtkinlikModal(discord.ui.Modal, title="Etkinlik Duyurusu"):
    baslik = discord.ui.TextInput(label="Etkinlik Adı", placeholder="Etkinliğin adını yazın...", max_length=200)
    icerik = discord.ui.TextInput(
        label="Açıklama",
        placeholder="Etkinlik detaylarını yazın. Enter ile alt satıra geçebilirsiniz...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )
    tarih = discord.ui.TextInput(label="Tarih & Saat", placeholder="Örn: 6 Mart 21:00", max_length=100)
    odul = discord.ui.TextInput(label="Ödül (opsiyonel)", placeholder="Ödül bilgisini yazın...", required=False, max_length=200)
    video = discord.ui.TextInput(label="Video Linki (opsiyonel)", placeholder="https://...", required=False, max_length=300)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ekstra = [("<a:cyan:1478524807044923553>  Tarih & Saat", self.tarih.value)]
        if self.odul.value:
            ekstra.append(("<a:yellow:1478524892801667203>  Ödül", self.odul.value))
        embed = _duyuru_embed(
            guild=interaction.guild, baslik=self.baslik.value, icerik=self.icerik.value,
            renk=self.cog.settings.renkler["turuncu"],
            tur_emoji="<a:green:1478524929149239398>", tur_adi="Etkinlik", ekstra_alanlar=ekstra,
        )
        await self.cog._gonder_rapor(interaction, embed, "Etkinlik", video_url=self.video.value.strip() or None)


class CekilisModal(discord.ui.Modal, title="Çekiliş Duyurusu"):
    odul = discord.ui.TextInput(label="Ödül", placeholder="Çekiliş ödülünü yazın...", max_length=200)
    icerik = discord.ui.TextInput(
        label="Katılım Koşulları",
        placeholder="Koşulları yazın. Enter ile alt satıra geçebilirsiniz...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )
    bitis = discord.ui.TextInput(label="Bitiş Tarihi", placeholder="Örn: 10 Mart 23:59", max_length=100)
    kazanan = discord.ui.TextInput(label="Kazanan Sayısı", placeholder="Örn: 1", max_length=10)
    video = discord.ui.TextInput(label="Video Linki (opsiyonel)", placeholder="https://...", required=False, max_length=300)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = _duyuru_embed(
            guild=interaction.guild, baslik=self.odul.value, icerik=self.icerik.value,
            renk=self.cog.settings.renkler["pembe"],
            tur_emoji="<a:pink:1478524874061516992>", tur_adi="Çekiliş",
            ekstra_alanlar=[
                ("<a:white:1478524885016907998>  Bitiş", self.bitis.value),
                ("<a:yellow:1478524892801667203>  Kazanan Sayısı", self.kazanan.value),
            ],
        )
        await self.cog._gonder_rapor(interaction, embed, "Çekiliş", video_url=self.video.value.strip() or None)


class GuncellemeModal(discord.ui.Modal, title="Güncelleme Notu"):
    versiyon = discord.ui.TextInput(label="Versiyon", placeholder="Örn: v1.2.0", max_length=50)
    icerik = discord.ui.TextInput(
        label="Güncelleme Notları",
        placeholder="Değişiklikleri yazın. Enter ile alt satıra geçebilirsiniz...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )
    tarih = discord.ui.TextInput(label="Yayın Tarihi", placeholder="Örn: 6 Mart 2026", max_length=100)
    video = discord.ui.TextInput(label="Tanıtım Videosu (opsiyonel)", placeholder="https://...", required=False, max_length=300)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = _duyuru_embed(
            guild=interaction.guild, baslik=f"Versiyon {self.versiyon.value}", icerik=self.icerik.value,
            renk=self.cog.settings.renkler["mavi"],
            tur_emoji="<a:cyan:1478524807044923553>", tur_adi="Güncelleme",
            ekstra_alanlar=[("<a:white:1478524885016907998>  Yayın Tarihi", self.tarih.value)],
        )
        await self.cog._gonder_rapor(interaction, embed, "Güncelleme", video_url=self.video.value.strip() or None)


class OnIzlemeModal(discord.ui.Modal, title="Ön İzleme Duyurusu"):
    baslik = discord.ui.TextInput(label="Başlık", placeholder="Ön izleme başlığını yazın...", max_length=200)
    icerik = discord.ui.TextInput(
        label="İçerik",
        placeholder="Detayları yazın. Enter ile alt satıra geçebilirsiniz...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )
    tarih = discord.ui.TextInput(label="Yayın Tarihi", placeholder="Örn: 6 Mart 2026", max_length=100)
    video = discord.ui.TextInput(label="Tanıtım Videosu (opsiyonel)", placeholder="https://...", required=False, max_length=300)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = _duyuru_embed(
            guild=interaction.guild, baslik=self.baslik.value, icerik=self.icerik.value,
            renk=self.cog.settings.renkler["mor"],
            tur_emoji="<a:pink:1478524874061516992>", tur_adi="Ön İzleme",
            ekstra_alanlar=[("<a:white:1478524885016907998>  Yayın Tarihi", self.tarih.value)],
        )
        await self.cog._gonder_rapor(interaction, embed, "Ön İzleme", video_url=self.video.value.strip() or None)


class DuyuruCog(commands.Cog, name="Duyurular"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    async def _gonder_rapor(self, interaction, embed, ad, video_url=None):
        view = _sosyal_view()
        sonuc = await herkese_gonder(interaction.guild, embed, self.settings, video_url=video_url, view=view)
        rapor = discord.Embed(
            title=f"✅  {ad} Gönderildi",
            description=sonuc.ozet(),
            color=self.settings.renkler["yesil"],
            timestamp=datetime.now(timezone.utc),
        )
        rapor.set_footer(text="Ascelia Bot • AWGames")
        await interaction.followup.send(embed=rapor, ephemeral=True)
        log.info(f"{ad} — {interaction.user} | ✓{len(sonuc.basarili)} ✗{len(sonuc.basarisiz)}")

    @app_commands.command(name="duyuru", description="[ADMIN] Tüm üyelere duyuru DM'i gönderir")
    async def duyuru(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        await interaction.response.send_modal(DuyuruModal(self))

    @app_commands.command(name="etkinlik", description="[ADMIN] Tüm üyelere etkinlik duyurusu gönderir")
    async def etkinlik(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        await interaction.response.send_modal(EtkinlikModal(self))

    @app_commands.command(name="çekiliş", description="[ADMIN] Tüm üyelere çekiliş duyurusu gönderir")
    async def cekilis(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        await interaction.response.send_modal(CekilisModal(self))

    @app_commands.command(name="güncelleme", description="[ADMIN] Tüm üyelere güncelleme notu gönderir")
    async def guncelleme(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        await interaction.response.send_modal(GuncellemeModal(self))

    @app_commands.command(name="ön-izleme", description="[ADMIN] Tüm üyelere ön izleme duyurusu gönderir")
    async def on_izleme(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return
        await interaction.response.send_modal(OnIzlemeModal(self))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DuyuruCog(bot))
