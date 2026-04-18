"""cogs/yardim.py — /yardım komutu (modern UI)."""

import logging
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import Settings
from utils import ui

log = logging.getLogger("cog.yardim")


# ── Sunucuya özel animasyonlu emojiler ────────────────────────
E_GENEL    = "<a:genel:1478389856874004592>"
E_TICKET   = "<a:ticket1:1478391380635287725>"
E_BASVURU  = "<a:basvuru:1478389708932255775>"
E_BILDIRIM = "<a:bildirim:1478390691334979645>"
E_COIN     = "<a:coin:1478390167310958734>"
E_DOT_A    = "<:dot1:1478383822625181879>"
E_DOT_B    = "<:dot2:1478383869534404712>"
E_DOT_C    = "<:dot3:1478383947976282275>"
E_DOT_D    = "<:dot4:1478383949620449290>"


def _bolum(baslik: str, emoji: str, komutlar: list[tuple[str, str, str]]) -> tuple[str, str]:
    """Kart bölümü döndürür: (name, value)."""
    satirlar = []
    for dot, kmt, acik in komutlar:
        satirlar.append(f"{dot} `{kmt}` {ui.Icon.ARROW} {acik}")
    return f"{emoji}  {baslik}", "\n".join(satirlar)


class YardimCog(commands.Cog, name="Yardım"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot      = bot
        self.settings = Settings()

    @app_commands.command(name="yardım", description="Botun tüm komutlarını gösterir")
    async def yardim(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        embed = discord.Embed(color=ui.Palette.GOLD)
        if guild and guild.icon:
            embed.set_author(name=f"{guild.name} • Komut Rehberi", icon_url=guild.icon.url)
            embed.set_thumbnail(url=guild.icon.url)
        else:
            embed.set_author(name="Ascelia • Komut Rehberi")

        embed.description = ui.header_banner("ASCELIA  —  KOMUT REHBERİ")

        # ── Genel / Destek / Başvuru / Bildirim ─────────────────
        n, v = _bolum("Genel", E_GENEL, [
            (E_DOT_A, "/yardım", "Bu menü"),
            (E_DOT_A, "/sss",     "Sıkça sorulan sorular"),
        ])
        embed.add_field(name=n, value=v, inline=False)

        n, v = _bolum("Destek", E_TICKET, [
            (E_DOT_B, "/ticket", "Yeni destek talebi oluştur"),
        ])
        embed.add_field(name=n, value=v, inline=True)

        n, v = _bolum("Başvuru", E_BASVURU, [
            (E_DOT_C, "/başvuru", "Moderatör · İçerik Üreticisi"),
        ])
        embed.add_field(name=n, value=v, inline=True)

        n, v = _bolum("Geri Bildirim", E_BILDIRIM, [
            (E_DOT_D, "/öneri",   "Sunucu önerisi"),
            (E_DOT_D, "/şikayet", "Oyuncu şikayeti"),
        ])
        embed.add_field(name=n, value=v, inline=False)

        # ── Ekonomi ─────────────────────────────────────────────
        embed.add_field(name=f"{ui.DIVIDER_FAT}", value="\u200b", inline=False)

        n, v = _bolum("M2B Coin Ekonomisi", E_COIN, [
            (E_DOT_A, "/günlük-giriş", "Günlük 1–50 M2B Coin"),
            (E_DOT_A, "/bakiye",        "Bakiyene bak"),
            (E_DOT_A, "/sıralama",      "En zengin 10 kişi"),
            (E_DOT_A, "/market",        "MP Kuponu satın al"),
        ])
        embed.add_field(name=n, value=v, inline=False)

        n, v = _bolum("Günlük Görev · Roller", ui.Icon.SCROLL, [
            (E_DOT_B, "/günlük-görev",    "Görevi gör & tamamla"),
            (E_DOT_B, "/görev-istatistik", "Toplam görev & gem"),
        ])
        v += f"\n{ui.Icon.ARROW} 3 · 6 · 9 · 12 görevde **Vanguard → Harbinger → Sentinel → Luminary**"
        embed.add_field(name=n, value=v, inline=False)

        n, v = _bolum("Gem Sistemi", ui.Icon.GEM, [
            (E_DOT_C, "/gem-al",     "Coin → Gem"),
            (E_DOT_C, "/gem-mağaza", "Perkler"),
            (E_DOT_C, "/perklerim",  "Aktif perklerin"),
        ])
        embed.add_field(name=n, value=v, inline=False)

        n, v = _bolum("Patron", ui.Icon.SKULL, [
            (E_DOT_D, "/patron-durum",    "Aktif patron HP & süre"),
            (E_DOT_D, "/patron-sıralama", "Haftalık hasar sıralaması"),
        ])
        v = f"{ui.Icon.ARROW} Günde 1 kez belirir • Haftalık top 3 {ui.Icon.GEM} kazanır\n" + v
        embed.add_field(name=n, value=v, inline=False)

        # ── Maç Tahmin ─────────────────────────────────────────
        embed.add_field(name=f"{ui.DIVIDER_FAT}", value="\u200b", inline=False)

        n, v = _bolum("Maç Tahmini", "⚽", [
            (E_DOT_A, "/skor-tahmin", "Yeni tahmin (Admin)"),
            (E_DOT_A, "/sonuclar",    "Sonuç gir (Admin)"),
        ])
        embed.add_field(name=n, value=v, inline=False)

        embed.set_footer(
            text=f"Ascelia • AWGames  {ui.Icon.BULLET}  Owner: Aselica  {ui.Icon.BULLET}  🔹 Üye  🔸 Admin",
            icon_url=guild.icon.url if guild and guild.icon else None,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        log.info(f"/yardım — {interaction.user}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YardimCog(bot))
