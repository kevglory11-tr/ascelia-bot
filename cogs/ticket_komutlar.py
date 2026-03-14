"""
cogs/ticket_komutlar.py — Ticket içi destek ekibi komutları
Komutlar yalnızca TICKET_SUPPORT_ROL_IDLERI env var'ında tanımlı role sahip kişiler tarafından kullanılabilir.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from config.settings import Settings

log = logging.getLogger("cog.ticket_komutlar")


def destek_ekibi_mi(interaction: discord.Interaction, settings: Settings) -> bool:
    """Kullanıcının Railway'de tanımlı destek rolüne sahip olup olmadığını kontrol et."""
    return any(r.id in settings.ticket_support_rol_idleri for r in interaction.user.roles)


class TicketKomutlar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = Settings()

    # ─────────────────────────────────────────────────────────────
    # /email-değişim
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(
        name="email-değişim",
        description="E-Mail değişikliği için gerekli bilgi formunu gönderir."
    )
    async def email_degisim(self, interaction: discord.Interaction):
        if not destek_ekibi_mi(interaction, self.settings):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="📨  E-Mail Değişikliği", color=0x2F3136)
        embed.description = (
            "> ⚠️ **Hesap bilgileriniz ile uyuşmayan bilgiler paylaşmanız durumunda "
            "işlem talebiniz reddedilecektir.**"
        )
        embed.add_field(
            name="📋  Lütfen aşağıdaki bilgileri eksiksiz doldurun",
            value=(
                "<a:whitearrow:1478394670856933429>  **Kullanıcı adı:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Karakter adı:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Kayıt olurken oluşturduğunuz 4 haneli pin kodu:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Bilgisayarınızın adı:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Bilgisayar MAC adresiniz:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Nesne marketten satın aldıysanız son alınan ürün:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Yeni e-mail adresiniz:**"
            ),
            inline=False
        )
        embed.add_field(
            name="\u200b",
            value=(
                "⚠️ MAC adresinize nasıl ulaşacağınızı bilmiyorsanız **CMD** menüsünü açın "
                "ve `ipconfig /all` veya `ipconfig -all` yazıp ekran görüntüsünü bizimle paylaşın.\n\n"
                "⚠️ Bilgisayar adını nasıl öğreneceğinizi bilmiyorsanız **Sistem** menüsünden "
                "görebilir veya masaüstündeki **Bu Bilgisayar**'a sağ tıklayıp "
                "**Özellikler** sekmesine göz atın."
            ),
            inline=False
        )
        embed.set_footer(text="M2Board Destek Ekibi")
        await interaction.response.send_message(embed=embed)
        log.info(f"/email-değişim → {interaction.channel} ({interaction.user})")

    # ─────────────────────────────────────────────────────────────
    # /güvenli-bilgisayar
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(
        name="güvenli-bilgisayar",
        description="Güvenli Bilgisayar adımlarını açıklar."
    )
    async def guvenli_bilgisayar(self, interaction: discord.Interaction):
        if not destek_ekibi_mi(interaction, self.settings):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="🔐  Güvenli Bilgisayar Adımları", color=0x2F3136)
        embed.add_field(
            name="1️⃣  Siteye Giriş",
            value="Web sitemiz üzerinden hesabınıza giriş yapın.",
            inline=False
        )
        embed.add_field(
            name="2️⃣  Güvenli Bilgisayar Butonu",
            value="Giriş yaptıktan sonra **Güvenli Bilgisayar** butonuna tıklayın.",
            inline=False
        )
        embed.add_field(
            name="3️⃣  Onay Kodu Gönder",
            value="Açılan sayfada hesabınızda kayıtlı e-posta adresine onay kodu gönderin.",
            inline=False
        )
        embed.add_field(
            name="4️⃣  Kodu Doğrula",
            value="E-posta adresinize gelen onay kodunu siteye doğru şekilde girin ve işlemi tamamlayın.",
            inline=False
        )
        embed.add_field(
            name="5️⃣  Onay Bekleyen Cihazlar",
            value="İşlemi tamamladıktan sonra tekrar **Güvenli Bilgisayar** butonuna basarak **Onay Bekleyen Cihazlar** ekranına gidin.",
            inline=False
        )
        embed.add_field(
            name="6️⃣  Cihazı Onayla  ✅",
            value="Hesabınızın açılmasını istediğiniz cihazı listeden seçip onay verin.",
            inline=False
        )
        embed.set_footer(text="M2Board Destek Ekibi")
        await interaction.response.send_message(embed=embed)
        log.info(f"/güvenli-bilgisayar → {interaction.channel} ({interaction.user})")

    # ─────────────────────────────────────────────────────────────
    # /windows-defender
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(
        name="windows-defender",
        description="Windows Güvenlik Engeli çözüm adımlarını açıklar."
    )
    async def windows_defender(self, interaction: discord.Interaction):
        if not destek_ekibi_mi(interaction, self.settings):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="🛡️  Windows Güvenlik Engeli Çözümü", color=0x2F3136)
        embed.description = (
            "▫️ Windows bazı dosyaları tanımadığı için uyarı verebilir veya açılmayı engelleyebilir. "
            "Bu durum virüs kaynaklı değildir, Windows'un yabancı dosyalara karşı aldığı otomatik korumadır.\n\n"
            "Oyunu açabilmek için şu adımları uygulayın:"
        )
        embed.add_field(
            name="📋  Adımlar",
            value=(
                "🔍  Windows arama → **Windows Güvenliği**'ni açın\n"
                "🧩  **Virüs ve Tehdit Koruması** → **Ayarları Yönet** bölümüne girin\n"
                "⛔  **Gerçek Zamanlı Koruma** özelliğini geçici olarak kapatın\n"
                "📁  **Dışlamalar** bölümünden → **Bir dışlama ekle** → **Klasör** seçin\n"
                "🎮  Oyunun kurulu olduğu klasörü seçip dışlama olarak ekleyin\n"
                "🚀  Torrent / Client dosyasını **Yönetici olarak** çalıştırın\n\n"
                "*Bu sadece Windows engelini kaldırmak içindir, sisteminiz için bir risk oluşturmaz.*"
            ),
            inline=False
        )
        embed.add_field(
            name="🔧  Ek Bilgilendirme",
            value=(
                "▫️ Windows Defender güncel değilse bu sorun daha sık yaşanır → "
                "**Windows Update** yapıp Defender'ı güncelleyin.\n"
                "▫️ Farklı bir antivirüs kullanıyorsanız → o antivirüs içinde "
                "**klasör hariç bırakma / karantinadan çıkarma** talimatını uygulayın.\n"
                "▫️ Gerekirse antivirüs programını **15-30 dakika** geçici olarak kapatabilirsiniz."
            ),
            inline=False
        )
        embed.set_footer(text="M2Board Destek Ekibi")
        await interaction.response.send_message(embed=embed)
        log.info(f"/windows-defender → {interaction.channel} ({interaction.user})")

    # ─────────────────────────────────────────────────────────────
    # /kullanıcı-öğren
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(
        name="kullanıcı-öğren",
        description="Kullanıcı adı öğrenme talebi için gerekli bilgi formunu gönderir."
    )
    async def kullanici_ogren(self, interaction: discord.Interaction):
        if not destek_ekibi_mi(interaction, self.settings):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="📨  Kullanıcı Adı Öğrenme Talebi", color=0x2F3136)
        embed.description = (
            "> ⚠️ **Hesap bilgileriniz ile uyuşmayan bilgiler paylaşmanız durumunda "
            "işlem talebiniz reddedilecektir.**"
        )
        embed.add_field(
            name="📋  Lütfen aşağıdaki bilgileri eksiksiz doldurun",
            value=(
                "<a:whitearrow:1478394670856933429>  **Karakter adı:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Kayıt olurken oluşturduğunuz 4 haneli pin kodu:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Bilgisayarınızın adı:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Bilgisayar MAC adresiniz:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Nesne marketten satın aldıysanız son alınan ürün:**\n\n"
                "<a:whitearrow:1478394670856933429>  **Mail adresiniz:**"
            ),
            inline=False
        )
        embed.add_field(
            name="\u200b",
            value=(
                "⚠️ MAC adresinize nasıl ulaşacağınızı bilmiyorsanız **CMD** menüsünü açın "
                "ve `ipconfig /all` veya `ipconfig -all` yazıp ekran görüntüsünü bizimle paylaşın.\n\n"
                "⚠️ Bilgisayar adını nasıl öğreneceğinizi bilmiyorsanız **Sistem** menüsünden "
                "görebilir veya masaüstündeki **Bu Bilgisayar**'a sağ tıklayıp "
                "**Özellikler** sekmesine göz atın."
            ),
            inline=False
        )
        embed.set_footer(text="M2Board Destek Ekibi")
        await interaction.response.send_message(embed=embed)
        log.info(f"/kullanıcı-öğren → {interaction.channel} ({interaction.user})")


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketKomutlar(bot))
