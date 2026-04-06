"""
cogs/gunluk_gorev.py — Günlük Görev sistemi (revize)

Görevler:
  1. Sunucuya 25 mesaj gönder          — 25 coin  (otomatik)
  2. 25 farklı mesajı yanıtla           — 25 coin  (otomatik)
  3. Instagram gönderisine yorum at     — 25 coin  (admin onaylı)
  4. 25 farklı mesaja tepki bırak       — 25 coin  (otomatik)
  5. metin2pvp.biz günlük oy ver        — admin onaylı (ödül: 100 MP)
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import date, datetime, timezone, timedelta
import os

import database
from utils.logger import setup_logger
from config.coin_settings import (
    ROL_VANGUARD_ID, ROL_HARBINGER_ID, ROL_SENTINEL_ID, ROL_LUMINARY_ID
)

log       = setup_logger("gunluk_gorev")
_TR_OFF   = timedelta(hours=3)
M2B       = "<:m2bcoin:1480481551337783437>"


def _bugun_tr() -> date:
    """Railway UTC sunucusunda Türkiye saatiyle (UTC+3) bugünün tarihini döndürür."""
    return (datetime.now(timezone.utc) + _TR_OFF).date()
OK        = "<a:olumlutick:1478524954688356494>"
FAIL_EMO  = "<a:no:1478524993670479942>"
COIN_ANIM = "<a:coin:1478390167310958734>"
BILDIRIM  = "<a:bildirim:1478390691334979645>"

GOREV_KANAL_ID = int(os.getenv("GOREV_KANAL_ID", "0"))
OY_LINK        = "https://metin2pvp.biz/servers/m2-board-1-115-farm-sunucusu-otomatik-av"

ROL_ESIKLERI = {
    3:  ROL_VANGUARD_ID,
    6:  ROL_HARBINGER_ID,
    9:  ROL_SENTINEL_ID,
    12: ROL_LUMINARY_ID,
}

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


# ── In-memory tracker (gün bazlı sıfırlanır) ──────────────────
_tracker: dict[int, dict] = {}
_son_gun: date = _bugun_tr()
# Görev yenileme sayacı: {discord_id: yenileme_sayisi}
_yenileme: dict[int, int] = {}


def _tracker_kontrol():
    global _son_gun, _yenileme
    bugun = _bugun_tr()
    if bugun != _son_gun:
        _tracker.clear()
        _yenileme.clear()
        _son_gun = bugun


def _t(discord_id: int) -> dict:
    _tracker_kontrol()
    if discord_id not in _tracker:
        _tracker[discord_id] = {
            "mesajlar": set(),
            "yanitlar": set(),
            "tepkiler": set(),
        }
    return _tracker[discord_id]


def bugunun_gorevi(discord_id: int, ek: bool = False) -> dict:
    """
    ek=False → normal görev
    ek=True  → 2. görev (farklı seed, ana görevle çakışmaz)
    Görev Yenile perki kullanıldıysa _yenileme sayacı artar → farklı görev çıkar.
    """
    _tracker_kontrol()
    bugun    = _bugun_tr().isoformat()
    yenileme = _yenileme.get(discord_id, 0)
    seed     = hash(f"{discord_id}_{bugun}_{yenileme}") % len(GOREVLER)

    if not ek:
        return GOREVLER[seed]

    # Ek görev: ana görevle aynı olmaması için farklı index seç
    ek_seed = hash(f"{discord_id}_{bugun}_ek_{yenileme}") % len(GOREVLER)
    if ek_seed == seed:
        ek_seed = (ek_seed + 1) % len(GOREVLER)
    return GOREVLER[ek_seed]


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
        bugun = _bugun_tr().isoformat()
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
                    ek_gorev     BOOLEAN DEFAULT FALSE,
                    created_at   TIMESTAMP DEFAULT NOW()
                )
            """)
            # Mevcut tabloya ek_gorev kolonu ekle (varsa atla)
            await conn.execute(
                "ALTER TABLE gunluk_gorev_log ADD COLUMN IF NOT EXISTS ek_gorev BOOLEAN DEFAULT FALSE"
            )
        log.info("Günlük görev tablosu hazır.")

    async def _aktif_gorev_al(self, discord_id: int) -> tuple[dict, bool]:
        """
        Kullanıcının şu an aktif görevini döndürür.
        ek_hak=True ve ana görev tamamlandıysa ek görevi döndürür.
        Returns: (gorev, ek_mi)
        """
        bugun  = _bugun_tr().isoformat()
        ek_hak = await database.perk_haftalik_limit_kontrol(discord_id, "gunluk_gorev_satin_al")

        if ek_hak:
            async with database.pool.acquire() as conn:
                ana = await conn.fetchrow(
                    """SELECT durum FROM gunluk_gorev_log
                       WHERE discord_id=$1 AND tarih=$2 AND ek_gorev=FALSE
                       ORDER BY id DESC LIMIT 1""", discord_id, bugun)
                ana_tamam = ana and ana["durum"] in ("tamamlandi", "onaylandi")
                if ana_tamam:
                    ek = await conn.fetchrow(
                        """SELECT durum FROM gunluk_gorev_log
                           WHERE discord_id=$1 AND tarih=$2 AND ek_gorev=TRUE
                           ORDER BY id DESC LIMIT 1""", discord_id, bugun)
                    ek_tamam = ek and ek["durum"] in ("tamamlandi", "onaylandi")
                    if not ek_tamam:
                        return bugunun_gorevi(discord_id, ek=True), True

        return bugunun_gorevi(discord_id, ek=False), False

    # ── Event: mesaj ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gorev, ek = await self._aktif_gorev_al(message.author.id)
        t = _t(message.author.id)

        if gorev["id"] == "mesaj_25":
            t["mesajlar"].add(message.id)
            if len(t["mesajlar"]) == 25:
                await self._tamamla(message.author, message.guild, gorev, ek=ek)

        elif gorev["id"] == "yanit_25" and message.reference:
            ref = message.reference.resolved
            if ref and hasattr(ref, "author") and ref.author.id != message.author.id:
                t["yanitlar"].add(ref.author.id)
                if len(t["yanitlar"]) == 25:
                    await self._tamamla(message.author, message.guild, gorev, ek=ek)

    # ── Event: tepki ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user):
        if user.bot or not reaction.message.guild:
            return
        gorev, ek = await self._aktif_gorev_al(user.id)
        if gorev["id"] != "tepki_25":
            return
        t = _t(user.id)
        if reaction.message.author.id != user.id:
            t["tepkiler"].add(reaction.message.id)
            if len(t["tepkiler"]) == 25:
                member = reaction.message.guild.get_member(user.id)
                if member:
                    await self._tamamla(member, reaction.message.guild, gorev, ek=ek)

    # ── Rol kontrol ────────────────────────────────────────────
    async def _rol_kontrol(self, member: discord.Member, guild: discord.Guild):
        sayi = await database.get_lifetime_gorev_sayisi(member.id)
        for esik, rol_id in ROL_ESIKLERI.items():
            if sayi >= esik and rol_id:
                rol = guild.get_role(rol_id)
                if rol and rol not in member.roles:
                    try:
                        await member.add_roles(rol, reason=f"Günlük görev: {sayi} görev tamamlandı")
                        log.info(f"Rol verildi: {member} → {rol.name}")
                    except discord.Forbidden:
                        log.warning(f"Rol verilemedi (yetki): {member} → {rol.name}")
                    except Exception as e:
                        log.error(f"Rol verme hatası: {e}")

        # Luminary kalıcı bonus (sadece bir kez)
        if sayi >= 12:
            async with database.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE coins SET luminary_bonus=5 WHERE discord_id=$1 AND luminary_bonus=0",
                    member.id
                )

    # ── Görev tamamlama ────────────────────────────────────────
    async def _tamamla(self, member: discord.Member, guild: discord.Guild, gorev: dict, ek: bool = False):
        bugun = _bugun_tr().isoformat()

        # Görev Takviyesi perki aktif mi?
        takviye = await database.get_aktif_perk(member.id, "gorev_takviyesi")
        efektif_odul = gorev["odul"] + (10 if takviye and gorev["tur"] != "admin" else 0)

        async with database.pool.acquire() as conn:
            mevcut = await conn.fetchval(
                """SELECT id FROM gunluk_gorev_log
                   WHERE discord_id=$1 AND gorev_id=$2 AND tarih=$3 AND durum='tamamlandi' AND ek_gorev=$4""",
                member.id, gorev["id"], bugun, ek)
            if mevcut:
                return

            await conn.execute(
                """INSERT INTO gunluk_gorev_log
                   (discord_id, isim, gorev_id, gorev_baslik, durum, tarih, odul, ek_gorev)
                   VALUES ($1,$2,$3,$4,'tamamlandi',$5,$6,$7)
                   ON CONFLICT DO NOTHING""",
                member.id, member.display_name,
                gorev["id"], gorev["baslik"], bugun, efektif_odul, ek)

            yeni = await database.add_coins(
                member.id, member.display_name, efektif_odul,
                aciklama=f"Günlük görev: {gorev['baslik']}")

        # Rol kontrolü
        await self._rol_kontrol(member, guild)

        takviye_satir = f"\n⚡ **Görev Takviyesi:** +10 bonus coin!" if takviye and gorev["tur"] != "admin" else ""
        try:
            await member.send(
                f"{OK} **Günlük görevin tamamlandı!**\n"
                f"**{gorev['baslik']}**\n\n"
                f"{COIN_ANIM} **+{efektif_odul} M2B Coin** hesabına eklendi!{takviye_satir}\n"
                f"Yeni bakiyen: **{yeni} M2B Coin**")
        except Exception:
            pass
        log.info(f"Görev tamamlandı: {member} → {gorev['id']} +{efektif_odul} coin")

    # ── /günlük-görev komutu ──────────────────────────────────
    @app_commands.command(name="günlük-görev", description="Bugünkü görevini görüntüle.")
    async def gunluk_gorev(self, interaction: discord.Interaction):
        uid   = interaction.user.id
        bugun = _bugun_tr().isoformat()

        # Ek görev hakkı kontrolü
        ek_hak = await database.perk_haftalik_limit_kontrol(uid, "gunluk_gorev_satin_al")

        async with database.pool.acquire() as conn:
            # Ana görev kaydı
            ana_kayit = await conn.fetchrow(
                """SELECT durum, gorev_id FROM gunluk_gorev_log
                   WHERE discord_id=$1 AND tarih=$2 AND ek_gorev=FALSE
                   ORDER BY id DESC LIMIT 1""",
                uid, bugun)
            # Ek görev kaydı
            ek_kayit = await conn.fetchrow(
                """SELECT durum, gorev_id FROM gunluk_gorev_log
                   WHERE discord_id=$1 AND tarih=$2 AND ek_gorev=TRUE
                   ORDER BY id DESC LIMIT 1""",
                uid, bugun) if ek_hak else None

        ana_tamamlandi = ana_kayit and ana_kayit["durum"] in ("tamamlandi", "onaylandi", "bekliyor")
        ek_tamamlandi  = ek_kayit  and ek_kayit["durum"]  in ("tamamlandi", "onaylandi", "bekliyor")

        # Hangi görevi göstereceğimizi belirle
        # Ek görev hakkı var VE ana görev tamamlandı VE ek görev henüz yapılmadıysa → ek görevi göster
        goster_ek = ek_hak and ana_tamamlandi and not ek_tamamlandi
        gorev     = bugunun_gorevi(uid, ek=goster_ek)
        tamamlandi = ek_tamamlandi if goster_ek else ana_tamamlandi

        embed = discord.Embed(
            title=f"{BILDIRIM}  {'Ek Günlük Görev' if goster_ek else 'Günlük Görev'}",
            color=0x95A5A6 if tamamlandi else (0xFFD700 if goster_ek else 0x2ECC71))
        embed.add_field(name="Görev",    value=f"**{gorev['baslik']}**", inline=False)
        embed.add_field(name="Açıklama", value=gorev["aciklama"],        inline=False)

        if gorev["id"] == "oy_ver":
            embed.add_field(name="Ödül", value="🎟️ 100 MP Kuponu", inline=True)
        else:
            embed.add_field(name="Ödül", value=f"{COIN_ANIM} {gorev['odul']} M2B Coin", inline=True)

        if goster_ek:
            embed.add_field(name="💎 Ek Görev", value="Gem Mağazası'ndan satın alınan ek görev hakkı!", inline=False)

        if tamamlandi:
            kayit = ek_kayit if goster_ek else ana_kayit
            durum_txt = {"tamamlandi": "✅ Tamamlandı", "onaylandi": "✅ Onaylandı", "bekliyor": "⏳ Onay Bekliyor"}
            embed.add_field(name="Durum", value=durum_txt.get(kayit["durum"], "✅"), inline=True)
            # Ana da ek de tamamlandıysa bilgi ver
            if ana_tamamlandi and ek_tamamlandi:
                embed.set_footer(text="Bugün hem ana hem ek görevini tamamladın! 🎉")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if gorev["tur"] == "otomatik":
            mevcut, hedef = _ilerleme(uid, gorev["id"])
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
