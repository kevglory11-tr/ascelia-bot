"""cogs/yardim.py — /yardım komutu."""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from config.settings import Settings

log = logging.getLogger("cog.yardim")


class YardimCog(commands.Cog, name="Yardım"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot      = bot
        self.settings = Settings()

    @app_commands.command(name="yardım", description="Botun tüm komutlarını gösterir")
    async def yardim(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        embed = discord.Embed(color=self.settings.renkler["altin"])

        if guild and guild.icon:
            embed.set_author(name=f"{guild.name} — Komut Rehberi", icon_url=guild.icon.url)
        else:
            embed.set_author(name="Ascelia Bot — Tüm Komutlar")

        embed.description = "```\n⚔️  Ascelia Bot — Tüm Komutlar\n```"

        # ── Genel ──────────────────────────────────────────────
        embed.add_field(
            name="<a:genel:1478389856874004592>  Genel",
            value=(
                "> <:dot1:1478383822625181879> `/yardım` — Bu menü\n"
                "> <:dot1:1478383822625181879> `/sss` — Sıkça sorulan sorular"
            ),
            inline=False,
        )

        # ── Destek ─────────────────────────────────────────────
        embed.add_field(
            name="<a:ticket1:1478391380635287725>  Destek Sistemi",
            value="> <:dot2:1478383869534404712> `/ticket` — Yeni destek talebi oluştur",
            inline=False,
        )

        # ── Başvuru ────────────────────────────────────────────
        embed.add_field(
            name="<a:basvuru:1478389708932255775>  Başvuru Sistemi",
            value="> <:dot3:1478383947976282275> `/başvuru` — Moderatör veya İçerik Üreticisi başvurusu yap",
            inline=False,
        )

        # ── Geri Bildirim ──────────────────────────────────────
        embed.add_field(
            name="<a:bildirim:1478390691334979645>  Geri Bildirim",
            value=(
                "> <:dot4:1478383949620449290> `/öneri` — Sunucu için öneri gönder\n"
                "> <:dot4:1478383949620449290> `/şikayet` — Oyuncu hakkında şikayet bildir"
            ),
            inline=False,
        )

        # ── Ayırıcı ────────────────────────────────────────────
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)

        # ── M2B Coin Sistemi ───────────────────────────────────
        embed.add_field(
            name="<a:coin:1478390167310958734>  M2Board Coin Sistemi",
            value=(
                "> <:dot1:1478383822625181879> `/günlük-giriş` — Günlük 1–50 M2B Coin kazan\n"
                "> <:dot1:1478383822625181879> `/bakiye` — M2B Coin bakiyeni gör\n"
                "> <:dot1:1478383822625181879> `/bakiye @kullanıcı` — Birinin bakiyesine bak\n"
                "> <:dot1:1478383822625181879> `/sıralama` — En zengin 10 kişi\n"
                "> <:dot1:1478383822625181879> `/market` — MP Kuponlarını satın al"
            ),
            inline=False,
        )

        # ── Ayırıcı ────────────────────────────────────────────
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)

        # ── Günlük Görev & Roller ──────────────────────────────
        embed.add_field(
            name="📋  Günlük Görev & Roller",
            value=(
                "> <:dot2:1478383869534404712> `/günlük-görev` — Bugünkü görevini gör ve tamamla\n"
                "> <:dot2:1478383869534404712> `/görev-istatistik` — Toplam görev, mevcut rol ve gem bakiyesi\n"
                "> <:dot2:1478383869534404712> 3 · 6 · 9 · 12 görevde **Vanguard → Harbinger → Sentinel → Luminary** rolü"
            ),
            inline=False,
        )

        # ── Gem Sistemi ────────────────────────────────────────
        embed.add_field(
            name="💎  Gem Sistemi",
            value=(
                "> <:dot3:1478383947976282275> `/gem-al <adet>` — Coin harcayarak Gem satın al\n"
                "> <:dot3:1478383947976282275> `/gem-mağaza` — Perkler ve Gem bilgisi\n"
                "> <:dot3:1478383947976282275> `/perklerim` — Aktif perklerini gör"
            ),
            inline=False,
        )

        # ── Patron Sistemi ─────────────────────────────────────
        embed.add_field(
            name="👹  Patron Sistemi",
            value=(
                "> <:dot4:1478383949620449290> Patron günde 1 kez belirir — saldır, hasar ver!\n"
                "> <:dot4:1478383949620449290> Her hafta en çok hasar veren **top 3** Pazartesi **Gem** ödülü alır\n"
                "> <:dot4:1478383949620449290> `/patron-durum` — Aktif patronun HP ve süresini gör"
            ),
            inline=False,
        )

        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # ── Ayırıcı ────────────────────────────────────────────
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)

        # ── Skor Tahmin ────────────────────────────────────────
        embed.add_field(
            name="⚽  Maç Tahmini",
            value=(
                "> <:dot1:1478383822625181879> `/skor-tahmin` — Yeni maç tahmini oluştur (Admin)\n"
                "> <:dot1:1478383822625181879> `/sonuclar <maç_id> <skor>` — Sonucu gir (Admin)"
            ),
            inline=False,
        )

        embed.set_footer(
            text="Ascelia Bot • AWGames | Bot Owner: Aselica | 🔹 Üye  🔸 Admin",
            icon_url=guild.icon.url if guild and guild.icon else None,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        log.info(f"/yardım — {interaction.user}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YardimCog(bot))
