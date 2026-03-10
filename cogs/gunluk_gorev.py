"""cogs/gunluk_gorev.py — /günlük-görev ve /günlük-görev-teslim komutları."""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
import os

import database
from utils.logger import setup_logger

log       = setup_logger("gunluk_gorev")
TR_OFFSET = timedelta(hours=3)
M2B       = "<:m2bcoin:1480481551337783437>"
OK        = "<a:olumlutick:1478524954688356494>"
FAIL_EMO  = "<a:no:1478524993670479942>"
COIN_ANIM = "<a:coin:1478390167310958734>"
BILDIRIM  = "<a:bildirim:1478390691334979645>"
ONERI     = "<a:onerino:1478614338909769799>"
INSTAGRAM = "<a:ınstagram:1478635152614625281>"

GOREV_KANAL_ID = int(os.getenv("GOREV_KANAL_ID", "0"))

INSTAGRAM_LINK = "https://www.instagram.com/tmgamesatius"

GOREVLER = [
    {
        "id":       "instagram_yorum",
        "isim":     "📸 Instagram — Profil Gönderi Yorum",
        "aciklama": f"Instagram sayfamızdaki herhangi bir gönderiye yorum at.\n🔗 {INSTAGRAM_LINK}",
        "odul":     50,
    },
    {
        "id":       "instagram_sponsorlu_yorum",
        "isim":     "📸 Instagram — Sponsorlu Yorum",
        "aciklama": f"Instagram sayfamızdaki sponsorlu gönderiye yorum at.\n🔗 {INSTAGRAM_LINK}",
        "odul":     50,
    },
    {
        "id":       "instagram_hikaye",
        "isim":     "📸 Instagram — Hikaye Etiket",
        "aciklama": f"Instagram hikayende M2Board'ı etiketleyip oyun içi görselini paylaş.\n🔗 {INSTAGRAM_LINK}",
        "odul":     50,
    },
]


def _bugun_tr() -> str:
    return (datetime.now(timezone.utc) + TR_OFFSET).strftime("%Y-%m-%d")

def _gorev_sec(discord_id: int, tarih: str) -> dict:
    seed = hash(f"{discord_id}_{tarih}") % len(GOREVLER)
    return GOREVLER[seed]


class RedSebebiModal(discord.ui.Modal, title="Reddetme Sebebi"):
    sebep = discord.ui.TextInput(
        label="Sebep",
        placeholder="Görevi neden reddediyorsunuz?",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=300,
    )

    def __init__(self, discord_id: int, gorev: dict, bildirim_kanal_id: int, onay_mesaj: discord.Message):
        super().__init__()
        self.discord_id        = discord_id
        self.gorev             = gorev
        self.bildirim_kanal_id = bildirim_kanal_id
        self.onay_mesaj        = onay_mesaj

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Embed güncelle
        embed       = self.onay_mesaj.embeds[0]
        embed.color = 0xE74C3C
        embed.set_footer(text=f"❌ Reddeden: {interaction.user.display_name} | Sebep: {self.sebep.value}")

        # Tüm butonları devre dışı bırak
        view = discord.ui.View()
        await self.onay_mesaj.edit(embed=embed, view=view)

        uye = interaction.guild.get_member(self.discord_id)

        # DM bildirim
        try:
            if uye:
                dm_embed = discord.Embed(
                    title=f"{FAIL_EMO} Görevin Reddedildi — M2Board",
                    description=(
                        f"**{self.gorev['isim']}** görevi onaylanmadı.\n\n"
                        f"📝 **Sebep:** {self.sebep.value}\n\n"
                        "Görevi eksiksiz tamamlayıp `/günlük-görev-teslim` ile tekrar gönder."
                    ),
                    color=0xE74C3C,
                )
                await uye.send(embed=dm_embed)
        except Exception:
            pass  # DM kapalıysa sessiz geç

        log.info(f"Görev reddedildi: discord_id={self.discord_id} → {self.gorev['id']} | Sebep: {self.sebep.value}")


class GorevOnayView(discord.ui.View):
    def __init__(self, discord_id: int, gorev: dict, bildirim_kanal_id: int):
        super().__init__(timeout=None)
        self.discord_id        = discord_id
        self.gorev             = gorev
        self.bildirim_kanal_id = bildirim_kanal_id

    async def _yetkili_mi(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        rol = discord.utils.get(interaction.guild.roles, name="Admin")
        return bool(rol and rol in interaction.user.roles)

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._yetkili_mi(interaction):
            await interaction.response.send_message("Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer()

        uye    = interaction.guild.get_member(self.discord_id)
        u_isim = uye.display_name if uye else "Kullanıcı"
        yeni   = await database.add_coins(self.discord_id, u_isim, self.gorev["odul"])

        async with database.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO gorev_log (discord_id, gorev_id, tarih) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                self.discord_id, self.gorev["id"], _bugun_tr(),
            )

        # Embed güncelle
        for item in self.children:
            item.disabled = True
        embed       = interaction.message.embeds[0]
        embed.color = 0x2ECC71
        embed.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=embed, view=self)

        # DM bildirim
        try:
            if uye:
                dm_embed = discord.Embed(
                    title=f"{OK} Görevin Onaylandı! — M2Board",
                    description=(
                        f"{BILDIRIM} **{self.gorev['isim']}** görevi onaylandı! 🎉\n\n"
                        f"{COIN_ANIM} **+{self.gorev['odul']} M2B Coin** hesabına eklendi!\n"
                        f"{M2B} Yeni bakiyen: **{yeni:,} M2B Coin**\n\n"
                        f"M2Board sunucusunda `/bakiye` yazarak kontrol edebilirsin."
                    ),
                    color=0x2ECC71,
                )
                await uye.send(embed=dm_embed)
        except Exception:
            pass  # DM kapalıysa sessiz geç

        log.info(f"Görev onaylandı: {u_isim} → {self.gorev['id']} +{self.gorev['odul']} coin")

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._yetkili_mi(interaction):
            await interaction.response.send_message("Yetkin yok!", ephemeral=True)
            return
        # Modal aç — sebep zorunlu
        await interaction.response.send_modal(
            RedSebebiModal(self.discord_id, self.gorev, self.bildirim_kanal_id, interaction.message)
        )


class GorevTeslimModal(discord.ui.Modal, title="Görev Teslimi"):
    oyun_hesap = discord.ui.TextInput(
        label="Oyun Hesap Adın (Nick)",
        placeholder="Örn: Warrior123",
        min_length=2, max_length=50,
    )
    karakter_adi = discord.ui.TextInput(
        label="Karakter Adın",
        placeholder="Örn: DarkKnight",
        min_length=2, max_length=50,
    )
    instagram_nick = discord.ui.TextInput(
        label="Instagram Kullanıcı Adın (@olmadan)",
        placeholder="Örn: ali.metin2",
        min_length=2, max_length=50,
    )
    kanit = discord.ui.TextInput(
        label="Gyazo Kanıt Linki",
        placeholder="https://gyazo.com/...",
        min_length=10, max_length=200,
    )

    def __init__(self, gorev: dict, discord_id: int, kanal_id: int):
        super().__init__()
        self.gorev      = gorev
        self.discord_id = discord_id
        self.kanal_id   = kanal_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bugun = _bugun_tr()

        async with database.pool.acquire() as conn:
            tamamlandi = await conn.fetchval(
                "SELECT 1 FROM gorev_log WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3",
                interaction.user.id, self.gorev["id"], bugun,
            )

        if tamamlandi:
            await interaction.followup.send(
                f"{OK} Bugünkü görevini zaten tamamladın!", ephemeral=True
            )
            return

        if not GOREV_KANAL_ID:
            await interaction.followup.send("❌ `GOREV_KANAL_ID` ayarlanmamış!", ephemeral=True)
            return

        try:
            admin_kanal = interaction.client.get_channel(GOREV_KANAL_ID) or await interaction.client.fetch_channel(GOREV_KANAL_ID)
        except Exception:
            await interaction.followup.send("❌ Admin kanalı bulunamadı.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{BILDIRIM} Görev Teslimi — Onay Bekliyor",
            color=0xFFD700,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(
            name="👤 Discord",
            value=f"{interaction.user.mention}\n`ID: {interaction.user.id}`",
            inline=True,
        )
        embed.add_field(name="🎮 Oyun Hesap Adı",  value=self.oyun_hesap.value,    inline=True)
        embed.add_field(name="⚔️ Karakter Adı",    value=self.karakter_adi.value,  inline=True)
        embed.add_field(name="📷 Instagram Nick",   value=f"@{self.instagram_nick.value}", inline=True)
        embed.add_field(name="📋 Görev",            value=self.gorev["isim"],       inline=False)
        embed.add_field(name="🎁 Ödül",             value=f"**{self.gorev['odul']}** {M2B}", inline=True)
        embed.add_field(name="📎 Kanıt",            value=self.kanit.value,         inline=False)
        embed.set_footer(text=f"Tarih: {bugun}")

        view = GorevOnayView(interaction.user.id, self.gorev, self.kanal_id)
        await admin_kanal.send(embed=embed, view=view)

        await interaction.followup.send(
            f"{OK} Görevin teslim edildi! Admin onayından sonra **{self.gorev['odul']}** {M2B} hesabına eklenecek.",
            ephemeral=True,
        )
        log.info(f"Görev teslim (modal): {interaction.user} → {self.gorev['id']}")


class GunlukGorevCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="günlük-görev", description="Bugünkü günlük görevini gör!")
    async def gunluk_gorev(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bugun = _bugun_tr()
            gorev = _gorev_sec(interaction.user.id, bugun)

            async with database.pool.acquire() as conn:
                tamamlandi = await conn.fetchval(
                    "SELECT 1 FROM gorev_log WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3",
                    interaction.user.id, gorev["id"], bugun,
                )

            embed = discord.Embed(
                title=f"{BILDIRIM} Günlük Görev",
                color=0x2ECC71 if tamamlandi else 0xFFD700,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name=f"{INSTAGRAM} {gorev["isim"]}", value=gorev["aciklama"], inline=False)
            embed.add_field(name="🎁 Ödül",    value=f"**{gorev['odul']}** {M2B}", inline=True)
            embed.add_field(
                name="📌 Durum",
                value=f"{OK} **Tamamlandı!**" if tamamlandi else "⏳ Bekliyor",
                inline=True,
            )
            embed.add_field(
                name="⚠️ Önemli Not",
                value=(
                    "Görsel kanıtlarını **[Gyazo](https://gyazo.com)** ile gönder!\n"
                    "Gyazo dışında gönderilen kanıtlar **kabul edilmeyecektir.**"
                ),
                inline=False,
            )

            if tamamlandi:
                embed.set_footer(text="Yarın yeni bir görev gelecek!")
            else:
                embed.set_footer(text="Görevi tamamlayınca /günlük-görev-teslim kullan!")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            log.error(f"günlük-görev hatası: {e}", exc_info=True)
            await interaction.followup.send("❌ Bir hata oluştu.", ephemeral=True)

    @app_commands.command(name="günlük-görev-teslim", description="Tamamladığın görevi teslim et!")
    async def gunluk_gorev_teslim(self, interaction: discord.Interaction):
        try:
            await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bugun = _bugun_tr()
            gorev = _gorev_sec(interaction.user.id, bugun)

            async with database.pool.acquire() as conn:
                tamamlandi = await conn.fetchval(
                    "SELECT 1 FROM gorev_log WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3",
                    interaction.user.id, gorev["id"], bugun,
                )

            if tamamlandi:
                await interaction.response.send_message(
                    f"{OK} Bugünkü görevini zaten tamamladın! Yarın tekrar gel.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_modal(
                GorevTeslimModal(gorev, interaction.user.id, interaction.channel_id)
            )

        except Exception as e:
            log.error(f"günlük-görev-teslim hatası: {e}", exc_info=True)
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunlukGorevCog(bot))
