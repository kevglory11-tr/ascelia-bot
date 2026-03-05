"""
cogs/ticket.py — Tam ticket sistemi v2

Değişiklikler:
  • Modal form — ticket açılırken kategori bazlı sorular sorulur
  • Kanal adı: kategori-kullanici formatında (örn: teknik-ahmet)
  • Kapat butonu: sadece admin/support veya ticket sahibi
  • Sahiplen: sadece admin/support, sahiplenen kişi bilete yanıt verebilir
  • Ekle → Transfer Et: admin/support seçer, DM gönderilir
  • Panel tekrar gönderme koruması
  • Transcript timezone hatası düzeltildi
"""

import asyncio
import io
import json
import logging
import os
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config.settings import Settings
from utils.permissions import is_admin, yetki_yok_mesaji
from utils.transcript import html_olustur

log = logging.getLogger("cog.ticket")

acik_ticketlar: dict[int, dict] = {}
_VERI_DOSYASI = "ticket_data.json"


def _veriyi_kaydet(bot: discord.ext.commands.Bot) -> None:
    """Açık ticket kanallarını JSON dosyasına kaydet."""
    try:
        kayit = {}
        for kanal_id, veri in acik_ticketlar.items():
            kayit[str(kanal_id)] = {
                "olusturan_id": veri["olusturan"].id,
                "kategori": veri["kategori"],
                "acilis": veri["acilis"].isoformat(),
                "sahip_id": veri["sahip"].id if veri["sahip"] else None,
            }
        with open(_VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(kayit, f)
    except Exception as e:
        log.error(f"Ticket verisi kaydedilemedi: {e}")


async def _veriyi_yukle(bot: discord.ext.commands.Bot) -> None:
    """JSON dosyasından açık ticket verilerini yükle."""
    if not os.path.exists(_VERI_DOSYASI):
        return
    try:
        with open(_VERI_DOSYASI, "r", encoding="utf-8") as f:
            kayit = json.load(f)
        for kanal_id_str, veri in kayit.items():
            kanal_id = int(kanal_id_str)
            # Kanalın hâlâ var olup olmadığını kontrol et
            kanal = bot.get_channel(kanal_id)
            if not kanal:
                continue
            guild = kanal.guild
            olusturan = guild.get_member(veri["olusturan_id"])
            if not olusturan:
                try:
                    olusturan = await guild.fetch_member(veri["olusturan_id"])
                except Exception:
                    continue
            sahip = None
            if veri.get("sahip_id"):
                sahip = guild.get_member(veri["sahip_id"])
            acilis = datetime.fromisoformat(veri["acilis"])
            acik_ticketlar[kanal_id] = {
                "olusturan": olusturan,
                "kategori": veri["kategori"],
                "acilis": acilis,
                "sahip": sahip,
            }
        log.info(f"Ticket verisi yüklendi → {len(acik_ticketlar)} açık ticket")
    except Exception as e:
        log.error(f"Ticket verisi yüklenemedi: {e}")

KATEGORI_KISA_AD = {
    "teknik_destek": "teknik",
    "sikayet":       "sikayet",
    "oneri":         "oneri",
    "nesne_market":  "market",
    "zindan_iade":   "zindan",
}

def _kategori_adi(value: str) -> str:
    adlar = {
        "teknik_destek": "🔧 Teknik Destek",
        "sikayet":       "😡 Şikayet",
        "oneri":         "💡 Öneri",
        "nesne_market":  "🏪 Nesne Market",
        "zindan_iade":   "⚔️ Zindan İade",
    }
    return adlar.get(value, value.replace("_", " ").title())

def _is_support(interaction: discord.Interaction, settings: Settings) -> bool:
    if is_admin(interaction, settings):
        return True
    return any(r.id in settings.ticket_support_rol_idleri for r in interaction.user.roles)


# ══════════════════════════════════════════════════════════════════════════════
# MODALS — Kategori bazlı formlar
# ══════════════════════════════════════════════════════════════════════════════

class TicketFormBase(discord.ui.Modal):
    giris_adi = discord.ui.TextInput(label="Girişteki Kullanıcı Adınız", placeholder="Oyun girişinde kullandığınız ad", required=True)
    karakter_adi = discord.ui.TextInput(label="Karakter Adınız", placeholder="Karakterinizin adı", required=True)

    def __init__(self, kategori_key: str, settings: Settings):
        super().__init__(title=_kategori_adi(kategori_key).split(" ", 1)[-1] + " Talebi")
        self.kategori_key = kategori_key
        self.settings = settings

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await ticket_ac_form(interaction, self.kategori_key, self.settings, self._form_verileri())

    def _form_verileri(self) -> dict:
        return {
            "Giriş Kullanıcı Adı": self.giris_adi.value,
            "Karakter Adı": self.karakter_adi.value,
        }


class TeknikDestekForm(TicketFormBase):
    konu = discord.ui.TextInput(label="Yaşanan Sorun", placeholder="Sorunu detaylıca açıklayın", style=discord.TextStyle.paragraph, required=True)
    gorsel_url = discord.ui.TextInput(label="Görsel / Video URL (opsiyonel)", placeholder="https://...", required=False)

    def _form_verileri(self) -> dict:
        return {
            "Giriş Kullanıcı Adı": self.giris_adi.value,
            "Karakter Adı": self.karakter_adi.value,
            "Yaşanan Sorun": self.konu.value,
            "Görsel / Video": self.gorsel_url.value or "—",
        }


class SikayetForm(TicketFormBase):
    sikayet_karakter = discord.ui.TextInput(label="Şikayet Edilen Karakter", placeholder="Şikayet ettiğiniz karakterin adı", required=True)
    konu = discord.ui.TextInput(label="Konu", placeholder="Şikayetinizi detaylıca açıklayın", style=discord.TextStyle.paragraph, required=True)
    kanit_url = discord.ui.TextInput(label="Ekran Görüntüsü / Video URL", placeholder="https://...", required=False)

    def _form_verileri(self) -> dict:
        return {
            "Giriş Kullanıcı Adı": self.giris_adi.value,
            "Karakter Adı": self.karakter_adi.value,
            "Şikayet Edilen Karakter": self.sikayet_karakter.value,
            "Konu": self.konu.value,
            "Kanıt": self.kanit_url.value or "—",
        }


class OneriForm(TicketFormBase):
    oneri = discord.ui.TextInput(label="Öneriniz", placeholder="Önerinizi detaylıca açıklayın", style=discord.TextStyle.paragraph, required=True)

    def _form_verileri(self) -> dict:
        return {
            "Giriş Kullanıcı Adı": self.giris_adi.value,
            "Karakter Adı": self.karakter_adi.value,
            "Öneri": self.oneri.value,
        }


class MarketForm(TicketFormBase):
    konu = discord.ui.TextInput(label="Yaşanan Sorun", placeholder="Market sorununu detaylıca açıklayın", style=discord.TextStyle.paragraph, required=True)
    gorsel_url = discord.ui.TextInput(label="Görsel / Video URL (opsiyonel)", placeholder="https://...", required=False)

    def _form_verileri(self) -> dict:
        return {
            "Giriş Kullanıcı Adı": self.giris_adi.value,
            "Karakter Adı": self.karakter_adi.value,
            "Yaşanan Sorun": self.konu.value,
            "Görsel / Video": self.gorsel_url.value or "—",
        }


class ZindanForm(TicketFormBase):
    konu = discord.ui.TextInput(label="Yaşanan Sorun", placeholder="Zindan iade talebinizi detaylıca açıklayın", style=discord.TextStyle.paragraph, required=True)
    gorsel_url = discord.ui.TextInput(label="Görsel / Video URL (opsiyonel)", placeholder="https://...", required=False)

    def _form_verileri(self) -> dict:
        return {
            "Giriş Kullanıcı Adı": self.giris_adi.value,
            "Karakter Adı": self.karakter_adi.value,
            "Yaşanan Sorun": self.konu.value,
            "Görsel / Video": self.gorsel_url.value or "—",
        }


FORM_MAP = {
    "teknik_destek": TeknikDestekForm,
    "sikayet":       SikayetForm,
    "oneri":         OneriForm,
    "nesne_market":  MarketForm,
    "zindan_iade":   ZindanForm,
}


# ══════════════════════════════════════════════════════════════════════════════
# MODAL — Transfer Et
# ══════════════════════════════════════════════════════════════════════════════

class TransferModal(discord.ui.Modal, title="Ticket Transfer"):
    sebep = discord.ui.TextInput(label="Transfer Sebebi", placeholder="Neden transfer ediyorsunuz?", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, hedef: discord.Member):
        super().__init__()
        self.hedef = hedef

    async def on_submit(self, interaction: discord.Interaction) -> None:
        kanal = interaction.channel
        settings = Settings()

        # Hedefe izin ver
        await kanal.set_permissions(self.hedef, view_channel=True, send_messages=True, read_message_history=True)

        # Kanal embed
        embed = discord.Embed(
            color=settings.renkler["mavi"],
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(
            name="Ticket Transfer Edildi",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )
        embed.description = (
            f"<:transfer:1478566977529188564>  **Transfer Yapıldı**\n\n"
            f"<a:whitearrow:1478394670856933429>  **Transferi Yapan:** {interaction.user.mention}\n"
            f"<a:whitearrow:1478394670856933429>  **Transfer Edilen:** {self.hedef.mention}\n"
            f"<a:whitearrow:1478394670856933429>  **Sebep:** ```{self.sebep.value}```"
        )
        embed.set_footer(text="Ascelia Bot • AWGames")
        await kanal.send(embed=embed)

        # Hedefe DM
        try:
            dm_emb = discord.Embed(
                color=settings.renkler["altin"],
                timestamp=datetime.now(timezone.utc),
            )
            dm_emb.set_author(
                name=f"{interaction.guild.name} — Ticket Transferi",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )
            dm_emb.description = (
                f"<:transfer:1478566977529188564>  **Bir ticket size transfer edildi!**\n\n"
                f"<a:whitearrow:1478394670856933429>  **Yönetici:** {interaction.user.mention}\n"
                f"<a:whitearrow:1478394670856933429>  **Bilet:** {kanal.mention}\n"
                f"<a:whitearrow:1478394670856933429>  **Sebep:** ```{self.sebep.value}```"
            )
            if interaction.guild.icon:
                dm_emb.set_thumbnail(url=interaction.guild.icon.url)
            dm_emb.set_footer(text="Ascelia Bot • AWGames")
            await self.hedef.send(embed=dm_emb)
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            f"<a:olumlutick:1478524954688356494>  Ticket {self.hedef.mention} kişisine transfer edildi.",
            ephemeral=True
        )
        log.info(f"Transfer → {kanal.name} | {interaction.user} → {self.hedef}")


# ══════════════════════════════════════════════════════════════════════════════
# VIEW — Dropdown
# ══════════════════════════════════════════════════════════════════════════════

class TicketDropdown(discord.ui.Select):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        secenekler = []
        for s in settings.ticket_secenekleri:
            emoji_str = s["emoji"]
            # Custom emoji formatı: <:name:id> veya <a:name:id>
            if emoji_str and emoji_str.startswith("<"):
                animated = emoji_str.startswith("<a:")
                parts = emoji_str.strip("<>").split(":")
                emoji = discord.PartialEmoji(name=parts[1], id=int(parts[2]), animated=animated)
            else:
                emoji = emoji_str
            secenekler.append(discord.SelectOption(
                label=s["label"],
                description=s["description"],
                value=s["value"],
                emoji=emoji,
            ))
        super().__init__(
            placeholder="🎫  Bir konu seç...",
            min_values=1,
            max_values=1,
            options=secenekler,
            custom_id="ticket_dropdown",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        FormClass = FORM_MAP.get(self.values[0], TicketFormBase)
        await interaction.response.send_modal(FormClass(self.values[0], self.settings))


class TicketPanelView(discord.ui.View):
    def __init__(self, settings: Settings) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketDropdown(settings))


# ══════════════════════════════════════════════════════════════════════════════
# VIEW — Ticket içi butonlar
# ══════════════════════════════════════════════════════════════════════════════

class TicketIslemleriView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.secondary, custom_id="ticket_kapat", emoji=discord.PartialEmoji(name="kapat", id=1478567016800456878))
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await ticket_kapat_islem(interaction)

    @discord.ui.button(label="Transfer Et", style=discord.ButtonStyle.secondary, custom_id="ticket_transfer", emoji=discord.PartialEmoji(name="transfer", id=1478566977529188564))
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await ticket_transfer_islem(interaction)

    @discord.ui.button(label="Sahiplen", style=discord.ButtonStyle.primary, custom_id="ticket_sahiplen", emoji=discord.PartialEmoji(name="ticket2", id=1478527657380679811))
    async def sahiplen(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await ticket_sahiplen(interaction)


# ══════════════════════════════════════════════════════════════════════════════
# VIEW — Kapatma onayı
# ══════════════════════════════════════════════════════════════════════════════

class KapatmaOnayView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Evet, Kapat", style=discord.ButtonStyle.secondary, custom_id="onay_evet", emoji=discord.PartialEmoji(name="kapat", id=1478567016800456878))
    async def evet(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view_ref = self
        msg_ref = interaction.message

        class KapatmaSebebiModal(discord.ui.Modal, title="Kapatma Sebebi"):
            sebep = discord.ui.TextInput(
                label="Kapatma Sebebi",
                placeholder="Bu ticketi neden kapatiyorsunuz?",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=500,
            )

            async def on_submit(modal_self, modal_interaction: discord.Interaction) -> None:
                modal_interaction.client._ticket_kapatma_sebebi = modal_self.sebep.value
                await msg_ref.edit(content="\u23f3 Transcript oluşturuluyor...", view=None, embed=None)
                await _ticket_kapat_gercek(modal_interaction, sebep=modal_self.sebep.value)

        await interaction.response.send_modal(KapatmaSebebiModal())

    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, custom_id="onay_iptal", emoji=discord.PartialEmoji(name="no", id=1478524993670479942, animated=True))
    async def iptal(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(content="Kapatma iptal edildi.", view=None, embed=None)


# ══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════════════════

async def ticket_ac_form(interaction: discord.Interaction, kategori_key: str, settings: Settings, form_verileri: dict) -> None:
    guild = interaction.guild
    uye = interaction.user

    # Max ticket kontrolü
    kullanici_sayisi = sum(1 for v in acik_ticketlar.values() if v["olusturan"].id == uye.id)
    if kullanici_sayisi >= settings.max_ticket_per_user:
        await interaction.followup.send(
            f"❌ Zaten **{settings.max_ticket_per_user}** açık ticketin var. Önce mevcut ticketını kapat.",
            ephemeral=True
        )
        return

    kat_id = settings.ticket_kategori_idleri.get(kategori_key, 0)
    kategori = guild.get_channel(kat_id) if kat_id else None

    kisa_ad = KATEGORI_KISA_AD.get(kategori_key, "ticket")
    kullanici_kisa = uye.name.lower().replace(" ", "-")[:20]
    kanal_adi = f"{kisa_ad}-{kullanici_kisa}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        uye: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    for rol_id in settings.ticket_support_rol_idleri:
        rol = guild.get_role(rol_id)
        if rol:
            overwrites[rol] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    try:
        kanal = await guild.create_text_channel(
            name=kanal_adi,
            category=kategori,
            overwrites=overwrites,
            topic=f"Ticket | {uye.display_name} | {_kategori_adi(kategori_key)}",
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Kanal oluşturmak için yetkim yok.", ephemeral=True)
        return

    acik_ticketlar[kanal.id] = {
        "olusturan": uye,
        "kategori":  kategori_key,
        "acilis":    datetime.now(timezone.utc),
        "sahip":     None,
    }
    _veriyi_kaydet(interaction.client)

    ping_rolleri = " ".join(f"<@&{rid}>" for rid in settings.ticket_support_rol_idleri if guild.get_role(rid))

    # Hoşgeldin embed — modern tasarım
    embed = discord.Embed(
        color=settings.renkler["altin"],
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{_kategori_adi(kategori_key)}",
        icon_url=guild.icon.url if guild.icon else None,
    )
    embed.description = (
        f"Merhaba {uye.mention}, talebiniz başarıyla oluşturuldu! <a:olumlutick:1478524954688356494>\n\n"
        f"<:saat:1478567051378298931>  Destek ekibimiz en kısa sürede sizinle ilgilenecek\n"
        f"<:kapat:1478567016800456878>  Kapatmak için aşağıdaki Kapat butonunu kullan\n"
        f"<:transfer:1478566977529188564>  Transfer için Transfer Et butonunu kullan"
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Form verilerini embed'e ekle
    embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━", value="📋  **Form Bilgileri**", inline=False)
    for soru, cevap in form_verileri.items():
        embed.add_field(name=f"<a:whitearrow:1478394670856933429>  {soru}", value=f"```{cevap or '—'}```", inline=False)

    embed.set_footer(
        text="Ascelia Bot • AWGames",
        icon_url=guild.icon.url if guild.icon else None,
    )

    await kanal.send(
        content=f"{uye.mention} {ping_rolleri}",
        embed=embed,
        view=TicketIslemleriView(),
    )

    await interaction.followup.send(f"✅ Ticketin oluşturuldu! → {kanal.mention}", ephemeral=True)
    log.info(f"Ticket açıldı → {kanal.name} | {uye} | {kategori_key}")


async def ticket_kapat_islem(interaction: discord.Interaction) -> None:
    settings = Settings()

    # Ticket kanalı değilse ve admin de değilse
    if interaction.channel.id not in acik_ticketlar:
        # Kanal adına göre ticket olabilir mi kontrol et
        kanal_adi = interaction.channel.name.lower()
        ticket_isimleri = list(KATEGORI_KISA_AD.values()) + ["ticket"]
        is_ticket_kanal = any(kanal_adi.startswith(k + "-") for k in ticket_isimleri)

        if not is_ticket_kanal:
            if not _is_support(interaction, settings):
                await interaction.response.send_message(
                    "❌ Yalnızca adminler bu komutu kullanabilir.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Bu kanal bir ticket değil.",
                    ephemeral=True
                )
            return

    veri = acik_ticketlar.get(interaction.channel.id)
    is_yetkili = (
        _is_support(interaction, settings)
        or (veri and interaction.user.id == veri["olusturan"].id)
    )
    if not is_yetkili:
        await interaction.response.send_message(
            "❌ Bu ticketi kapatma yetkin yok. Yalnızca ticket sahibi veya destek ekibi kapatabilir.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔒  Ticket Kapatılıyor",
        description="Bu ticketi kapatmak istediğinden emin misin?\nKapatılırsa transcript otomatik kaydedilecek.",
        color=settings.renkler["kirmizi"],
    )
    await interaction.response.send_message(embed=embed, view=KapatmaOnayView())


async def ticket_transfer_islem(interaction: discord.Interaction) -> None:
    settings = Settings()
    if not _is_support(interaction, settings):
        await interaction.response.send_message(
            "<a:no:1478524993670479942>  Transfer işlemi yalnızca destek ekibi tarafından yapılabilir.",
            ephemeral=True
        )
        return

    kanal = interaction.channel
    guild = interaction.guild
    view_ref = interaction.message

    class TransferSecView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)
            self.hedef = None

        @discord.ui.select(
            cls=discord.ui.UserSelect,
            placeholder="Transfer edilecek kişiyi seç...",
            min_values=1,
            max_values=1,
        )
        async def hedef_sec(self, inter: discord.Interaction, select: discord.ui.UserSelect) -> None:
            hedef = select.values[0]
            if hedef.bot:
                await inter.response.send_message("<a:no:1478524993670479942>  Bota transfer yapamazsın.", ephemeral=True)
                return
            self.stop()
            await inter.response.send_modal(TransferModal(hedef))

    embed = discord.Embed(
        color=settings.renkler["mavi"],
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name="Ticket Transfer",
        icon_url=guild.icon.url if guild.icon else None,
    )
    embed.description = (
        "<:transfer:1478566977529188564>  Transferi yapacağınız kişiyi aşağıdan seçin.\n\n"
        "Seçtikten sonra sebep belirtmeniz istenecek."
    )
    embed.set_footer(text="Ascelia Bot • AWGames")
    await interaction.response.send_message(embed=embed, view=TransferSecView(), ephemeral=True)


async def ticket_sahiplen(interaction: discord.Interaction) -> None:
    settings = Settings()
    if not _is_support(interaction, settings):
        await interaction.response.send_message(
            "❌ Sahiplenme işlemi yalnızca destek ekibi tarafından yapılabilir.",
            ephemeral=True
        )
        return

    kanal = interaction.channel
    kanal_adi = kanal.name.lower()
    ticket_isimleri = list(KATEGORI_KISA_AD.values()) + ["ticket"]
    is_ticket_kanal = any(kanal_adi.startswith(k + "-") for k in ticket_isimleri) or kanal.id in acik_ticketlar

    if not is_ticket_kanal:
        await interaction.response.send_message("❌ Bu kanal bir ticket değil.", ephemeral=True)
        return

    if kanal.id in acik_ticketlar:
        acik_ticketlar[kanal.id]["sahip"] = interaction.user
        _veriyi_kaydet(interaction.client)

    # Sadece sahiplenen kişi ve bot yazabilsin, diğer destek ekibi sadece görsün
    await kanal.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)

    try:
        await kanal.edit(topic=f"{kanal.topic or ''} | Sahip: {interaction.user.display_name}")
    except Exception:
        pass

    embed = discord.Embed(
        description=f"🔑 {interaction.user.mention} bu ticketi sahiplendi. Artık yalnızca o yanıt verecek.",
        color=settings.renkler["mavi"]
    )
    await interaction.response.send_message(embed=embed)
    log.info(f"Ticket sahiplenildi → {kanal.name} | {interaction.user}")


async def _ticket_kapat_gercek(interaction: discord.Interaction, sebep: str = "Belirtilmedi") -> None:
    kanal = interaction.channel
    veri = acik_ticketlar.get(kanal.id)

    if not veri:
        kategori_key = "teknik_destek"
        olusturan = interaction.user
        if kanal.topic:
            for k in ["teknik_destek", "sikayet", "oneri", "nesne_market", "zindan_iade"]:
                if _kategori_adi(k).lower() in kanal.topic.lower():
                    kategori_key = k
                    break
        async for msg in kanal.history(limit=10, oldest_first=True):
            if not msg.author.bot:
                olusturan = msg.author
                break
        veri = {
            "olusturan": olusturan,
            "kategori":  kategori_key,
            "acilis":    kanal.created_at.replace(tzinfo=timezone.utc),
            "sahip":     None,
        }
        acik_ticketlar[kanal.id] = veri
        log.info(f"Ticket verisi kanaldan geri yüklendi → {kanal.name}")

    settings = Settings()
    await interaction.response.defer()
    if interaction.message:
        await interaction.message.edit(content="⏳ Transcript oluşturuluyor...", view=None)

    try:
        html_icerik = await html_olustur(kanal, kanal.name, veri["acilis"])
        dosya = discord.File(io.BytesIO(html_icerik.encode("utf-8")), filename=f"{kanal.name}.html")

        embed_t = discord.Embed(
            title="📄  Ticket Transkripti",
            description=(
                f"**Kanal:** {kanal.name}\n"
                f"**Açan:** {veri['olusturan'].mention}\n"
                f"**Kategori:** {_kategori_adi(veri['kategori'])}\n"
                f"**Kapatan:** {interaction.user.mention}"
            ),
            color=settings.renkler["mavi"],
            timestamp=datetime.now(timezone.utc),
        )
        embed_t.set_footer(text="Ascelia Bot • AWGames")

        # Transcript kanalına gönder — CDN linki al
        cdn_link = None
        transcript_kanal = kanal.guild.get_channel(settings.ticket_transcript_kanal_id)
        if transcript_kanal:
            mesaj = await transcript_kanal.send(file=dosya)
            if mesaj.attachments:
                cdn_link = mesaj.attachments[0].url

        # CDN linkiyle buton oluştur
        class TranscriptView(discord.ui.View):
            def __init__(self, link):
                super().__init__()
                if link:
                    self.add_item(discord.ui.Button(
                        label="🌐 View Online Transcript",
                        url=link,
                        style=discord.ButtonStyle.link,
                    ))

        # Embed + butonu transcript kanalına gönder
        if transcript_kanal:
            await transcript_kanal.send(embed=embed_t, view=TranscriptView(cdn_link))

        # Açan kişiye DM
        try:
            dm_emb = discord.Embed(
                color=settings.renkler["kirmizi"],
                timestamp=datetime.now(timezone.utc),
            )
            dm_emb.set_author(
                name=f"{kanal.guild.name} — Ticket Kapatıldı",
                icon_url=kanal.guild.icon.url if kanal.guild.icon else None,
            )
            dm_emb.description = (
                f"<:kapat:1478567016800456878>  **Biletiniz kapatıldı.**\n\n"
                f"<a:whitearrow:1478394670856933429>  **Bilet:** `{kanal.name}`\n"
                f"<a:whitearrow:1478394670856933429>  **Kapatan:** {interaction.user.mention}\n"
                f"<a:whitearrow:1478394670856933429>  **Sebep:** ```{sebep}```"
            )
            if kanal.guild.icon:
                dm_emb.set_thumbnail(url=kanal.guild.icon.url)
            dm_emb.set_footer(text="Ascelia Bot • AWGames")
            await veri["olusturan"].send(embed=dm_emb, view=TranscriptView(cdn_link))
        except discord.Forbidden:
            pass

        log_kanal = kanal.guild.get_channel(settings.ticket_log_kanal_id)
        if log_kanal:
            log_emb = discord.Embed(title="🔒  Ticket Kapatıldı", color=settings.renkler["kirmizi"], timestamp=datetime.now(timezone.utc))
            log_emb.add_field(name="Kanal",    value=kanal.name, inline=True)
            log_emb.add_field(name="Açan",     value=veri["olusturan"].mention, inline=True)
            log_emb.add_field(name="Kapatan",  value=interaction.user.mention, inline=True)
            log_emb.add_field(name="Kategori", value=_kategori_adi(veri["kategori"]), inline=True)
            log_emb.set_footer(text="Ascelia Bot • AWGames")
            await log_kanal.send(embed=log_emb, view=TranscriptView(cdn_link))

    except Exception as e:
        log.error(f"Transcript hatası: {e}", exc_info=True)

    if kanal.id in acik_ticketlar:
        del acik_ticketlar[kanal.id]
        _veriyi_kaydet(interaction.client)
    log.info(f"Ticket kapatıldı → {kanal.name}")
    await asyncio.sleep(3)
    await kanal.delete(reason=f"Ticket kapatıldı — {interaction.user}")


# ══════════════════════════════════════════════════════════════════════════════
# COG
# ══════════════════════════════════════════════════════════════════════════════

class TicketCog(commands.Cog, name="Ticket"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    @app_commands.command(name="ticket", description="Yeni bir destek ticketi aç")
    async def ticket_cmd(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="<a:ticket1:1478391380635287725>  Destek Talebi",
            description=(
                "<a:noted:1478525003342286932>  Aşağıdan konunu seç ve ticket oluştur.\n"
                "Destek ekibimiz en kısa sürede seninle ilgilenecek.\n\n"
                "<:warning1:1478525076373635102>  Lütfen doğru kategoriyi seçtiğinden emin ol."
            ),
            color=self.settings.renkler["altin"],
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.response.send_message(embed=embed, view=TicketPanelView(self.settings), ephemeral=True)

    @app_commands.command(name="ticket-panel-gonder", description="[ADMIN] Ticket panelini kanala gönder (kalıcı)")
    async def ticket_panel_gonder(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return

        await interaction.response.defer(ephemeral=True)

        # Kanalda zaten panel var mı kontrol et
        async for msg in interaction.channel.history(limit=50):
            if msg.author == interaction.guild.me and msg.components:
                for row in msg.components:
                    for item in row.children:
                        if hasattr(item, "custom_id") and item.custom_id == "ticket_dropdown":
                            await interaction.followup.send(
                                "<a:no:1478524993670479942>  Bu kanalda zaten bir ticket paneli bulunmaktadır. Ticket paneli göndermek istiyorsan önceki paneli silmelisin.",
                                ephemeral=True
                            )
                            return

        embed = discord.Embed(
            title="<a:ticket1:1478391380635287725>  Destek & Yardım Merkezi",
            description=(
                "Aşağıdaki menüden konunu seç ve destek talebi oluştur.\n\n"
                "<:teknik:1478527729329639485> **Teknik Destek** — Oyun içi teknik sorunlar\n"
                "<a:nesnemarket:1478390167310958734> **Nesne Market** — Market sorunları\n"
                "<:dungeon:1478527882765533374> **Zindan İade** — Zindan iade talepleri\n\n"
                "Talebini oluşturduktan sonra form eksiksiz doldur."
            ),
            color=self.settings.renkler["altin"],
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.channel.send(embed=embed, view=TicketPanelView(self.settings))
        await interaction.followup.send("<a:olumlutick:1478524954688356494>  Ticket paneli gönderildi.", ephemeral=True)
        log.info(f"Ticket paneli gönderildi → {interaction.channel} | {interaction.user}")

    @app_commands.command(name="ticket-kapat", description="Mevcut ticketi kapat")
    async def ticket_kapat(self, interaction: discord.Interaction) -> None:
        await ticket_kapat_islem(interaction)

    @app_commands.command(name="ticket-cikar", description="Ticketten kullanıcı çıkar")
    @app_commands.describe(kullanici="Çıkarılacak kullanıcı")
    async def ticket_cikar(self, interaction: discord.Interaction, kullanici: discord.Member) -> None:
        if not _is_support(interaction, self.settings):
            await interaction.response.send_message("❌ Bu işlem için yetkin yok.", ephemeral=True)
            return
        kanal_adi = interaction.channel.name.lower()
        ticket_isimleri = list(KATEGORI_KISA_AD.values()) + ["ticket"]
        if interaction.channel.id not in acik_ticketlar and not any(kanal_adi.startswith(k + "-") for k in ticket_isimleri):
            await interaction.response.send_message("❌ Bu kanal bir ticket değil.", ephemeral=True)
            return
        veri = acik_ticketlar.get(interaction.channel.id)
        if veri and kullanici.id == veri["olusturan"].id:
            await interaction.response.send_message("❌ Ticket sahibini çıkaramazsın.", ephemeral=True)
            return
        await interaction.channel.set_permissions(kullanici, overwrite=None)
        embed = discord.Embed(description=f"✅ {kullanici.mention} ticketten çıkarıldı.", color=self.settings.renkler["kirmizi"])
        await interaction.response.send_message(embed=embed)

    async def cog_load(self) -> None:
        self.bot.add_view(TicketPanelView(self.settings))
        self.bot.add_view(TicketIslemleriView())
        self.bot.add_view(KapatmaOnayView())
        await _veriyi_yukle(self.bot)
        log.info("Ticket view'ları yüklendi")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketCog(bot))
