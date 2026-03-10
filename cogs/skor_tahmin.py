"""cogs/skor_tahmin.py — Maç skoru tahmin sistemi."""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
import asyncio
import os

import database
from utils.logger import setup_logger

log       = setup_logger("skor_tahmin")
TR_OFFSET = timedelta(hours=3)
M2B       = "<:m2bcoin:1480481551337783437>"
OK        = "<a:check:1478394670856933429>"
BILDIRIM  = "<a:bildirim:1478390691334979645>"
COIN_ANIM = "<a:coin:1478390167310958734>"

# Aktif maçlar: {mac_id: MacData}
aktif_maclar: dict = {}


class MacData:
    def __init__(self, mac_id, ev, ev_logo, dep, dep_logo, mac_zamani, kanal_id, mesaj_id=None):
        self.mac_id    = mac_id
        self.ev        = ev
        self.ev_logo   = ev_logo
        self.dep       = dep
        self.dep_logo  = dep_logo
        self.mac_zamani = mac_zamani  # datetime (TR)
        self.kanal_id  = kanal_id
        self.mesaj_id  = mesaj_id
        self.kapali    = False
        self.tahminler = {}  # {discord_id: {"skor": "2-1", "zaman": datetime}}


class SkorModal(discord.ui.Modal, title="Skor Tahmini"):
    skor = discord.ui.TextInput(
        label="Tahmininiz (örn: 2-1, 0-0)",
        placeholder="Ev sahibi - Deplasman (örn: 2-1)",
        min_length=3,
        max_length=10,
    )

    def __init__(self, mac: MacData):
        super().__init__()
        self.mac = mac

    async def on_submit(self, interaction: discord.Interaction):
        # Format kontrolü
        skor_val = self.skor.value.strip().replace(" ", "")
        parcalar = skor_val.split("-")
        if len(parcalar) != 2 or not all(p.isdigit() for p in parcalar):
            await interaction.response.send_message(
                "❌ Geçersiz format! Örnek: `2-1` veya `0-0`", ephemeral=True
            )
            return

        if self.mac.kapali:
            await interaction.response.send_message(
                "❌ Bu maçın tahminleri kapandı!", ephemeral=True
            )
            return

        onceki = self.mac.tahminler.get(interaction.user.id)
        self.mac.tahminler[interaction.user.id] = {
            "skor":  skor_val,
            "zaman": datetime.now(timezone.utc),
            "isim":  interaction.user.display_name,
        }

        if onceki:
            await interaction.response.send_message(
                f"{OK} Tahminin güncellendi: **{skor_val}** "
                f"({self.mac.ev} - {self.mac.dep})",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{OK} Tahminin kaydedildi: **{skor_val}** "
                f"({self.mac.ev} - {self.mac.dep})\n"
                f"Maç sonunda ilk **5 doğru tahmin** 🎟️ **100 MP Kuponu** kazanır!",
                ephemeral=True,
            )
        log.info(f"Tahmin: {interaction.user} → {skor_val} ({self.mac.mac_id})")


class TahminView(discord.ui.View):
    def __init__(self, mac: MacData):
        super().__init__(timeout=None)
        self.mac = mac

    @discord.ui.button(label="⚽ Tahmin Yap", style=discord.ButtonStyle.primary, custom_id="tahmin_yap")
    async def tahmin_yap(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.mac.kapali:
            await interaction.response.send_message(
                "❌ Bu maçın tahminleri kapandı!", ephemeral=True
            )
            return
        await interaction.response.send_modal(SkorModal(self.mac))


def _mac_embed(mac: MacData, kapali: bool = False) -> discord.Embed:
    tr_zaman = mac.mac_zamani
    zaman_str = tr_zaman.strftime("%d.%m.%Y %H:%M")

    embed = discord.Embed(
        title=f"⚽ Maç Skoru Tahmini",
        description=(
            f"**{mac.ev}  🆚  {mac.dep}**\n\n"
            f"📅 Tarih: **{zaman_str}**\n"
            f"👥 Tahmin sayısı: **{len(mac.tahminler)}**\n\n"
            f"🏆 İlk **5 doğru tahmin** → 🎟️ **100 MP Kuponu**\n\n"
            + ("⏰ **Tahminler kapandı!**" if kapali else
               f"⏳ Tahminler maç saatine kadar açık!")
        ),
        color=0x95A5A6 if kapali else 0x2ECC71,
    )

    if mac.ev_logo:
        embed.set_thumbnail(url=mac.ev_logo)
    if mac.dep_logo:
        embed.set_image(url=mac.dep_logo)

    embed.set_footer(text=f"Maç ID: {mac.mac_id} | Tahmin yap butonuna bas!")
    return embed


class SkorTahminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _admin_mi(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        rol = discord.utils.get(interaction.guild.roles, name="Admin")
        return bool(rol and rol in interaction.user.roles)

    @app_commands.command(name="skor-tahmin", description="[Admin] Yeni maç tahmini oluştur.")
    @app_commands.describe(
        ev_takim="Ev sahibi takım adı",
        ev_logo="Ev sahibi takım logo URL'si",
        dep_takim="Deplasman takım adı",
        dep_logo="Deplasman takım logo URL'si",
        tarih="Maç tarihi (GG.AA.YYYY)",
        saat="Maç saati (SS:DD)",
        kanal="Tahminin yayınlanacağı kanal",
    )
    async def skor_tahmin(
        self,
        interaction: discord.Interaction,
        ev_takim: str,
        ev_logo: str,
        dep_takim: str,
        dep_logo: str,
        tarih: str,
        saat: str,
        kanal: discord.TextChannel,
    ):
        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Tarih parse
        try:
            mac_zamani = datetime.strptime(f"{tarih} {saat}", "%d.%m.%Y %H:%M")
        except ValueError:
            await interaction.followup.send(
                "❌ Tarih formatı hatalı! Örnek: `10.03.2026` `20:45`", ephemeral=True
            )
            return

        # Maç ID
        mac_id = f"{ev_takim[:3].upper()}{dep_takim[:3].upper()}{mac_zamani.strftime('%d%m%H%M')}"

        mac = MacData(mac_id, ev_takim, ev_logo, dep_takim, dep_logo, mac_zamani, kanal.id)
        aktif_maclar[mac_id] = mac

        embed = _mac_embed(mac)
        view  = TahminView(mac)
        mesaj = await kanal.send(embed=embed, view=view)
        mac.mesaj_id = mesaj.id

        await interaction.followup.send(
            f"{OK} Tahmin başlatıldı! Maç ID: `{mac_id}`\n"
            f"Maç saatinde tahminler otomatik kapanır.\n"
            f"Sonuçları girmek için: `/sonuclar {mac_id} <skor>`",
            ephemeral=True,
        )
        log.info(f"Yeni maç: {mac_id} — {ev_takim} vs {dep_takim}")

        # Maç saatinde otomatik kapat
        asyncio.create_task(self._otomatik_kapat(mac, mesaj))

    async def _otomatik_kapat(self, mac: MacData, mesaj: discord.Message):
        # TR saati → UTC farkı hesapla
        simdi_utc = datetime.now(timezone.utc)
        mac_utc   = mac.mac_zamani.replace(tzinfo=timezone(TR_OFFSET))
        bekle     = (mac_utc - simdi_utc).total_seconds()

        if bekle > 0:
            await asyncio.sleep(bekle)

        if mac.kapali:
            return

        mac.kapali = True
        try:
            embed = _mac_embed(mac, kapali=True)
            await mesaj.edit(embed=embed, view=None)
            log.info(f"Tahminler kapandı: {mac.mac_id} ({len(mac.tahminler)} tahmin)")
        except Exception as e:
            log.error(f"Otomatik kapama hatası: {e}")

    @app_commands.command(name="sonuclar", description="[Admin] Maç sonucunu gir ve kazananları ilan et.")
    @app_commands.describe(
        mac_id="Maç ID'si (/skor-tahmin sonrası verilir)",
        gercek_skor="Gerçek maç skoru (örn: 2-1)",
    )
    async def sonuclar(self, interaction: discord.Interaction, mac_id: str, gercek_skor: str):
        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer()

        mac = aktif_maclar.get(mac_id)
        if not mac:
            await interaction.followup.send(
                f"❌ `{mac_id}` ID'li maç bulunamadı! Bot yeniden başlatılmışsa kayıtlar silinmiş olabilir.",
                ephemeral=True,
            )
            return

        # Format kontrol
        parcalar = gercek_skor.strip().replace(" ", "").split("-")
        if len(parcalar) != 2 or not all(p.isdigit() for p in parcalar):
            await interaction.followup.send(
                "❌ Geçersiz skor formatı! Örnek: `2-1`", ephemeral=True
            )
            return

        mac.kapali = True

        # Kazananları bul — zaman sırasına göre ilk 5
        kazananlar = [
            (uid, data) for uid, data in mac.tahminler.items()
            if data["skor"] == gercek_skor.strip().replace(" ", "")
        ]
        kazananlar.sort(key=lambda x: x[1]["zaman"])
        kazananlar = kazananlar[:5]

        # Sonuç embed'i
        embed = discord.Embed(
            title=f"🏆 Maç Sonucu — {mac.ev} vs {mac.dep}",
            description=f"**Gerçek Skor: {gercek_skor}**\n\n",
            color=0xFFD700,
        )

        if mac.ev_logo:
            embed.set_thumbnail(url=mac.ev_logo)

        embed.description += f"📊 Toplam tahmin: **{len(mac.tahminler)}**\n"
        embed.description += f"✅ Doğru tahmin: **{len(kazananlar)}**\n\n"

        if kazananlar:
            embed.description += "🎟️ **100 MP Kupon Kazananları:**\n"
            for i, (uid, data) in enumerate(kazananlar, 1):
                uye = interaction.guild.get_member(uid)
                mention = uye.mention if uye else data["isim"]
                embed.description += f"> **{i}.** {mention}\n"
            embed.description += "\n⚠️ Kazananlar en kısa sürede ticket açsın!"
        else:
            embed.description += "😔 Doğru tahmin yapan olmadı!"

        embed.set_footer(text=f"Maç ID: {mac_id}")

        # Maç kanalına gönder
        kanal = self.bot.get_channel(mac.kanal_id)
        if kanal:
            await kanal.send(embed=embed)

        # Orijinal mesajı güncelle
        if mac.mesaj_id and kanal:
            try:
                mesaj = await kanal.fetch_message(mac.mesaj_id)
                bitis_embed = _mac_embed(mac, kapali=True)
                bitis_embed.add_field(
                    name="🏆 Sonuç",
                    value=f"Gerçek skor: **{gercek_skor}**",
                    inline=False,
                )
                await mesaj.edit(embed=bitis_embed, view=None)
            except Exception:
                pass

        await interaction.followup.send(
            f"{OK} Sonuçlar ilan edildi! {len(kazananlar)} kazanan.",
            ephemeral=True,
        )
        log.info(f"Sonuç girildi: {mac_id} → {gercek_skor} | {len(kazananlar)} kazanan")
        del aktif_maclar[mac_id]


async def setup(bot: commands.Bot):
    await bot.add_cog(SkorTahminCog(bot))
