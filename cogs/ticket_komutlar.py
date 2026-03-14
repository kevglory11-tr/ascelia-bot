"""
cogs/ticket_komutlar.py — Ticket içi destek ekibi komutları
Komutlar yalnızca ticket kanallarında ve destek rolüne sahip kişiler tarafından kullanılabilir.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from config.settings import Settings
from cogs.ticket import acik_ticketlar, destek_ekibi_mi

log = logging.getLogger("cog.ticket_komutlar")


def ticket_kanal_mi(kanal_id: int) -> bool:
    """Kanalın aktif bir ticket kanalı olup olmadığını kontrol et."""
    return kanal_id in acik_ticketlar


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
        # Yalnızca ticket kanalında çalışır
        if not ticket_kanal_mi(interaction.channel_id):
            await interaction.response.send_message(
                "❌ Bu komut yalnızca ticket kanallarında kullanılabilir.",
                ephemeral=True
            )
            return

        # Yalnızca destek ekibi kullanabilir
        if not destek_ekibi_mi(interaction):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨  E-Mail Değişikliği",
            color=0x2F3136
        )

        embed.description = (
            "> ⚠️ **Hesap bilgileriniz ile uyuşmayan bilgiler paylaşmanız durumunda "
            "işlem talebiniz reddedilecektir.**"
        )

        embed.add_field(
            name="📋  Lütfen aşağıdaki bilgileri eksiksiz doldurun",
            value=(
                "**Kullanıcı adı:**\n"
                "**Karakter adı:**\n"
                "**Kayıt olurken oluşturduğunuz 4 haneli pin kodu:**\n"
                "**Bilgisayarınızın adı:**\n"
                "**Bilgisayar MAC adresiniz:**\n"
                "**Nesne marketten satın aldıysanız son alınan ürün:**\n"
                "**Yeni e-mail adresiniz:**"
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
        if not ticket_kanal_mi(interaction.channel_id):
            await interaction.response.send_message(
                "❌ Bu komut yalnızca ticket kanallarında kullanılabilir.",
                ephemeral=True
            )
            return

        if not destek_ekibi_mi(interaction):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔐  Güvenli Bilgisayar Adımları",
            color=0x2F3136
        )

        embed.add_field(
            name="\u200b",
            value=(
                "**1️⃣**  Web sitemiz üzerinden hesabınıza giriş yapın.\n\n"
                "**2️⃣**  Giriş yaptıktan sonra **Güvenli Bilgisayar** butonuna tıklayın.\n\n"
                "**3️⃣**  Açılan sayfada hesabınızda kayıtlı bulunan e-posta adresine onay kodu gönderin.\n\n"
                "**4️⃣**  E-posta adresinize gelen onay kodunu sitemizde doğru şekilde girin ve işlemi tamamlayın.\n\n"
                "**5️⃣**  Bu adım başarılı şekilde tamamlandıktan sonra tekrar **Güvenli Bilgisayar** butonuna "
                "basarak **Onay Bekleyen Cihazlar** ekranına gidin.\n\n"
                "**6️⃣**  Burada hesabınızın açılmasını istediğiniz cihazı seçip onay verebilirsiniz. ✅"
            ),
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
        if not ticket_kanal_mi(interaction.channel_id):
            await interaction.response.send_message(
                "❌ Bu komut yalnızca ticket kanallarında kullanılabilir.",
                ephemeral=True
            )
            return

        if not destek_ekibi_mi(interaction):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛡️  Windows Güvenlik Engeli Çözümü",
            color=0x2F3136
        )

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
        if not ticket_kanal_mi(interaction.channel_id):
            await interaction.response.send_message(
                "❌ Bu komut yalnızca ticket kanallarında kullanılabilir.",
                ephemeral=True
            )
            return

        if not destek_ekibi_mi(interaction):
            await interaction.response.send_message(
                "❌ Bu komutu yalnızca destek ekibi kullanabilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨  Kullanıcı Adı Öğrenme Talebi",
            color=0x2F3136
        )

        embed.description = (
            "> ⚠️ **Hesap bilgileriniz ile uyuşmayan bilgiler paylaşmanız durumunda "
            "işlem talebiniz reddedilecektir.**"
        )

        embed.add_field(
            name="📋  Lütfen aşağıdaki bilgileri eksiksiz doldurun",
            value=(
                "**Karakter adı:**\n"
                "**Kayıt olurken oluşturduğunuz 4 haneli pin kodu:**\n"
                "**Bilgisayarınızın adı:**\n"
                "**Bilgisayar MAC adresiniz:**\n"
                "**Nesne marketten satın aldıysanız son alınan ürün:**\n"
                "**Mail adresiniz:**"
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
