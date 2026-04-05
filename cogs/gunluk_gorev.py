"""
cogs/gunluk_gorev.py — Günlük Görev sistemi (revize)

Görevler:
  1. Sunucuya 25 mesaj gönder          — 25 coin  (otomatik)
  2. 25 farklı mesajı yanıtla           — 25 coin  (otomatik)
  3. Ses kanalında 15 dk aktif ol       — 25 coin  (otomatik)
  4. 25 farklı mesaja tepki bırak       — 25 coin  (otomatik)
  5. metin2pvp.biz günlük oy ver        — admin onaylı (ödül: 100 MP)
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import date, datetime
import os

import database
from utils.logger import setup_logger

log       = setup_logger("gunluk_gorev")
M2B       = "<:m2bcoin:1480481551337783437>"
OK        = "<a:olumlutick:1478524954688356494>"
FAIL_EMO  = "<a:no:1478524993670479942>"
COIN_ANIM = "<a:coin:1478390167310958734>"
BILDIRIM  = "<a:bildirim:1478390691334979645>"

GOREV_KANAL_ID = int(os.getenv("GOREV_KANAL_ID", "0"))
OY_LINK        = "https://metin2pvp.biz/servers/m2-board-1-115-farm-sunucusu-otomatik-av"

GOREVLER = [
    {
        "id":      "mesaj_25",
        "baslik":  "Sunucuya 25 Mesaj Gönder",
        "aciklama": "Sunucuda bugün 25 mesaj gönder.",
        "odul":    25,
        "tur":     "otomatik",
    },
    {
        "id":      "yanit_25",
        "baslik":  "25 Farklı Mesajı Yanıtla",
        "aciklama": "Sunucuda 25 farklı kişinin mesajını yanıtla.",
        "odul":    25,
        "tur":     "otomatik",
    },
    {
        "id":      "instagram_yorum",
        "baslik":  "Instagram Gönderisine Yorum At",
        "aciklama": "[@tmgamesatius](https://www.instagram.com/tmgamesatius) Instagram profilindeki son oyun gönderisine yorum at.",
        "odul":    25,
        "tur":     "admin",
    },
    {
        "id":      "tepki_25",
        "baslik":  "25 Farklı Mesaja Tepki Bırak",
        "aciklama": "Sunucuda 25 farklı kişinin mesajına tepki ekle.",
        "odul":    25,
        "tur":     "otomatik",
    },
    {
        "id":      "oy_ver",
        "baslik":  "Sunucumuzu Oyla",
        "aciklama": f"[metin2pvp.biz]({OY_LINK}) sitesinde sunucumuzu günlük oyla.",
        "odul":    0,
        "tur":     "admin",
    },
]


def bugunun_gorevi(discord_id: int) -> dict:
    bugun = date.today().isoformat()
    seed  = hash(f"{discord_id}_{bugun}") % len(GOREVLER)
    return GOREVLER[seed]


# ── In-memory tracker (gün bazlı sıfırlanır) ──────────────────
_tracker: dict[int, dict] = {}
_son_gun: date = date.today()


def _tracker_kontrol():
    global _son_gun
    bugun = date.today()
    if bugun != _son_gun:
        _tracker.clear()
        _son_gun = bugun


def _t(discord_id: int) -> dict:
    _tracker_kontrol()
    if discord_id not in _tracker:
        _tracker[discord_id] = {
            "mesajlar":      set(),
            "yanitlar":      set(),
            "tepkiler":      set(),
            "ses_baslangic": None,
            "ses_sure":      0.0,
        }
    return _tracker[discord_id]


def _ilerleme(discord_id: int, gorev_id: str) -> tuple:
    t = _t(discord_id)
    if gorev_id == "mesaj_25":  return len(t["mesajlar"]), 25
    if gorev_id == "yanit_25":  return len(t["yanitlar"]), 25
    if gorev_id == "tepki_25":  return len(t["tepkiler"]),  25
    return 0, 1


# ── Oy Modalı ─────────────────────────────────────────────────
class AdminGorevModal(discord.ui.Modal, title="Görev Kanıtı"):
    oyun_adi = discord.ui.TextInput(
        label="Oyun Hesap Adı", placeholder="Metin2 oyun adın",
        min_length=2, max_length=50)
    karakter = discord.ui.TextInput(
        label="Karakter Adı", placeholder="Karakterin adı",
        min_length=2, max_length=50)
    kanit = discord.ui.TextInput(
        label="Ekran Görüntüsü Linki", placeholder="Gyazo veya Imgur linki",
        min_length=5, max_length=200)

    def __init__(self, gorev: dict):
        super().__init__(title=f"Görev Kanıtı — {gorev['baslik'][:30]}")
        self.gorev = gorev

    async def on_submit(self, interaction: discord.Interaction):
        bugun = date.today().isoformat()
        async with database.pool.acquire() as conn:
            mevcut = await conn.fetchval(
                "SELECT id FROM gunluk_gorev_log WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3",
                interaction.user.id, self.gorev["id"], bugun
            )
            if mevcut:
                await interaction.response.send_message(
                    f"{FAIL_EMO} Bugün zaten gönderdın! Onay bekleniyor.", ephemeral=True)
                return

            odul_metin = "100 MP Kuponu" if self.gorev["id"] == "oy_ver" else f"{self.gorev['odul']} M2B Coin"

            await conn.execute(
                """INSERT INTO gunluk_gorev_log
                   (discord_id, isim, gorev_id, gorev_baslik, durum, tarih, kanit, odul)
                   VALUES ($1,$2,$3,$4,'bekliyor',$5,$6,$7)""",
                interaction.user.id, interaction.user.display_name,
                self.gorev["id"], self.gorev["baslik"], bugun,
                f"Oyun: {self.oyun_adi.value} | Karakter: {self.karakter.value} | {self.kanit.value}",
                self.gorev["odul"]
            )

        await interaction.response.send_message(
            f"{OK} Talebın alındı! Onaylanınca **{odul_metin}** hesabına eklenecek.",
            ephemeral=True)

        if GOREV_KANAL_ID:
            kanal = interaction.client.get_channel(GOREV_KANAL_ID)
            if kanal:
                embed = discord.Embed(
                    title=f"{BILDIRIM}  Görev Kanıtı — {self.gorev['baslik']}",
                    color=0x2ECC71)
                embed.add_field(name="Kullanıcı", value=interaction.user.mention, inline=True)
                embed.add_field(name="Oyun Adı",  value=self.oyun_adi.value,      inline=True)
                embed.add_field(name="Karakter",  value=self.karakter.value,      inline=True)
                embed.add_field(name="Kanıt",     value=self.kanit.value,         inline=False)
                embed.add_field(name="Ödül",      value=odul_metin,               inline=True)
                embed.set_footer(text=f"ID: {interaction.user.id} | {bugun}")
                await kanal.send(
                    embed=embed,
                    view=AdminOnayView(
                        interaction.user.id, interaction.user.display_name,
                        self.gorev["id"], bugun, self.gorev["odul"],
                        self.gorev["id"] == "oy_ver"
                    )
                )
        log.info(f"Admin görev talebi: {interaction.user} → {self.gorev['id']}")


class AdminOnayView(discord.ui.View):
    def __init__(self, discord_id, isim, gorev_id, tarih, odul_coin, mp_odulu=False):
        super().__init__(timeout=None)
        self.discord_id = discord_id
        self.isim       = isim
        self.gorev_id   = gorev_id
        self.tarih      = tarih
        self.odul_coin  = odul_coin
        self.mp_odulu   = mp_odulu  # True ise 100 MP, False ise coin

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with database.pool.acquire() as conn:
            await conn.execute(
                "UPDATE gunluk_gorev_log SET durum='onaylandi' WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3",
                self.discord_id, self.gorev_id, self.tarih)
            if not self.mp_odulu and self.odul_coin > 0:
                uye_obj = interaction.guild.get_member(self.discord_id)
                isim = uye_obj.display_name if uye_obj else self.isim
                await database.add_coins(self.discord_id, isim, self.odul_coin,
                                         aciklama=f"Günlük görev onayı: {self.gorev_id}")
        try:
            uye = interaction.guild.get_member(self.discord_id)
            if uye:
                if self.mp_odulu:
                    msg = (f"{OK} **Günlük görevin onaylandı!**\n"
                           "**100 MP Kuponu** için ticket açabilirsin.")
                else:
                    msg = (f"{OK} **Günlük görevin onaylandı!**\n"
                           f"{COIN_ANIM} **+{self.odul_coin} M2B Coin** hesabına eklendi!")
                await uye.send(msg)
        except Exception:
            pass
        for child in self.children:
            child.disabled = True
        odul_str = "100 MP" if self.mp_odulu else f"+{self.odul_coin} Coin"
        await interaction.response.edit_message(
            content=f"✅ **{self.isim}** — Onaylandı · {odul_str} ({interaction.user.display_name})",
            view=self)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with database.pool.acquire() as conn:
            await conn.execute(
                "UPDATE gunluk_gorev_log SET durum='reddedildi' WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3",
                self.discord_id, self.gorev_id, self.tarih)
        try:
            uye = interaction.guild.get_member(self.discord_id)
            if uye:
                await uye.send(
                    f"{FAIL_EMO} **Günlük görevin reddedildi.**\n"
                    "Geçerli bir kanıt gönderdiğinden emin ol.")
        except Exception:
            pass
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ **{self.isim}** — Reddedildi ({interaction.user.display_name})",
            view=self)


class AdminGorevView(discord.ui.View):
    def __init__(self, gorev):
        super().__init__(timeout=300)
        self.gorev = gorev

    @discord.ui.button(label="Kanıt Gönder", style=discord.ButtonStyle.primary, emoji="🗳️")
    async def gonder(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdminGorevModal(self.gorev))


# ── Cog ────────────────────────────────────────────────────────
class GunlukGorevCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        async with database.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS gunluk_gorev_log (
                    id           SERIAL PRIMARY KEY,
                    discord_id   BIGINT NOT NULL,
                    isim         TEXT,
                    gorev_id     TEXT NOT NULL,
                    gorev_baslik TEXT,
                    durum        TEXT DEFAULT 'bekliyor',
                    tarih        TEXT NOT NULL,
                    kanit        TEXT,
                    odul         INT  DEFAULT 0,
                    created_at   TIMESTAMP DEFAULT NOW()
                )
            """)
        log.info("Günlük görev tablosu hazır.")

    # ── Event: mesaj ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gorev = bugunun_gorevi(message.author.id)
        t = _t(message.author.id)

        if gorev["id"] == "mesaj_25":
            t["mesajlar"].add(message.id)
            if len(t["mesajlar"]) == 25:
                await self._tamamla(message.author, message.guild, gorev)

        elif gorev["id"] == "yanit_25" and message.reference:
            ref = message.reference.resolved
            if ref and hasattr(ref, "author") and ref.author.id != message.author.id:
                t["yanitlar"].add(ref.author.id)
                if len(t["yanitlar"]) == 25:
                    await self._tamamla(message.author, message.guild, gorev)

    # ── Event: tepki ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user):
        if user.bot or not reaction.message.guild:
            return
        gorev = bugunun_gorevi(user.id)
        if gorev["id"] != "tepki_25":
            return
        t = _t(user.id)
        if reaction.message.author.id != user.id:
            t["tepkiler"].add(reaction.message.id)
            if len(t["tepkiler"]) == 25:
                member = reaction.message.guild.get_member(user.id)
                if member:
                    await self._tamamla(member, reaction.message.guild, gorev)

    # ── Görev tamamlama ────────────────────────────────────────
    async def _tamamla(self, member: discord.Member, guild: discord.Guild, gorev: dict):
        bugun = date.today().isoformat()
        async with database.pool.acquire() as conn:
            mevcut = await conn.fetchval(
                """SELECT id FROM gunluk_gorev_log
                   WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3 AND durum='tamamlandi'""",
                member.id, gorev["id"], bugun)
            if mevcut:
                return

            await conn.execute(
                """INSERT INTO gunluk_gorev_log
                   (discord_id, isim, gorev_id, gorev_baslik, durum, tarih, odul)
                   VALUES ($1,$2,$3,$4,'tamamlandi',$5,$6)
                   ON CONFLICT DO NOTHING""",
                member.id, member.display_name,
                gorev["id"], gorev["baslik"], bugun, gorev["odul"])

            yeni = await database.add_coins(
                member.id, member.display_name, gorev["odul"],
                aciklama=f"Günlük görev: {gorev['baslik']}")

        try:
            await member.send(
                f"{OK} **Günlük görevin tamamlandı!**\n"
                f"**{gorev['baslik']}**\n\n"
                f"{COIN_ANIM} **+{gorev['odul']} M2B Coin** hesabına eklendi!\n"
                f"Yeni bakiyen: **{yeni} M2B Coin**")
        except Exception:
            pass
        log.info(f"Görev tamamlandı: {member} → {gorev['id']} +{gorev['odul']} coin")

    # ── /günlük-görev komutu ──────────────────────────────────
    @app_commands.command(name="günlük-görev", description="Bugünkü görevini görüntüle.")
    async def gunluk_gorev(self, interaction: discord.Interaction):
        gorev = bugunun_gorevi(interaction.user.id)
        bugun = date.today().isoformat()

        async with database.pool.acquire() as conn:
            kayit = await conn.fetchrow(
                """SELECT durum FROM gunluk_gorev_log
                   WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3""",
                interaction.user.id, gorev["id"], bugun)

        tamamlandi = kayit and kayit["durum"] in ("tamamlandi", "onaylandi", "bekliyor")

        embed = discord.Embed(
            title=f"{BILDIRIM}  Günlük Görev",
            color=0x95A5A6 if tamamlandi else 0x2ECC71)
        embed.add_field(name="Görev",    value=f"**{gorev['baslik']}**", inline=False)
        embed.add_field(name="Açıklama", value=gorev["aciklama"],        inline=False)

        if gorev["id"] == "oy_ver":
            embed.add_field(name="Ödül", value="🎟️ 100 MP Kuponu", inline=True)
        else:
            embed.add_field(name="Ödül", value=f"{COIN_ANIM} {gorev['odul']} M2B Coin", inline=True)

        if tamamlandi:
            durum_txt = {"tamamlandi": "✅ Tamamlandı", "onaylandi": "✅ Onaylandı", "bekliyor": "⏳ Onay Bekliyor"}
            embed.add_field(name="Durum", value=durum_txt.get(kayit["durum"], "✅"), inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if gorev["tur"] == "otomatik":
            mevcut, hedef = _ilerleme(interaction.user.id, gorev["id"])
            dolu   = min(mevcut, 10)
            bos    = 10 - dolu
            embed.add_field(
                name="İlerleme",
                value=f"{'█' * dolu}{'░' * bos}  {mevcut}/{hedef}",
                inline=False)
            embed.set_footer(text="Görevi tamamladığında coin otomatik yatacak!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed.set_footer(text=f"Oy verdikten sonra kanıtını gönder → {OY_LINK}")
            await interaction.response.send_message(
                embed=embed, view=AdminGorevView(gorev), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunlukGorevCog(bot))
