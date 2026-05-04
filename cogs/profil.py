"""
cogs/profil.py — /profil, /profil-duzenle, /rozet-sec, /arka-plan komutları.
EXP sistemi (mesaj başına) + dinamik profil kartı görsel üretimi.
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import random

import database
from utils.logger import setup_logger
from utils.profil_karti import profil_karti_olustur
from config.coin_settings import (
    OZEL_ROZETLER, ROZET_MAGAZA,
    PROFIL_ARKA_PLANLAR,
    PROFIL_ARKA_PLANLAR_STATIK,
    PROFIL_ARKA_PLANLAR_HAREKETLI,
)

# ── Sabitler ──────────────────────────────────────────────────────────────────

M2B  = "<:m2bcoin:1480481551337783437>"
GEM  = "💎"
OK   = "<a:olumlutick:1478524954688356494>"
FAIL = "❌"

log = setup_logger("profil")

EXP_MESAJ_MIN   = 5
EXP_MESAJ_MAX   = 15
EXP_COOLDOWN_SN = 60

_BANNERS = "assets/banners"
ARKA_PLAN_URL_MAP: dict[str, str | None] = {
    "varsayilan":     None,
    "kirmizi":        f"{_BANNERS}/kirmizi.jpg",
    "mavi":           f"{_BANNERS}/mavi.jpg",
    "mor":            f"{_BANNERS}/mor.gif",
    "altin":          f"{_BANNERS}/altin.jpg",
    "zumrut":         f"{_BANNERS}/zumrut.jpg",
    "gunes":          f"{_BANNERS}/gunes.jpg",
    "galaksi":        f"{_BANNERS}/galaksi.jpg",
    "ejder":          f"{_BANNERS}/ejder.jpg",
    "efsane":         f"{_BANNERS}/efsane.jpg",
    "gojo_statik":    f"{_BANNERS}/mor.jpg",
    "gojo_hareketli": f"{_BANNERS}/mor.gif",
}

# id → dict araması için hazır harita
_TUM_AP: dict[str, dict] = {ap["id"]: ap for ap in PROFIL_ARKA_PLANLAR}


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _tum_rozetler() -> list:
    return OZEL_ROZETLER + ROZET_MAGAZA


def _arka_plan_renk(ap_id: str) -> str:
    ap = _TUM_AP.get(ap_id)
    return ap["renk"] if ap else "2b2d31"


def _arka_plan_isim(ap_id: str) -> str:
    ap = _TUM_AP.get(ap_id)
    return ap["isim"] if ap else ap_id


def _avatar_url(member: discord.Member) -> str:
    """Animasyonlu avatar varsa GIF URL, yoksa varsayılan URL döndürür."""
    av = member.display_avatar
    if av.is_animated():
        return str(av.replace(format="gif").url)
    return str(av.url)


async def _satin_al(discord_id: int, ap: dict) -> tuple[bool, int]:
    """
    Arka plan için ödeme alır.
    Returns (başarılı, kalan_bakiye).
    """
    if ap.get("para_birimi") == "gem":
        ok    = await database.remove_gem(discord_id, ap["fiyat"], tip="arka_plan", aciklama=f"Arka plan: {ap['isim']}")
        kalan = await database.get_gem_bakiye(discord_id)
    else:
        ok    = await database.remove_coins(discord_id, ap["fiyat"], aciklama=f"Arka plan: {ap['isim']}")
        kayit = await database.get_user(discord_id)
        kalan = kayit["bakiye"] if kayit else 0
    return ok, kalan


# ── Cog ───────────────────────────────────────────────────────────────────────

class ProfilCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── EXP — mesaj dinleyici ─────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if len(message.content) < 3:
            return
        try:
            kayit = await database.ensure_user(message.author.id, message.author.display_name)
            son   = kayit["son_mesaj_exp"]
            if son:
                gecen = (datetime.now(timezone.utc) - son.replace(tzinfo=timezone.utc)).total_seconds()
                if gecen < EXP_COOLDOWN_SN:
                    return

            exp   = random.randint(EXP_MESAJ_MIN, EXP_MESAJ_MAX)
            sonuc = await database.add_exp(message.author.id, message.author.display_name, exp)

            async with database.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE coins SET son_mesaj_exp = NOW() WHERE discord_id = $1",
                    message.author.id,
                )

            if sonuc["level_up"]:
                try:
                    embed = discord.Embed(
                        title="🎉 Seviye Atladın!",
                        description=(
                            f"{message.author.mention} **Seviye {sonuc['level']}** oldu!\n"
                            f"💰 Ödül: **+{sonuc['coin_odulu']} M2B Coin**"
                        ),
                        color=0xffd700,
                    )
                    await message.channel.send(embed=embed, delete_after=10)
                except Exception:
                    pass
        except Exception as e:
            log.error(f"on_message EXP hatası: {e}", exc_info=True)

    # ── /profil ───────────────────────────────────────────────────────────────

    @app_commands.command(name="profil", description="Profil kartını görüntüle.")
    @app_commands.describe(kullanici="Başka birinin profiline bak (opsiyonel)")
    async def profil(self, interaction: discord.Interaction, kullanici: discord.Member = None):
        await interaction.response.defer()
        hedef = kullanici or interaction.user
        try:
            kayit = await database.ensure_user(hedef.id, hedef.display_name)

            level   = kayit["level"]
            exp     = kayit["exp"]
            gereken = database.exp_gereken(level)
            bakiye  = kayit["bakiye"]
            ap_id   = kayit["profil_arka_plan"] or "varsayilan"
            renk    = _arka_plan_renk(ap_id)

            async with database.pool.acquire() as conn:
                sira = await conn.fetchval(
                    "SELECT COUNT(*) + 1 FROM coins WHERE bakiye > $1", bakiye
                )

            aktif_rozet_isim = None
            if kayit["aktif_rozet"]:
                r = next((r for r in _tum_rozetler() if r["id"] == kayit["aktif_rozet"]), None)
                if r:
                    aktif_rozet_isim = r["isim"]

            try:
                buf, is_animated = await profil_karti_olustur(
                    kullanici_adi  = hedef.display_name,
                    avatar_url     = _avatar_url(hedef),
                    level          = level,
                    exp            = exp,
                    gereken_exp    = gereken,
                    bakiye         = bakiye,
                    siralama       = sira,
                    aktif_rozet    = aktif_rozet_isim,
                    arka_plan_url  = ARKA_PLAN_URL_MAP.get(ap_id),
                    renk_hex       = renk,
                    bio            = kayit["profil_bio"],
                )
                fname = "profil.gif" if is_animated else "profil.png"
                await interaction.followup.send(file=discord.File(buf, filename=fname))
            except Exception as e:
                log.error(f"Kart üretimi başarısız: {e}", exc_info=True)
                embed = discord.Embed(
                    title=f"{hedef.display_name} — Profil",
                    color=int(renk, 16) if renk else 0x2b2d31,
                    description=(
                        f"**Level:** {level}\n"
                        f"**Coins:** {bakiye:,}\n"
                        f"**Sıralama:** #{sira:,}"
                    ),
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            log.error(f"profil hatası: {e}", exc_info=True)
            await interaction.followup.send("Bir hata oluştu.", ephemeral=True)

    # ── /profil-duzenle ───────────────────────────────────────────────────────

    @app_commands.command(name="profil-duzenle", description="Profil biyografini düzenle.")
    @app_commands.describe(bio="Profil biyografin (max 100 karakter)")
    async def profil_duzenle(self, interaction: discord.Interaction, bio: str):
        if len(bio) > 100:
            await interaction.response.send_message("Bio en fazla 100 karakter olabilir!", ephemeral=True)
            return
        await database.ensure_user(interaction.user.id, interaction.user.display_name)
        await database.update_profil(interaction.user.id, profil_bio=bio)
        await interaction.response.send_message(f"✅ Bio güncellendi: *{bio}*", ephemeral=True)

    # ── /arka-plan ─────────────────────────────────────────────────────────────

    @app_commands.command(name="arka-plan", description="Profil kartı arka planını değiştir.")
    async def arka_plan(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid    = interaction.user.id
        kayit  = await database.ensure_user(uid, interaction.user.display_name)
        coins  = kayit["bakiye"]
        gems   = await database.get_gem_bakiye(uid)
        mevcut = kayit["profil_arka_plan"] or "varsayilan"

        embed = discord.Embed(
            title="🖼️ Profil Arka Planı",
            description=(
                "Mağazadaki içerikleri satın alarak profilini özelleştirebilirsin.\n"
                "Hareketli ve Hareketsiz arka planlar için aşağıdaki menüyü kullan.\n\n"
                f"{M2B} Bakiye: **{coins:,} Coin** · {GEM} **{gems} Gem**\n"
                f"Aktif: **{_arka_plan_isim(mevcut)}**"
            ),
            color=0x7B2FBE,
        )

        view = ArkaPlanView(uid, coins, gems, mevcut)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ── /rozet-sec ─────────────────────────────────────────────────────────────

    @app_commands.command(name="rozet-sec", description="Profilinde gösterilecek aktif rozeti seç.")
    async def rozet_sec(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            sahip = await database.get_rozet_listesi(interaction.user.id)
            if not sahip:
                await interaction.followup.send(
                    "Henüz rozet sahibi değilsin! `/market` → Rozet Mağazası'ndan satın alabilirsin.",
                    ephemeral=True,
                )
                return
            options = [
                discord.SelectOption(label=r["isim"], value=r["id"])
                for r in _tum_rozetler() if r["id"] in sahip
            ][:25]
            view = RozetSecView(interaction.user.id, options)
            await interaction.followup.send(
                "Aktif rozet olarak hangisini kullanmak istiyorsun?",
                view=view, ephemeral=True,
            )
        except Exception as e:
            log.error(f"rozet-sec hatası: {e}", exc_info=True)
            await interaction.followup.send("Bir hata oluştu.", ephemeral=True)


# ── UI Bileşenleri ────────────────────────────────────────────────────────────

def _ap_option(ap: dict, mevcut: str, coins: int, gems: int) -> discord.SelectOption:
    """Bir arka plan için SelectOption üretir, fiyat ve kilit bilgisini ekler."""
    aktif    = ap["id"] == mevcut
    is_gem   = ap.get("para_birimi") == "gem"
    birim    = "Gem" if is_gem else "Coin"
    kilitli  = not aktif and (gems < ap["fiyat"] if is_gem else coins < ap["fiyat"])

    if ap["fiyat"] == 0:
        fiyat_txt = "Ücretsiz"
    else:
        fiyat_txt = f"{ap['fiyat']} {birim}"
    if kilitli:
        fiyat_txt += " — Yetersiz"

    return discord.SelectOption(
        label=(f"✅ {ap['isim']}" if aktif else ap["isim"])[:100],
        description=fiyat_txt[:100],
        value=ap["id"],
        emoji=ap["emoji"],
        default=aktif,
    )


class ArkaPlanSelect(discord.ui.Select):
    """Coin veya Gem fiyatlı arka planları tek bir Select ile yönetir."""

    def __init__(
        self,
        discord_id:   int,
        coins:        int,
        gems:         int,
        mevcut:       str,
        arka_planlar: list,
        placeholder:  str,
    ):
        self.discord_id = discord_id
        options = [_ap_option(ap, mevcut, coins, gems) for ap in arka_planlar]
        super().__init__(placeholder=placeholder, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return

        secim = self.values[0]
        ap    = _TUM_AP[secim]
        await interaction.response.defer(ephemeral=True)

        if ap["fiyat"] > 0:
            ok, kalan = await _satin_al(self.discord_id, ap)
            if not ok:
                is_gem = ap.get("para_birimi") == "gem"
                birim  = "Gem" if is_gem else "Coin"
                await interaction.followup.send(
                    f"{FAIL} Yetersiz {birim}!\n"
                    f"Gerekli: **{ap['fiyat']} {birim}** — Bakiyen: **{kalan} {birim}**",
                    ephemeral=True,
                )
                return

        await database.update_profil(self.discord_id, profil_arka_plan=secim)

        if ap["fiyat"] > 0:
            is_gem   = ap.get("para_birimi") == "gem"
            sembol   = GEM if is_gem else M2B
            birim    = "Gem" if is_gem else "Coin"
            para_str = f"\n{sembol} **{ap['fiyat']} {birim}** harcandı."
        else:
            para_str = ""

        embed = discord.Embed(
            title=f"{OK} Arka Plan Güncellendi!",
            description=(
                f"{ap['emoji']} **{ap['isim']}** seçildi.{para_str}\n\n"
                "`/profil` ile kontrol edebilirsin."
            ),
            color=int(ap["renk"], 16),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class ArkaPlanView(discord.ui.View):
    def __init__(self, discord_id: int, coins: int, gems: int, mevcut: str):
        super().__init__(timeout=120)
        self.add_item(ArkaPlanSelect(
            discord_id, coins, gems, mevcut,
            PROFIL_ARKA_PLANLAR_STATIK,
            "Hareketsiz Arka Plan seç...",
        ))
        self.add_item(ArkaPlanSelect(
            discord_id, coins, gems, mevcut,
            PROFIL_ARKA_PLANLAR_HAREKETLI,
            "Hareketli Arka Plan seç...",
        ))


class RozetSecView(discord.ui.View):
    def __init__(self, discord_id: int, options: list):
        super().__init__(timeout=60)
        self.add_item(RozetSecSecim(discord_id, options))


class RozetSecSecim(discord.ui.Select):
    def __init__(self, discord_id: int, options: list):
        self.discord_id = discord_id
        super().__init__(placeholder="Rozet seç...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await database.set_aktif_rozet(interaction.user.id, self.values[0])
        rozet = next((r for r in _tum_rozetler() if r["id"] == self.values[0]), None)
        isim  = rozet["isim"] if rozet else self.values[0]
        await interaction.followup.send(f"✅ **{isim}** aktif rozet olarak seçildi!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfilCog(bot))
