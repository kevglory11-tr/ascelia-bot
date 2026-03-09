# -*- coding: utf-8 -*-
"""
cogs/basvuru.py — Tam başvuru sistemi.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config.settings import Settings
from utils.cooldown import basvuru_cooldown
from utils.dm_queue import dm_queue

_BASVURU_COOLDOWN_SURE = 300.0  # 5 dakika

log = logging.getLogger("cog.basvuru")

BASVURU_ETIKETLER = {
    "moderator": ("<:tdm:1478576238623850606>", "Moderatör Başvurusu", 0x3498DB),
    "partner":   ("<a:basvuru:1478389708932255775>", "İçerik Üreticisi Başvurusu", 0x2ECC71),
}


class BasvuruDropdown(discord.ui.Select):
    def __init__(self) -> None:
        secenekler = [
            discord.SelectOption(
                label="Moderatör Başvurusu",
                value="moderator",
                description="Trial Discord Moderatör olmak istiyorum",
                emoji=discord.PartialEmoji(name="tdm", id=1478576238623850606),
            ),
            discord.SelectOption(
                label="İçerik Üreticisi Başvurusu",
                value="partner",
                description="İçerik üreticisi olarak başvurmak istiyorum",
                emoji=discord.PartialEmoji(name="basvuru", id=1478389708932255775, animated=True),
            ),
        ]
        super().__init__(
            placeholder="📋  Başvuru türünü seç...",
            min_values=1,
            max_values=1,
            options=secenekler,
            custom_id="basvuru_dropdown",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # Cooldown kontrolü — aynı tür başvuru için 5 dakika
        anahtar = f"basvuru:{interaction.user.id}:{self.values[0]}"
        kalan = basvuru_cooldown.kontrol(anahtar, _BASVURU_COOLDOWN_SURE)
        if kalan is not None:
            dakika = int(kalan // 60)
            saniye = int(kalan % 60)
            sure_str = f"{dakika}dk {saniye}sn" if dakika > 0 else f"{saniye}sn"
            await interaction.response.send_message(
                f"<a:no:1478524993670479942>  Bu başvuru türü için **{sure_str}** beklemelisin.",
                ephemeral=True,
            )
            return
        log.info(f"Başvuru dropdown → {self.values[0]} | {interaction.user}")
        await interaction.response.defer(ephemeral=True)
        try:
            await basvuru_baslat(interaction, self.values[0])
        except Exception as e:
            log.error(f"Dropdown callback hata → {type(e).__name__}: {e}", exc_info=True)


class BasvuruPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(BasvuruDropdown())


class IncelemeView(discord.ui.View):
    def __init__(self, basvuran_id: int, tur: str) -> None:
        super().__init__(timeout=None)
        self.basvuran_id = basvuran_id
        self.tur = tur

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success, custom_id="basvuru_kabul",
                       emoji=discord.PartialEmoji(name="olumlutick", id=1478524954688356494, animated=True))
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._karar_ver(interaction, kabul_edildi=True, sebep=None)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, custom_id="basvuru_red",
                       emoji=discord.PartialEmoji(name="no", id=1478524993670479942, animated=True))
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view_ref = self
        msg_ref = interaction.message
        basvuran_id = self.basvuran_id
        tur = self.tur

        class RedSebebiModal(discord.ui.Modal, title="Red Sebebi"):
            sebep = discord.ui.TextInput(
                label="Red Sebebi",
                placeholder="Başvuruyu neden reddediyorsunuz?",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=500,
            )

            async def on_submit(modal_self, modal_inter: discord.Interaction) -> None:
                await modal_inter.response.defer()
                await view_ref._karar_ver(modal_inter, kabul_edildi=False, sebep=modal_self.sebep.value, msg=msg_ref)

        await interaction.response.send_modal(RedSebebiModal())

    async def _karar_ver(self, interaction: discord.Interaction, kabul_edildi: bool, sebep: Optional[str], msg=None) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True

        emoji, baslik, renk = BASVURU_ETIKETLER.get(self.tur, ("📝", "Başvuru", 0xC9A84C))
        karar_renk = 0x2ECC71 if kabul_edildi else 0xE74C3C

        guncellenmis = discord.Embed(color=karar_renk, timestamp=datetime.now(timezone.utc))
        guncellenmis.set_author(name=f"{baslik} — {'KABUL EDİLDİ' if kabul_edildi else 'REDDEDİLDİ'}")
        guncellenmis.description = f"Karar: {interaction.user.mention} tarafından verildi."
        if sebep:
            guncellenmis.add_field(name="Red Sebebi", value=f"```{sebep}```", inline=False)
        guncellenmis.set_footer(text="Ascelia Bot • AWGames")

        hedef_msg = msg or interaction.message
        if hedef_msg:
            try:
                await hedef_msg.edit(embed=guncellenmis, view=self)
            except Exception:
                pass
        else:
            try:
                await interaction.edit_original_response(embed=guncellenmis, view=self)
            except Exception:
                pass

        basvuran = interaction.guild.get_member(self.basvuran_id)
        if basvuran:
            try:
                if kabul_edildi:
                    dm_emb = discord.Embed(color=0x2ECC71, timestamp=datetime.now(timezone.utc))
                    dm_emb.set_author(
                        name=f"{baslik} — Olumlu Sonuçlandı!",
                        icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                    )
                    dm_emb.description = (
                        f"Merhaba, {basvuran.mention}!\n\n"
                        f"<:basvuruonay:1478613852215050350>  **{interaction.guild.name}** sunucusundaki başvurunuz olumlu sonuçlandı.\n\n"
                        f"<a:whitearrow:1478394670856933429>  Yetkililer ile iletişime geçerek detaylı bilgi alabilirsiniz.\n\n"
                        f"<:warning1:1478525076373635102>  En yakın zamanda yetkililerle iletişime geçmeyi ihmal etmeyin."
                    )
                else:
                    dm_emb = discord.Embed(color=0xE74C3C, timestamp=datetime.now(timezone.utc))
                    dm_emb.set_author(
                        name=f"{baslik} — Olumsuz Sonuçlandı",
                        icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                    )
                    dm_emb.description = (
                        f"Merhaba, {basvuran.mention}!\n\n"
                        f"<:basvuruolumsuz:1478614401006178376>  **{interaction.guild.name}** sunucusundaki başvurunuz olumsuz sonuçlandı.\n\n"
                        f"<:dot2:1478383869534404712>  **Red Sebebi:**\n```{sebep}```\n"
                        f"<a:noted:1478525003342286932>  Gelecekte tekrar alımlar açıldığında başvuru yapabilirsiniz. Vaktinizi ayırdığınız ve bizimle iletişime geçtiğiniz için teşekkür ederiz."
                    )
                if interaction.guild.icon:
                    dm_emb.set_thumbnail(url=interaction.guild.icon.url)
                dm_emb.set_footer(text="Ascelia Bot • AWGames")
                await basvuran.send(embed=dm_emb)
            except discord.Forbidden:
                pass


MODERATOR_KURALLAR = (
    "Merhaba! Öncelikle ekibimize başvuracağın için çok mutlu olduğumuzu bilmeni isterim. "
    "Eğer daha önce bir sunucuda moderatörlük yaptıysan tüm bildiklerini unutmalısın; "
    "çünkü burada yaşayacağın deneyimler ilk olacak! "
    "Seni daha fazla yormadan beklentilerimizi ileteyim ve formumuza geçelim.\n\n"
    "<a:whitearrow:1478394670856933429> Sinirli veya argo/küfürlü bir üslup kesinlikle kabul edilmez. Oyuncularla iletişim kurarken bir oyuncu gibi değil, yetkili kimliğinin bilincinde olarak konuşmalısın.\n"
    "<a:whitearrow:1478394670856933429> Oyunculara yalnızca oyun içi konularda destek vereceksin. Teknik veya oyun dışı sorunlar için ilgili kişileri ticket sistemine yönlendirebilirsin.\n"
    "<a:whitearrow:1478394670856933429> Belirlenen görev saatlerinde aktif olman beklenmektedir. Görev saatlerinde aktif olamayacağın durumlarda önceden mazeret bildirmen zorunludur.\n"
    "<a:whitearrow:1478394670856933429> Günlük olarak en az **4 saat** Discord'da aktif olabilecek zamana sahip olmalısın.\n"
    "<a:whitearrow:1478394670856933429> Oyunculara doğru ve etkili destek verebilmek için oyunumuz hakkında yeterli bilgiye sahip olman gerekmektedir.\n"
    "<a:whitearrow:1478394670856933429> Destek yalnızca oyun sohbet kanalı üzerinden yazılı olarak verilecektir. Sesli destek veya özel mesaj yoluyla destek sağlanmamaktadır.\n"
    "<a:whitearrow:1478394670856933429> Ticket'lara bakma sorumluluğun bulunmamaktadır.\n"
    "<a:whitearrow:1478394670856933429> Yönetim ekibine ve üst yetkililere karşı saygılı olmalı, alınan kararları benimseyerek ekip ruhuna uygun hareket etmelisin.\n"
    "<a:whitearrow:1478394670856933429> Aktif bir lonca üyesi olmamalısın.\n"
    "<a:whitearrow:1478394670856933429> Başvurunun onaylanması halinde, görev süreci için yeni bir Discord hesabı açmayı kabul etmelisin.\n\n"
    "Tüm bunları kabul edersen ekibimizin bir parçası olacak ve emeğinin karşılığı olarak oyun içi **MP** ile ödüllendirileceksin.\n"
    "*(1 EP = 1 MP — nesne market ürünlerinin ticareti ve pazarlanması yasaktır, yalnızca kendin kullanabilirsin.)*"
)


class ModeratorOnayView(discord.ui.View):
    def __init__(self, guild: discord.Guild, uye: discord.Member, settings: Settings):
        super().__init__(timeout=300)
        self.onaylandi = False
        self.guild = guild
        self.uye = uye
        self.settings = settings

    @discord.ui.button(
        label="Kabul Ediyorum, Devam Et",
        style=discord.ButtonStyle.secondary,
        custom_id="mod_kabul",
        emoji=discord.PartialEmoji(name="olumlutick", id=1478524954688356494, animated=True),
    )
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.onaylandi = True
        self.stop()
        form = ModeratorBasvuruFormu(self.guild, self.uye, self.settings)
        await interaction.response.send_modal(form)
        try:
            await interaction.message.edit(
                embed=discord.Embed(
                    description="<a:olumlutick:1478524954688356494>  Kuralları kabul ettin! Form açıldı, doldur ve gönder.",
                    color=0x2ECC71,
                ),
                view=None,
            )
        except Exception:
            pass

    @discord.ui.button(
        label="Vazgeçiyorum",
        style=discord.ButtonStyle.secondary,
        custom_id="mod_red",
        emoji=discord.PartialEmoji(name="no", id=1478524993670479942, animated=True),
    )
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.onaylandi = False
        self.stop()
        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(
                description="<a:no:1478524993670479942>  Başvurudan vazgeçildi.",
                color=0xE74C3C,
            ),
            view=None,
        )


class ModeratorBasvuruFormu(discord.ui.Modal, title="Moderatör Başvuru Formu"):
    discord_adi = discord.ui.TextInput(
        label="Discord Adınız",
        placeholder="Örn: kullaniciadi",
        required=True,
        max_length=100,
    )
    yas_ve_bilgi = discord.ui.TextInput(
        label="Kendinizden bahsedin (Yaş, iş durumunuz vb.)",
        placeholder="Kendinizden kısaca bahsedin...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    aktif_saatler = discord.ui.TextInput(
        label="Aktif olabileceğiniz saat dilimleri",
        placeholder="Örn: 15:00 – 22:00",
        required=True,
        max_length=100,
    )
    deneyim = discord.ui.TextInput(
        label="Daha önce moderatörlük yaptınız mı?",
        placeholder="Hangi platformlardaydı, neden ayrıldınız?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    neden_sen = discord.ui.TextInput(
        label="Sizi neden tercih etmeliyiz?",
        placeholder="Sizi diğer adaylardan ayıran özellikleriniz nelerdir?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    def __init__(self, guild: discord.Guild, uye: discord.Member, settings: Settings):
        super().__init__()
        self.guild = guild
        self.uye = uye
        self.settings = settings
        self.tamamlandi = False

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.tamamlandi = True
        await interaction.response.defer(ephemeral=True)

        # İnceleme kanalına gönder
        # Modal DM'den açıldığında interaction.guild None olur, self.guild kullan
        guild = self.guild
        inceleme_kanal_id = self.settings.basvuru_inceleme_kanallar.get("moderator", 0)
        # get_channel cache'e bakar, fetch_channel API'ye sorar — cache miss durumunda daha güvenli
        inceleme_kanal = guild.get_channel(inceleme_kanal_id)
        if not inceleme_kanal:
            try:
                inceleme_kanal = await interaction.client.fetch_channel(inceleme_kanal_id)
            except Exception as e:
                log.error(f"Moderatör inceleme kanalı fetch hatası: {inceleme_kanal_id} → {e}")
                inceleme_kanal = None
        log.info(f"Moderatör başvuru → guild={guild.id} kanal_id={inceleme_kanal_id} kanal={inceleme_kanal}")

        renk = 0x3498DB
        inceleme_emb = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
        inceleme_emb.set_author(name="Yeni Moderatör Başvurusu", icon_url=str(self.uye.display_avatar.url))
        inceleme_emb.description = (
            f"<:tdm:1478576238623850606>  **Başvuran:** {self.uye.mention}\n"
            f"<a:whitearrow:1478394670856933429>  **Kullanıcı:** `{self.uye.name}`\n"
            f"<a:whitearrow:1478394670856933429>  **ID:** `{self.uye.id}`\n"
            f"<a:whitearrow:1478394670856933429>  **Hesap Yaşı:** <t:{int(self.uye.created_at.timestamp())}:R>\n\n"
            "──────────────────────────────"
        )
        cevaplar = [
            ("Discord Adı", self.discord_adi.value),
            ("Kendinizden Bahsedin (Yaş, İş Durumu vb.)", self.yas_ve_bilgi.value),
            ("Aktif Saatler", self.aktif_saatler.value),
            ("Moderatörlük Deneyimi", self.deneyim.value),
            ("Neden Tercih Edilmeli?", self.neden_sen.value),
        ]
        for i, (soru, cevap) in enumerate(cevaplar, 1):
            inceleme_emb.add_field(
                name=f"<a:whitearrow:1478394670856933429>  `{i:02d}`  {soru}",
                value=f"```{cevap[:1020]}```",
                inline=False,
            )
        inceleme_emb.set_thumbnail(url=str(self.uye.display_avatar.url))
        inceleme_emb.set_footer(text="Ascelia Bot • AWGames | Kabul et veya reddet")

        if inceleme_kanal:
            await inceleme_kanal.send(embed=inceleme_emb, view=IncelemeView(self.uye.id, "moderator"))
        else:
            log.warning(f"Moderatör inceleme kanalı bulunamadı: {inceleme_kanal_id}")

        # Başvurana DM
        try:
            bitis_emb = discord.Embed(color=0x2ECC71, timestamp=datetime.now(timezone.utc))
            bitis_emb.set_author(name="Başvurunuz Tamamlandı!", icon_url=guild.icon.url if guild.icon else None)
            bitis_emb.description = (
                "<:basvuruonay:1478613852215050350>  Moderatör başvurunuz ekibimize iletildi!\n\n"
                "<:oneriinceleme:1478614169639977001>  Başvurunuz incelendikten sonra karar DM üzerinden bildirilecek."
            )
            bitis_emb.set_footer(text="Ascelia Bot • AWGames")
            await self.uye.send(embed=bitis_emb)
        except discord.Forbidden:
            pass


class PartnerBasvuruFormu(discord.ui.Modal, title="İçerik Üreticisi Başvuru Formu"):
    kanal_adi = discord.ui.TextInput(
        label="Kanal / Hesap Adınız",
        placeholder="Kanal veya hesap adınızı yazın...",
        required=True,
        max_length=100,
    )
    platform = discord.ui.TextInput(
        label="Platform(lar)",
        placeholder="Kick, Twitch, YouTube, TikTok...",
        required=True,
        max_length=100,
    )
    istatistik = discord.ui.TextInput(
        label="Kanal İstatistikleri (Bağlantı veya açıklama)",
        placeholder="İstatistik sayfası linki veya takipçi/izleyici bilgisi...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    beklenti = discord.ui.TextInput(
        label="Çalışma Beklentiniz",
        placeholder="Ücretli / Ücretsiz / EP karşılığında...",
        required=True,
        max_length=200,
    )
    neden = discord.ui.TextInput(
        label="Neden bizi tercih ediyorsunuz?",
        placeholder="Kısaca açıklayın...",
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

        guild = self.guild
        inceleme_kanal_id = self.settings.basvuru_inceleme_kanallar.get("partner", 0)
        inceleme_kanal = guild.get_channel(inceleme_kanal_id)
        if not inceleme_kanal:
            try:
                inceleme_kanal = await interaction.client.fetch_channel(inceleme_kanal_id)
            except Exception as e:
                log.error(f"Partner inceleme kanalı fetch hatası: {inceleme_kanal_id} → {e}")
                inceleme_kanal = None

        renk = 0x2ECC71
        inceleme_emb = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
        inceleme_emb.set_author(name="Yeni İçerik Üreticisi Başvurusu", icon_url=str(self.uye.display_avatar.url))
        inceleme_emb.description = (
            f"<a:basvuru:1478389708932255775>  **Başvuran:** {self.uye.mention}\n"
            f"<a:whitearrow:1478394670856933429>  **Kullanıcı:** `{self.uye.name}`\n"
            f"<a:whitearrow:1478394670856933429>  **ID:** `{self.uye.id}`\n"
            f"<a:whitearrow:1478394670856933429>  **Hesap Yaşı:** <t:{int(self.uye.created_at.timestamp())}:R>\n\n"
            "──────────────────────────────"
        )
        cevaplar = [
            ("Kanal / Hesap Adı", self.kanal_adi.value),
            ("Platform(lar)", self.platform.value),
            ("Kanal İstatistikleri", self.istatistik.value),
            ("Çalışma Beklentisi", self.beklenti.value),
            ("Neden Bizi Tercih Ediyor?", self.neden.value),
        ]
        for i, (soru, cevap) in enumerate(cevaplar, 1):
            inceleme_emb.add_field(
                name=f"<a:whitearrow:1478394670856933429>  `{i:02d}`  {soru}",
                value=f"```{cevap[:1020]}```",
                inline=False,
            )
        inceleme_emb.set_thumbnail(url=str(self.uye.display_avatar.url))
        inceleme_emb.set_footer(text="Ascelia Bot • AWGames | Kabul et veya reddet")

        if inceleme_kanal:
            await inceleme_kanal.send(embed=inceleme_emb, view=IncelemeView(self.uye.id, "partner"))
        else:
            log.warning(f"Partner inceleme kanalı bulunamadı: {inceleme_kanal_id}")

        # Başvurana DM
        try:
            bitis_emb = discord.Embed(color=0x2ECC71, timestamp=datetime.now(timezone.utc))
            bitis_emb.set_author(
                name="Başvurunuz Tamamlandı!",
                icon_url=guild.icon.url if guild.icon else None,
            )
            bitis_emb.description = (
                "<:basvuruonay:1478613852215050350>  İçerik üreticisi başvurunuz ekibimize iletildi!\n\n"
                "<:oneriinceleme:1478614169639977001>  Başvurunuz incelendikten sonra karar DM üzerinden bildirilecek."
            )
            bitis_emb.set_footer(text="Ascelia Bot • AWGames")
            await self.uye.send(embed=bitis_emb)
        except discord.Forbidden:
            pass


    def __init__(self, guild: discord.Guild, uye: discord.Member, settings: Settings):
        super().__init__(timeout=300)
        self.onaylandi = False
        self.guild = guild
        self.uye = uye
        self.settings = settings

    @discord.ui.button(
        label="Kabul Ediyorum, Devam Et",
        style=discord.ButtonStyle.secondary,
        custom_id="mod_kabul",
        emoji=discord.PartialEmoji(name="olumlutick", id=1478524954688356494, animated=True),
    )
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.onaylandi = True
        self.stop()
        form = ModeratorBasvuruFormu(self.guild, self.uye, self.settings)
        await interaction.response.send_modal(form)
        # Kurallar mesajını güncelle
        try:
            await interaction.message.edit(
                embed=discord.Embed(
                    description="<a:olumlutick:1478524954688356494>  Kuralları kabul ettin! Form açıldı, doldur ve gönder.",
                    color=0x2ECC71,
                ),
                view=None,
            )
        except Exception:
            pass

    @discord.ui.button(
        label="Vazgeçiyorum",
        style=discord.ButtonStyle.secondary,
        custom_id="mod_red",
        emoji=discord.PartialEmoji(name="no", id=1478524993670479942, animated=True),
    )
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.onaylandi = False
        self.stop()
        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(
                description="<a:no:1478524993670479942>  Başvurudan vazgeçildi.",
                color=0xE74C3C,
            ),
            view=None,
        )


async def basvuru_baslat(interaction: discord.Interaction, tur: str) -> None:
    settings = Settings()
    sorular = settings.basvuru_sorulari.get(tur, [])
    emoji, baslik, renk = BASVURU_ETIKETLER.get(tur, ("📝", "Başvuru", 0xC9A84C))
    guild = interaction.guild
    uye = interaction.user

    try:
        if tur == "moderator":
            kural_embed = discord.Embed(
                title="<:tdm:1478576238623850606>  Moderatör Başvurusu — Kurallar & Beklentiler",
                description=MODERATOR_KURALLAR,
                color=renk,
                timestamp=datetime.now(timezone.utc),
            )
            if guild.icon:
                kural_embed.set_thumbnail(url=guild.icon.url)
            kural_embed.set_footer(text="Ascelia Bot • AWGames | Kuralları okuyup kabul etmen gerekiyor")
            onay_view = ModeratorOnayView(guild, uye, settings)
            await uye.send(embed=kural_embed, view=onay_view)

            bilgi_embed = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
            bilgi_embed.set_author(
                name="Moderatör Başvurusu",
                icon_url=guild.icon.url if guild.icon else None,
            )
            bilgi_embed.description = (
                "<a:olumlutick:1478524954688356494>  **Kurallar ve başvuru formu özel mesaj olarak gönderildi.**\n\n"
                "<a:whitearrow:1478394670856933429>  Kuralları dikkatlice oku\n"
                "<a:whitearrow:1478394670856933429>  Kuralları kabul edersen başvuru formu açılacak\n"
                "<a:whitearrow:1478394670856933429>  Formu doldurup gönder, ekibimiz seni inceleyecek\n\n"
                "<:warning1:1478525076373635102>  DM kutunu kontrol etmeyi unutma!"
            )
            bilgi_embed.set_footer(text="Ascelia Bot • AWGames")
            await interaction.followup.send(embed=bilgi_embed, ephemeral=True)
            return
        else:
            giris_embed = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
            giris_embed.set_author(
                name="İçerik Üreticisi Başvurusu",
                icon_url=guild.icon.url if guild.icon else None,
            )
            giris_embed.description = (
                "<a:basvuru:1478389708932255775>  **AWGames İçerik Üreticisi Programına Hoş Geldiniz!**\n\n"
                "<a:whitearrow:1478394670856933429>  Başvuru formunuz açılıyor, lütfen tüm alanları eksiksiz doldurun\n"
                "<a:whitearrow:1478394670856933429>  Bilgilerinizi doğru ve güncel şekilde paylaşın\n"
                "<a:whitearrow:1478394670856933429>  Başvurunuz incelendikten sonra DM üzerinden bildirim alacaksınız\n\n"
                "<:kick:1478389759373217893>  **Kick**  •  <:twitch:1478389781577597020>  **Twitch**  •  <:tiktok:1478389808140259338>  **TikTok**  •  <:youtube:1478613337133809845>  **YouTube**\n\n"
                "<:warning1:1478525076373635102>  Anlaşma sağlanabilir platformlar yukarıda belirtilmiştir."
            )
            if guild.icon:
                giris_embed.set_thumbnail(url=guild.icon.url)
            giris_embed.set_footer(text="Ascelia Bot • AWGames")
            await uye.send(embed=giris_embed)

            # Partner modal formunu açmak için ephemeral buton gönder
            class PartnerFormAcView(discord.ui.View):
                def __init__(self_inner):
                    super().__init__(timeout=300)

                @discord.ui.button(
                    label="Başvuru Formunu Doldur",
                    style=discord.ButtonStyle.secondary,
                    emoji=discord.PartialEmoji(name="basvuru", id=1478389708932255775, animated=True),
                )
                async def form_ac(self_inner, inter: discord.Interaction, button: discord.ui.Button) -> None:
                    self_inner.stop()
                    form = PartnerBasvuruFormu(guild, uye, settings)
                    await inter.response.send_modal(form)
                    try:
                        await inter.message.edit(
                            embed=discord.Embed(
                                description="<a:olumlutick:1478524954688356494>  Form açıldı, doldur ve gönder.",
                                color=0x2ECC71,
                            ),
                            view=None,
                        )
                    except Exception:
                        pass

            await uye.send(view=PartnerFormAcView())

            bilgi_embed = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
            bilgi_embed.set_author(
                name="İçerik Üreticisi Başvurusu",
                icon_url=guild.icon.url if guild.icon else None,
            )
            bilgi_embed.description = (
                "<a:olumlutick:1478524954688356494>  **Başvuru formu özel mesaj olarak gönderildi.**\n\n"
                "<a:whitearrow:1478394670856933429>  DM kutunuzu açın ve formu eksiksiz doldurun\n"
                "<a:whitearrow:1478394670856933429>  Bilgilerinizi doğru ve güncel şekilde paylaşın\n"
                "<a:whitearrow:1478394670856933429>  Başvurunuz incelendikten sonra DM üzerinden bildirim alacaksınız\n\n"
                "<:warning1:1478525076373635102>  DM kutunuzu kontrol etmeyi unutmayın!"
            )
            bilgi_embed.set_footer(text="Ascelia Bot • AWGames")
            await interaction.followup.send(embed=bilgi_embed, ephemeral=True)
            return

    except (discord.Forbidden, discord.HTTPException) as e:
        hata_kodu = getattr(e, 'code', 0)
        log.warning(f"DM gönderilemedi → {uye} ({uye.id}) | kod={hata_kodu} | {type(e).__name__}: {e}")

        if hata_kodu == 50007:
            # Gerçekten DM kapalı
            await interaction.followup.send(
                "<a:no:1478524993670479942>  DM'lerin kapalı!\n\n"
                "> Discord Ayarları → Gizlilik & Güvenlik → **Sunucu üyelerinden gelen doğrudan mesajlara izin ver** seçeneğini aç.\n"
                "> Ayrıca sunucuya sağ tıkla → Gizlilik Ayarları → **Direkt Mesajlar** seçeneğinin açık olduğunu kontrol et.",
                ephemeral=True
            )
        elif hata_kodu == 40003:
            # Rate limit — biraz bekle, tekrar dene
            log.warning(f"DM rate limit (40003) → {uye} ({uye.id}), 8sn bekleniyor")
            await asyncio.sleep(8)
            try:
                if tur == "moderator":
                    await uye.send(embed=kural_embed, view=onay_view)
                else:
                    await uye.send(embed=giris_embed)
                    await uye.send(view=PartnerFormAcView())
                await interaction.followup.send(embed=bilgi_embed, ephemeral=True)
                return
            except Exception:
                pass
            await interaction.followup.send(
                "<a:no:1478524993670479942>  Sunucu şu an yoğun, birkaç dakika bekleyip tekrar dene.",
                ephemeral=True
            )
        else:
            # Bilinmeyen hata — bot geçici kısıtlı olabilir
            await interaction.followup.send(
                "<a:no:1478524993670479942>  DM gönderilemedi. Discord tarafında geçici bir kısıtlama olabilir.\n"
                "Birkaç dakika bekleyip tekrar dene. Sorun devam ederse yöneticilere bildir.",
                ephemeral=True
            )
        return
    except Exception as e:
        log.error(f"basvuru_baslat hata → tur={tur} uye={uye} → {type(e).__name__}: {e}", exc_info=True)
        try:
            await interaction.followup.send(
                "<a:no:1478524993670479942>  Bir hata oluştu, lütfen tekrar dene.",
                ephemeral=True
            )
        except Exception:
            pass
        return

    cevaplar = []
    dm_kanal = uye.dm_channel or await uye.create_dm()

    def kontrol(m: discord.Message) -> bool:
        return m.author.id == uye.id and m.channel.id == dm_kanal.id

    for i, soru in enumerate(sorular, 1):
        temiz_soru = soru.replace("<a:whitearrow:1478394670856933429> ", "")
        soru_embed = discord.Embed(
            description=f"**`Soru {i}/{len(sorular)}`**\n\n<a:whitearrow:1478394670856933429>  {temiz_soru}",
            color=renk,
        )
        soru_embed.set_footer(text="'iptal' yazarak formu iptal edebilirsin • Ascelia Bot")
        await dm_kanal.send(embed=soru_embed)

        try:
            mesaj = await interaction.client.wait_for("message", check=kontrol, timeout=300)
        except asyncio.TimeoutError:
            await dm_kanal.send(embed=discord.Embed(
                description="<a:no:1478524993670479942>  Süre doldu! Başvurunuz iptal edildi.",
                color=0xE74C3C
            ))
            return

        if mesaj.content.lower() == "iptal":
            await dm_kanal.send(embed=discord.Embed(
                description="<a:no:1478524993670479942>  Başvurunuz iptal edildi. İstediğinizde tekrar başvurabilirsiniz.",
                color=0xE74C3C
            ))
            return

        cevaplar.append((temiz_soru, mesaj.content))

    bitis_emb = discord.Embed(color=0x2ECC71, timestamp=datetime.now(timezone.utc))
    bitis_emb.set_author(name="Başvurunuz Tamamlandı!", icon_url=guild.icon.url if guild.icon else None)
    bitis_emb.description = (
        "<a:olumlutick:1478524954688356494>  Tüm soruları yanıtladın!\n\n"
        "Başvurunuz incelemeye alındı. Karar DM üzerinden bildirilecek. <a:bildirim:1478390691334979645>"
    )
    bitis_emb.set_footer(text="Ascelia Bot • AWGames")
    await dm_kanal.send(embed=bitis_emb)

    inceleme_kanal_id = settings.basvuru_inceleme_kanallar.get(tur, 0)
    inceleme_kanal = guild.get_channel(inceleme_kanal_id)
    if not inceleme_kanal:
        log.warning(f"İnceleme kanalı bulunamadı: {tur}")
        return

    inceleme_emb = discord.Embed(color=renk, timestamp=datetime.now(timezone.utc))
    inceleme_emb.set_author(name=f"Yeni {baslik}", icon_url=str(uye.display_avatar.url))
    inceleme_emb.description = (
        f"<:tdm:1478576238623850606>  **Başvuran:** {uye.mention}\n"
        f"<a:whitearrow:1478394670856933429>  **Kullanıcı:** `{uye.name}`\n"
        f"<a:whitearrow:1478394670856933429>  **ID:** `{uye.id}`\n"
        f"<a:whitearrow:1478394670856933429>  **Hesap Yaşı:** <t:{int(uye.created_at.timestamp())}:R>\n\n"
        "──────────────────────────────"
    )
    for i, (soru, cevap) in enumerate(cevaplar, 1):
        deger = cevap[:1020] + "..." if len(cevap) > 1020 else cevap
        inceleme_emb.add_field(
            name=f"<a:whitearrow:1478394670856933429>  `{i:02d}`  {soru}",
            value=f"```{deger}```",
            inline=False,
        )
    inceleme_emb.set_thumbnail(url=str(uye.display_avatar.url))
    inceleme_emb.set_footer(text="Ascelia Bot • AWGames | Kabul et veya reddet")

    await inceleme_kanal.send(embed=inceleme_emb, view=IncelemeView(uye.id, tur))
    log.info(f"Yeni başvuru -> {tur} | {uye} | {len(cevaplar)} cevap")


class BasvuruCog(commands.Cog, name="Başvuru"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()

    @app_commands.command(name="başvuru", description="Moderatör veya İçerik Üreticisi başvurusu yap")
    async def basvuru(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="<a:ticket1:1478391380635287725>  AWGames Başvuru",
            description=(
                "Oyunlarımızda Trial Discord Moderatör başvurusu ya da İçerik Üreticisi "
                "başvurusunda bulunmak istiyorsanız aşağıdaki seçeneklerden size uygun olanı seçebilirsiniz.\n\n"
                "<:tdm:1478576238623850606> **Moderatör Başvurusu** — Trial Discord Moderatör olmak istiyorum\n"
                "<a:basvuru:1478389708932255775> **İçerik Üreticisi Başvurusu** — İçerik üreticisi olarak başvurmak istiyorum\n\n"
                "<:warning1:1478525076373635102>  DM'lerin açık olduğundan emin ol!"
            ),
            color=self.settings.renkler["altin"],
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.response.send_message(embed=embed, view=BasvuruPanelView(), ephemeral=True)

    @app_commands.command(name="başvuru-panel-gönder", description="[ADMIN] Başvuru panelini kanala gönder (kalıcı)")
    async def basvuru_panel_gonder(self, interaction: discord.Interaction) -> None:
        from utils.permissions import is_admin, yetki_yok_mesaji
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return

        await interaction.response.defer(ephemeral=True)

        async for msg in interaction.channel.history(limit=50):
            if msg.author == interaction.guild.me and msg.components:
                for row in msg.components:
                    for item in row.children:
                        if hasattr(item, "custom_id") and item.custom_id == "basvuru_dropdown":
                            await interaction.followup.send(
                                "<a:no:1478524993670479942>  Bu kanalda zaten aktif bir panel bulunmaktadır. "
                                "Eğer işlem yapmak istiyorsan önceki paneli silmen yeterli.",
                                ephemeral=True
                            )
                            return

        embed = discord.Embed(
            title="<a:ticket1:1478391380635287725>  AWGames Başvuru",
            description=(
                "Oyunlarımızda Trial Discord Moderatör başvurusu ya da İçerik Üreticisi "
                "başvurusunda bulunmak istiyorsanız aşağıdaki seçeneklerden size uygun olanı seçebilirsiniz.\n\n"
                "<:tdm:1478576238623850606> **Moderatör Başvurusu** — Trial Discord Moderatör olmak istiyorum\n"
                "<a:basvuru:1478389708932255775> **İçerik Üreticisi Başvurusu** — İçerik üreticisi olarak başvurmak istiyorum\n\n"
                "<:warning1:1478525076373635102>  **Dikkat:** DM'lerin kapalıysa başvuru formu sana ulaşamaz!"
            ),
            color=self.settings.renkler["altin"],
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.channel.send(embed=embed, view=BasvuruPanelView())
        await interaction.followup.send(
            "<a:olumlutick:1478524954688356494>  Başvuru paneli gönderildi.",
            ephemeral=True
        )

    async def cog_load(self) -> None:
        self.bot.add_view(BasvuruPanelView())
        log.info("Başvuru view'ları yüklendi")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BasvuruCog(bot))
