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
OK        = "<a:check:1478394670856933429>"
FAIL      = "❌"

GOREV_KANAL_ID = int(os.getenv("GOREV_KANAL_ID", "0"))

GOREVLER = [
    {
        "id":       "facebook",
        "isim":     "📘 Facebook Görevi",
        "aciklama": "Facebook grubunda M2Board ile ilgili bir gönderi paylaş ve özgün yorumlar yaz.",
        "odul":     50,
    },
    {
        "id":       "turkmmo",
        "isim":     "🎮 Turkmmo Görevi",
        "aciklama": "Turkmmo'da M2Board Story'si paylaş.",
        "odul":     50,
    },
    {
        "id":       "instagram_yorum",
        "isim":     "📸 Instagram — Son Gönderi Yorum",
        "aciklama": "Instagram sayfamızdaki son gönderiye yorum at.",
        "odul":     50,
    },
    {
        "id":       "instagram_sponsorlu_yorum",
        "isim":     "📸 Instagram — Sponsorlu Yorum",
        "aciklama": "Instagram sayfamızdaki sponsorlu gönderiye yorum at.",
        "odul":     50,
    },
    {
        "id":       "instagram_hikaye",
        "isim":     "📸 Instagram — Hikaye Paylaşım",
        "aciklama": "Instagram sayfamızdaki sponsorlu gönderiyi hikayende paylaş.",
        "odul":     50,
    },
]


def _bugun_tr() -> str:
    return (datetime.now(timezone.utc) + TR_OFFSET).strftime("%Y-%m-%d")

def _gorev_sec(discord_id: int, tarih: str) -> dict:
    seed = hash(f"{discord_id}_{tarih}") % len(GOREVLER)
    return GOREVLER[seed]


class GorevOnayView(discord.ui.View):
    def __init__(self, discord_id: int, gorev: dict, bildirim_kanal_id: int):
        super().__init__(timeout=None)
        self.discord_id         = discord_id
        self.gorev              = gorev
        self.bildirim_kanal_id  = bildirim_kanal_id

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

        for item in self.children:
            item.disabled = True
        embed        = interaction.message.embeds[0]
        embed.color  = 0x2ECC71
        embed.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=embed, view=self)

        # Kullanıcıya bildirim kanalında mention
        try:
            kanal = interaction.guild.get_channel(self.bildirim_kanal_id)
            if kanal:
                bildirim = discord.Embed(
                    title=f"{OK} Görevin Onaylandı!",
                    description=(
                        f"**{self.gorev['isim']}** görevi onaylandı! 🎉\n\n"
                        f"{M2B} **+{self.gorev['odul']} M2B Coin** hesabına eklendi!\n"
                        f"💰 Yeni bakiyen: **{yeni:,} M2B Coin**\n\n"
                        f"`/bakiye` yazarak kontrol edebilirsin."
                    ),
                    color=0x2ECC71,
                )
                await kanal.send(content=uye.mention if uye else "", embed=bildirim)
        except Exception as e:
            log.error(f"Bildirim gönderilemedi: {e}")

        log.info(f"Görev onaylandı: {u_isim} → {self.gorev['id']} +{self.gorev['odul']} coin")

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._yetkili_mi(interaction):
            await interaction.response.send_message("Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer()

        for item in self.children:
            item.disabled = True
        embed       = interaction.message.embeds[0]
        embed.color = 0xE74C3C
        embed.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=embed, view=self)

        try:
            uye   = interaction.guild.get_member(self.discord_id)
            kanal = interaction.guild.get_channel(self.bildirim_kanal_id)
            if kanal and uye:
                bildirim = discord.Embed(
                    title="❌ Görevin Reddedildi",
                    description=(
                        f"**{self.gorev['isim']}** görevi onaylanmadı.\n\n"
                        "Lütfen görevi eksiksiz tamamladığından emin ol ve tekrar dene."
                    ),
                    color=0xE74C3C,
                )
                await kanal.send(content=uye.mention, embed=bildirim)
        except Exception as e:
            log.error(f"Red bildirimi gönderilemedi: {e}")


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
                title="📋 Günlük Görev",
                color=0x2ECC71 if tamamlandi else 0xFFD700,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name=gorev["isim"], value=gorev["aciklama"], inline=False)
            embed.add_field(name="🎁 Ödül",   value=f"**{gorev['odul']}** {M2B}", inline=True)
            embed.add_field(
                name="📌 Durum",
                value=f"{OK} **Tamamlandı!**" if tamamlandi else "⏳ Bekliyor",
                inline=True,
            )

            if tamamlandi:
                embed.set_footer(text="Yarın yeni bir görev gelecek!")
            else:
                embed.add_field(
                name="📌 Önemli Not",
                value=(
                    "Görsel kanıtlarını **[Gyazo](https://gyazo.com)** ile gönder!\n"
                    "Gyazo dışında gönderilen kanıtlar **kabul edilmeyecektir.**"
                ),
                inline=False,
            )
            embed.set_footer(text="Görevi tamamlayınca /günlük-görev-teslim kullan!")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            log.error(f"günlük-görev hatası: {e}", exc_info=True)
            await interaction.followup.send("❌ Bir hata oluştu.", ephemeral=True)

    @app_commands.command(name="günlük-görev-teslim", description="Tamamladığın görevi teslim et!")
    @app_commands.describe(
        oyun_ici_isim="Oyun içindeki karakterin adı",
        kanit="Gyazo ile aldığın ekran görüntüsü linki (https://gyazo.com)"
    )
    async def gunluk_gorev_teslim(self, interaction: discord.Interaction, oyun_ici_isim: str, kanit: str):
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

            if tamamlandi:
                await interaction.followup.send(
                    f"{OK} Bugünkü görevini zaten tamamladın! Yarın tekrar gel.",
                    ephemeral=True,
                )
                return

            if not GOREV_KANAL_ID:
                await interaction.followup.send(
                    "❌ `GOREV_KANAL_ID` Railway'de ayarlanmamış!", ephemeral=True
                )
                return

            admin_kanal = self.bot.get_channel(GOREV_KANAL_ID)
            if not admin_kanal:
                admin_kanal = await self.bot.fetch_channel(GOREV_KANAL_ID)
            if not admin_kanal:
                await interaction.followup.send("❌ Admin kanalı bulunamadı.", ephemeral=True)
                return

            embed = discord.Embed(
                title="📬 Görev Teslimi — Onay Bekliyor",
                color=0xFFD700,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(
                name="👤 Kullanıcı",
                value=f"{interaction.user.mention}\n`ID: {interaction.user.id}`",
                inline=False,
            )
            embed.add_field(name="🎮 Oyun İçi İsim", value=oyun_ici_isim, inline=False)
            embed.add_field(name="📋 Görev", value=gorev["isim"],              inline=True)
            embed.add_field(name="🎁 Ödül",  value=f"**{gorev['odul']}** {M2B}", inline=True)
            embed.add_field(name="📎 Kanıt", value=kanit,                      inline=False)
            embed.set_footer(text=f"Tarih: {bugun} | Kullanıcı ID: {interaction.user.id}")

            view = GorevOnayView(interaction.user.id, gorev, interaction.channel_id)
            await admin_kanal.send(embed=embed, view=view)

            await interaction.followup.send(
                f"{OK} Görevin teslim edildi! Admin onayından sonra **{gorev['odul']}** {M2B} hesabına eklenecek.",
                ephemeral=True,
            )
            log.info(f"Görev teslim: {interaction.user} → {gorev['id']}")

        except Exception as e:
            log.error(f"günlük-görev-teslim hatası: {e}", exc_info=True)
            await interaction.followup.send("❌ Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunlukGorevCog(bot))
