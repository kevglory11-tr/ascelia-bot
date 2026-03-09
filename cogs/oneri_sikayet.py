# -*- coding: utf-8 -*-
"""cogs/oneri_sikayet.py — /oneri ve /sikayet komutları."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config.settings import Settings
from utils.cooldown import oneri_cooldown, sikayet_cooldown
from utils.dm_queue import dm_queue

_ONERI_COOLDOWN_SURE  = 600.0  # 10 dakika
_SIKAYET_COOLDOWN_SURE = 600.0  # 10 dakika

log = logging.getLogger("cog.oneri_sikayet")


# ══════════════════════════════════════════════════════════════════════════════
# VIEW — Öneri inceleme butonları
# ══════════════════════════════════════════════════════════════════════════════

class OneriIncelemeView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    def _gonderen_id(self, embed: discord.Embed) -> Optional[int]:
        if embed.description:
            m = re.search(r"ID:\*\* `(\d+)`", embed.description)
            if m:
                return int(m.group(1))
        return None

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True

    async def _dm_gonder(self, uye: discord.Member, baslik: str, aciklama: str, renk: discord.Color):
        try:
            dm = discord.Embed(
                title=baslik,
                description=aciklama,
                color=renk,
                timestamp=datetime.now(timezone.utc),
            )
            dm.set_footer(text="Ascelia Bot • AWGames")
            await uye.send(embed=dm)
        except discord.Forbidden as e:
            hata_kodu = getattr(e, 'code', 0)
            if hata_kodu != 50007:
                log.warning(f"DM Forbidden (kod={hata_kodu}) → {uye}: {e}")

    @discord.ui.button(label="İşleme Alındı", style=discord.ButtonStyle.success, custom_id="oneri_kabul",
                       emoji=discord.PartialEmoji(name="olumlutick", id=1478524954688356494, animated=True))
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"İşleme Alındı — {interaction.user.display_name} • Ascelia Bot • AWGames")
        self.disable_all_items()
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("<a:olumlutick:1478524954688356494>  İşleme alındı olarak işaretlendi.", ephemeral=True)

        uid = self._gonderen_id(embed)
        if uid:
            try:
                uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            except Exception:
                uye = None
            if uye:
                await self._dm_gonder(
                    uye,
                    "<a:genel:1478389856874004592>  Öneriniz İşleme Alındı!",
                    (
                        "<:oneriiletildi:1478613938529763349>  Sunucumuza ilettiğiniz öneri yönetici ekibimiz tarafından **işleme alındı.**\n\n"
                        "<:dot1:1478383822625181879>  Öneriniz titizlikle değerlendirilecek ve oyun deneyimine katkı sağlayacak her fikir bizim için değerlidir. Düzenleme ve iyileştirmeleri güncelleme notlarından takip edebilirsiniz.\n\n"
                        "<a:bildirim:1478390691334979645>  Oyuna katkı sağladığınız ve geri dönüş verdiğiniz için teşekkür ederiz! "
                        "Sizin gibi aktif oyuncular topluluğumuzu daha iyi bir yer yapar. <a:yellow:1478524892801667203>"
                    ),
                    discord.Color.green()
                )

    @discord.ui.button(label="Reddedildi", style=discord.ButtonStyle.danger, custom_id="oneri_red",
                       emoji=discord.PartialEmoji(name="no", id=1478524993670479942, animated=True))
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = interaction.message.embeds[0]
        uid = self._gonderen_id(embed)
        view_ref = self
        msg_ref = interaction.message
        user_ref = interaction.user

        class RedSebebiModal(discord.ui.Modal, title="Reddetme Sebebi"):
            sebep = discord.ui.TextInput(
                label="Reddetme Sebebi",
                placeholder="Önerinin neden reddedildiğini açıklayın...",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=500,
            )

            async def on_submit(modal_self, modal_interaction: discord.Interaction) -> None:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"Reddedildi — {user_ref.display_name} • Ascelia Bot • AWGames")
                embed.add_field(name="Red Sebebi", value=f"```{modal_self.sebep.value}```", inline=False)
                view_ref.disable_all_items()
                await msg_ref.edit(embed=embed, view=view_ref)
                await modal_interaction.response.send_message("<a:no:1478524993670479942>  Reddedildi olarak işaretlendi.", ephemeral=True)

                if uid:
                    try:
                        uye = modal_interaction.guild.get_member(uid) or await modal_interaction.guild.fetch_member(uid)
                    except Exception:
                        uye = None
                    if uye:
                        try:
                            dm = discord.Embed(
                                color=discord.Color.red(),
                                timestamp=datetime.now(timezone.utc),
                            )
                            dm.set_author(name="Öneriniz Değerlendirildi")
                            dm.description = (
                                "<:onerino:1478614338909769799>  Sunucumuza ilettiğiniz öneri yönetici ekibimiz tarafından incelendi ancak şu an için **uygulamaya alınmayacak.**\n\n"
                                f"<a:bildirim:1478390691334979645>  **Red Sebebi:**\n```{modal_self.sebep.value}```\n"
                                "<:warning1:1478525076373635102>  Farklı önerileriniz için her zaman başvurabilirsiniz. Vaktiniz için teşekkürler!"
                            )
                            dm.set_footer(text="Ascelia Bot • AWGames")
                            await uye.send(embed=dm)
                        except discord.Forbidden:
                            pass

        await interaction.response.send_modal(RedSebebiModal())

    @discord.ui.button(label="İnceleniyor", style=discord.ButtonStyle.secondary, custom_id="oneri_inceleme",
                       emoji="🔍")
    async def inceleme(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.yellow()
        embed.set_footer(text=f"İnceleniyor — {interaction.user.display_name} • Ascelia Bot • AWGames")
        button.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("🔍  İnceleniyor olarak işaretlendi.", ephemeral=True)

        uid = self._gonderen_id(embed)
        if uid:
            try:
                uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            except Exception:
                uye = None
            if uye:
                await self._dm_gonder(
                    uye,
                    "<:oneriinceleme:1478614169639977001>  Öneriniz İnceleniyor",
                    (
                        "<a:bildirim:1478390691334979645>  Sunucumuza ilettiğiniz öneri yönetici ekibimiz tarafından **inceleniyor.**\n\n"
                        "<:saat:1478567051378298931>  Sonuç hakkında en kısa sürede bilgilendirileceksiniz."
                    ),
                    discord.Color.yellow()
                )


# ══════════════════════════════════════════════════════════════════════════════
# VIEW — Şikayet inceleme butonları
# ══════════════════════════════════════════════════════════════════════════════

class SikayetIncelemeView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    def _gonderen_id(self, embed: discord.Embed) -> Optional[int]:
        if embed.description:
            m = re.search(r"ID:\*\* `(\d+)`", embed.description)
            if m:
                return int(m.group(1))
        return None

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Olumlu Sonuçlandı", style=discord.ButtonStyle.success, custom_id="sikayet_kabul",
                       emoji=discord.PartialEmoji(name="olumlutick", id=1478524954688356494, animated=True))
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Olumlu Sonuçlandı — {interaction.user.display_name} • Ascelia Bot • AWGames")
        self.disable_all_items()
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("<a:olumlutick:1478524954688356494>  Olumlu sonuçlandı olarak işaretlendi.", ephemeral=True)

        uid = self._gonderen_id(embed)
        if uid:
            try:
                uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            except Exception:
                uye = None
            if uye:
                try:
                    dm = discord.Embed(color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
                    dm.set_author(name="Şikayetiniz Olumlu Sonuçlandı")
                    dm.description = (
                        f"<:oneriiletildi:1478613938529763349>  Sunucumuza ilettiğiniz şikayet yönetici ekibimiz tarafından incelendi ve **olumlu sonuçlandı.**\n\n"
                        "<a:whitearrow:1478394670856933429>  Gerekli işlemler ekibimiz tarafından uygulanacaktır.\n"
                        f"<a:white:1478524885016907998>  Topluluğumuzu daha iyi bir yer yapmaya katkıda bulunduğunuz için teşekkür ederiz! <a:yellow:1478524892801667203>"
                    )
                    dm.set_footer(text="Ascelia Bot • AWGames")
                    await uye.send(embed=dm)
                except discord.Forbidden as e:
                    hata_kodu = getattr(e, 'code', 0)
                    if hata_kodu != 50007:
                        log.warning(f"DM Forbidden (kod={hata_kodu}) → {uye}: {e}")

    @discord.ui.button(label="Olumsuz Sonuçlandı", style=discord.ButtonStyle.danger, custom_id="sikayet_red",
                       emoji=discord.PartialEmoji(name="no", id=1478524993670479942, animated=True))
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = interaction.message.embeds[0]
        uid = self._gonderen_id(embed)
        view_ref = self
        msg_ref = interaction.message
        user_ref = interaction.user

        class OlumsuzModal(discord.ui.Modal, title="Olumsuz Sonuç Sebebi"):
            sebep = discord.ui.TextInput(
                label="Sebep",
                placeholder="Şikayetin neden olumsuz sonuçlandığını açıklayın...",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=500,
            )

            async def on_submit(modal_self, modal_interaction: discord.Interaction) -> None:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"Olumsuz Sonuçlandı — {user_ref.display_name} • Ascelia Bot • AWGames")
                embed.add_field(name="Sebep", value=f"```{modal_self.sebep.value}```", inline=False)
                view_ref.disable_all_items()
                await msg_ref.edit(embed=embed, view=view_ref)
                await modal_interaction.response.send_message("<a:no:1478524993670479942>  Olumsuz sonuçlandı olarak işaretlendi.", ephemeral=True)

                if uid:
                    try:
                        uye = modal_interaction.guild.get_member(uid) or await modal_interaction.guild.fetch_member(uid)
                    except Exception:
                        uye = None
                    if uye:
                        try:
                            dm = discord.Embed(color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
                            dm.set_author(name="Şikayetiniz Değerlendirildi")
                            dm.description = (
                                f"<:onerino:1478614338909769799>  Sunucumuza ilettiğiniz şikayet yönetici ekibimiz tarafından incelendi ancak **olumsuz sonuçlandı.**\n\n"
                                f"<:dot2:1478383869534404712>  **Sebep:**\n```{modal_self.sebep.value}```\n\n"
                                "──────────────────────────────\n"
                                "<a:genel:1478389856874004592>  **Doğru Bildirim Nasıl Yapılır?**\n\n"
                                "<a:bildirim:1478390691334979645>  Oyunun adı, oyuncuların adı, tarih, saat ve konuşmaların tamamı **net ve okunabilir** olmalıdır.\n"
                                "<:dot1:1478383822625181879>  Bu bilgileri eksiksiz tamamlayarak doğru bir talep oluşturabilirsin.\n"
                                "<a:noted:1478525003342286932>  Gerekli bilgileri tamamlayıp yeniden başvurabilirsiniz."
                            )
                            dm.set_footer(text="Ascelia Bot • AWGames")
                            await uye.send(embed=dm)
                        except discord.Forbidden as e:
                            hata_kodu = getattr(e, 'code', 0)
                            if hata_kodu != 50007:
                                log.warning(f"DM Forbidden (kod={hata_kodu}) → {uye}: {e}")

        await interaction.response.send_modal(OlumsuzModal())

    @discord.ui.button(label="İnceleniyor", style=discord.ButtonStyle.secondary, custom_id="sikayet_inceleme",
                       emoji="🔍")
    async def inceleme(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.yellow()
        embed.set_footer(text=f"İnceleniyor — {interaction.user.display_name} • Ascelia Bot • AWGames")
        button.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("🔍  İnceleniyor olarak işaretlendi.", ephemeral=True)

        uid = self._gonderen_id(embed)
        if uid:
            try:
                uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            except Exception:
                uye = None
            if uye:
                try:
                    dm = discord.Embed(color=discord.Color.yellow(), timestamp=datetime.now(timezone.utc))
                    dm.description = (
                        "🔍  Şikayetiniz yönetici ekibimiz tarafından **inceleniyor.**\n\n"
                        "Sonuç hakkında en kısa sürede bilgilendirileceksiniz."
                    )
                    dm.set_footer(text="Ascelia Bot • AWGames")
                    await uye.send(embed=dm)
                except discord.Forbidden as e:
                    hata_kodu = getattr(e, 'code', 0)
                    if hata_kodu != 50007:
                        log.warning(f"DM Forbidden (kod={hata_kodu}) → {uye}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MODAL — Öneri Formu
# ══════════════════════════════════════════════════════════════════════════════

class OneriFormu(discord.ui.Modal, title="Öneri Formu"):
    baslik = discord.ui.TextInput(
        label="Önerinizin Başlığı",
        placeholder="Kısa ve öz bir başlık belirtin...",
        required=True,
        max_length=100,
    )
    aciklama = discord.ui.TextInput(
        label="Önerinizi Detaylıca Açıklayın",
        placeholder="Neden bu öneride bulunuyorsunuz?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )
    katkisi = discord.ui.TextInput(
        label="Oyuncu Deneyimine Katkısı",
        placeholder="Bu öneri oyuncuları nasıl etkiler?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    ek_bilgi = discord.ui.TextInput(
        label="Eklemek İstediğiniz Başka Bir Şey?",
        placeholder="Varsa belirtin, yoksa 'yok' yazın...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )

    def __init__(self, guild: discord.Guild, uye: discord.Member, settings: Settings):
        super().__init__()
        self.guild = guild
        self.uye = uye
        self.settings = settings

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        # Kullanıcıya tamamlandı DM'i
        try:
            bitis = discord.Embed(color=0x2ECC71, timestamp=datetime.now(timezone.utc))
            bitis.set_author(name="Öneriniz İletildi!", icon_url=self.guild.icon.url if self.guild.icon else None)
            bitis.description = (
                "<:onerigonderildi:1478613995622629468>  Merhaba, öneriniz yönetim ekibine başarıyla iletildi. Önerinizi iş yoğunluğumuza göre değerlendireceğiz. Olumlu veya olumsuz tarafınıza dönüş sağlayacağız.\n\n"
                "<a:noted:1478525003342286932>  Oyuna katkı sağladığınız ve geri dönüş verdiğiniz için teşekkür ederiz! "
                "Sizin gibi aktif oyuncular topluluğumuzu daha iyi bir yer yapar. <a:yellow:1478524892801667203>"
            )
            bitis.set_footer(text="Ascelia Bot • AWGames")
            await self.uye.send(embed=bitis)
        except discord.Forbidden as e:
            hata_kodu = getattr(e, 'code', 0)
            if hata_kodu != 50007:
                log.warning(f"DM Forbidden (kod={hata_kodu}) → {self.uye}: {e}")

        # Admin kanalına gönder
        kanal = self.guild.get_channel(self.settings.oneri_kanal_id)
        if not kanal:
            try:
                kanal = await interaction.client.fetch_channel(self.settings.oneri_kanal_id)
            except Exception:
                kanal = None

        if kanal:
            embed = discord.Embed(color=0xC9A84C, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=f"Yeni Öneri — {self.uye.display_name}", icon_url=str(self.uye.display_avatar.url))
            embed.description = (
                f"<:oneri:1478614033392341143>  **Gönderen:** {self.uye.mention}\n"
                f"<a:whitearrow:1478394670856933429>  **Kullanıcı:** `{self.uye.name}`\n"
                f"<a:whitearrow:1478394670856933429>  **ID:** `{self.uye.id}`\n\n"
                "──────────────────────────────"
            )
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `01`  Başlık", value=f"```{self.baslik.value}```", inline=False)
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `02`  Açıklama", value=f"```{self.aciklama.value[:1020]}```", inline=False)
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `03`  Oyuncu Deneyimine Katkısı", value=f"```{self.katkisi.value[:1020]}```", inline=False)
            if self.ek_bilgi.value and self.ek_bilgi.value.lower() != "yok":
                embed.add_field(name="<a:whitearrow:1478394670856933429>  `04`  Ek Bilgi", value=f"```{self.ek_bilgi.value[:1020]}```", inline=False)
            embed.set_thumbnail(url=str(self.uye.display_avatar.url))
            embed.set_footer(text="Ascelia Bot • AWGames | Öneri Sistemi")
            await kanal.send(embed=embed, view=OneriIncelemeView())

        log.info(f"Öneri → {self.uye} ({self.uye.id})")


# ══════════════════════════════════════════════════════════════════════════════
# MODAL — Şikayet Formu
# ══════════════════════════════════════════════════════════════════════════════

class SikayetFormu(discord.ui.Modal, title="Şikayet Formu"):
    karakter_adi = discord.ui.TextInput(
        label="Şikayet Ettiğiniz Oyuncunun Karakter Adı",
        placeholder="Oyun içi karakter adını yazın...",
        required=True,
        max_length=100,
    )
    kendi_adi = discord.ui.TextInput(
        label="Kendi Oyun İçi Karakter Adınız",
        placeholder="Kendi karakter adınızı yazın...",
        required=True,
        max_length=100,
    )
    olay = discord.ui.TextInput(
        label="Olay Detayları (Tarih, Saat, Açıklama)",
        placeholder="Yaşanan olayı tarih ve saatle birlikte detaylıca açıklayın...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )
    kanitlar = discord.ui.TextInput(
        label="Kanıtlar (Görsel / Video URL)",
        placeholder="Kanıt bağlantılarını paylaşın, yoksa 'yok' yazın...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    def __init__(self, guild: discord.Guild, uye: discord.Member, settings: Settings):
        super().__init__()
        self.guild = guild
        self.uye = uye
        self.settings = settings

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        # Kullanıcıya tamamlandı DM'i
        try:
            bitis = discord.Embed(color=0x2ECC71, timestamp=datetime.now(timezone.utc))
            bitis.set_author(name="Şikayetiniz İletildi!", icon_url=self.guild.icon.url if self.guild.icon else None)
            bitis.description = (
                "<:oneribaslik:1478614033392341143>  Şikayetiniz yönetici ekibimize başarıyla iletildi!\n\n"
                "<:oneriinceleme:1478614169639977001>  İnceleme sürecinde gerekirse sizinle iletişime geçilecektir. Bildiriminiz için teşekkür ederiz."
            )
            bitis.set_footer(text="Ascelia Bot • AWGames")
            await self.uye.send(embed=bitis)
        except discord.Forbidden as e:
            hata_kodu = getattr(e, 'code', 0)
            if hata_kodu != 50007:
                log.warning(f"DM Forbidden (kod={hata_kodu}) → {self.uye}: {e}")

        # Admin kanalına gönder
        kanal = self.guild.get_channel(self.settings.sikayet_kanal_id)
        if not kanal:
            try:
                kanal = await interaction.client.fetch_channel(self.settings.sikayet_kanal_id)
            except Exception:
                kanal = None

        if kanal:
            embed = discord.Embed(color=0xE74C3C, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=f"Yeni Şikayet — {self.uye.display_name}", icon_url=str(self.uye.display_avatar.url))
            embed.description = (
                f"<:oneri:1478613741947064340>  **Şikayetçi:** {self.uye.mention}\n"
                f"<a:whitearrow:1478394670856933429>  **Kullanıcı:** `{self.uye.name}`\n"
                f"<a:whitearrow:1478394670856933429>  **ID:** `{self.uye.id}`\n\n"
                "──────────────────────────────"
            )
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `01`  Şikayet Edilen Karakter", value=f"```{self.karakter_adi.value}```", inline=False)
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `02`  Şikayetçi Karakter", value=f"```{self.kendi_adi.value}```", inline=False)
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `03`  Olay Detayları", value=f"```{self.olay.value[:1020]}```", inline=False)
            embed.add_field(name="<a:whitearrow:1478394670856933429>  `04`  Kanıtlar", value=f"```{self.kanitlar.value[:1020]}```", inline=False)
            embed.set_thumbnail(url=str(self.uye.display_avatar.url))
            embed.set_footer(text="Ascelia Bot • AWGames | Şikayet Sistemi")
            await kanal.send(embed=embed, view=SikayetIncelemeView())

        log.info(f"Şikayet → {self.uye} ({self.uye.id})")


# ══════════════════════════════════════════════════════════════════════════════
# COG
# ══════════════════════════════════════════════════════════════════════════════

class OneriSikayetCog(commands.Cog, name="Öneri Şikayet"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    @app_commands.command(name="öneri", description="Sunucu için öneri gönder")
    async def oneri(self, interaction: discord.Interaction) -> None:
        kalan = oneri_cooldown.kontrol(f"oneri:{interaction.user.id}", _ONERI_COOLDOWN_SURE)
        if kalan is not None:
            dakika = int(kalan // 60)
            saniye = int(kalan % 60)
            sure_str = f"{dakika}dk {saniye}sn" if dakika > 0 else f"{saniye}sn"
            await interaction.response.send_message(
                f"<a:no:1478524993670479942>  Öneri göndermek için **{sure_str}** bekle.",
                ephemeral=True,
            )
            return
        form = OneriFormu(interaction.guild, interaction.user, self.settings)
        await interaction.response.send_modal(form)

    @app_commands.command(name="şikayet", description="Oyuncu veya sunucu hakkında şikayet bildir")
    async def sikayet(self, interaction: discord.Interaction) -> None:
        kalan = sikayet_cooldown.kontrol(f"sikayet:{interaction.user.id}", _SIKAYET_COOLDOWN_SURE)
        if kalan is not None:
            dakika = int(kalan // 60)
            saniye = int(kalan % 60)
            sure_str = f"{dakika}dk {saniye}sn" if dakika > 0 else f"{saniye}sn"
            await interaction.response.send_message(
                f"<a:no:1478524993670479942>  Şikayet göndermek için **{sure_str}** bekle.",
                ephemeral=True,
            )
            return
        form = SikayetFormu(interaction.guild, interaction.user, self.settings)
        await interaction.response.send_modal(form)

    async def cog_load(self) -> None:
        self.bot.add_view(OneriIncelemeView())
        self.bot.add_view(SikayetIncelemeView())
        log.info("Öneri & Şikayet view'ları yüklendi")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OneriSikayetCog(bot))
