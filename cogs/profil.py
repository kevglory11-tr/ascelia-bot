"""
cogs/profil.py — /profil, /profil-duzenle, /rozet-sec, /profil-magazasi komutları.
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

GEM  = "💎"
OK   = "<a:olumlutick:1478524954688356494>"
FAIL = "❌"

log = setup_logger("profil")

EXP_MESAJ_MIN   = 5
EXP_MESAJ_MAX   = 15
EXP_COOLDOWN_SN = 60

_BANNERS = "assets/banners"
ARKA_PLAN_URL_MAP: dict[str, str | None] = {
    # aktif arka planlar
    "varsayilan":     None,
    "gojo_statik":    f"{_BANNERS}/mor.jpg",
    "gojo_hareketli": f"{_BANNERS}/mor.gif",
    # eski renk ID'leri — backward compat, mağazada gösterilmez
    "mor":    f"{_BANNERS}/mor.gif",
    "kirmizi": f"{_BANNERS}/kirmizi.jpg",
    "mavi":    f"{_BANNERS}/mavi.jpg",
    "altin":   f"{_BANNERS}/altin.jpg",
    "zumrut":  f"{_BANNERS}/zumrut.jpg",
    "gunes":   f"{_BANNERS}/gunes.jpg",
    "galaksi": f"{_BANNERS}/galaksi.jpg",
    "ejder":   f"{_BANNERS}/ejder.jpg",
    "efsane":  f"{_BANNERS}/efsane.jpg",
}

_TUM_AP: dict[str, dict] = {ap["id"]: ap for ap in PROFIL_ARKA_PLANLAR}

# Eski renk ID'leri için fallback renk/isim (mağazada görünmez ama /profil'de kullanılır)
_LEGACY_AP: dict[str, dict] = {
    "mor":     {"renk": "6c3483", "isim": "Gojo"},
    "kirmizi": {"renk": "922b21", "isim": "Kirmizi"},
    "mavi":    {"renk": "1a5276", "isim": "Mavi"},
    "altin":   {"renk": "9a7d0a", "isim": "Altin"},
    "zumrut":  {"renk": "1e8449", "isim": "Zumrut"},
    "gunes":   {"renk": "ca6f1e", "isim": "Gunes"},
    "galaksi": {"renk": "4a235a", "isim": "Galaksi"},
    "ejder":   {"renk": "641e16", "isim": "Ejder"},
    "efsane":  {"renk": "784212", "isim": "Efsane"},
}


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _tum_rozetler() -> list:
    return OZEL_ROZETLER + ROZET_MAGAZA


def _arka_plan_renk(ap_id: str) -> str:
    if ap := _TUM_AP.get(ap_id):
        return ap["renk"]
    if ap := _LEGACY_AP.get(ap_id):
        return ap["renk"]
    return "2b2d31"


def _arka_plan_isim(ap_id: str) -> str:
    if ap := _TUM_AP.get(ap_id):
        return ap["isim"]
    if ap := _LEGACY_AP.get(ap_id):
        return ap["isim"]
    return "Varsayilan"


def _avatar_url(member: discord.Member) -> str:
    av = member.display_avatar
    if av.is_animated():
        return str(av.replace(format="gif").url)
    return str(av.url)


# ── Embed yardımcıları ────────────────────────────────────────────────────────

def _magazasi_embed(gems: int, mevcut: str) -> discord.Embed:
    return discord.Embed(
        title="🖼️ Profil Mağazası",
        description=(
            "Mağazadaki içerikleri satın alarak profilini özelleştirebilirsin.\n\n"
            f"{GEM} Bakiye: **{gems} Gem**\n"
            f"Aktif: **{_arka_plan_isim(mevcut)}**"
        ),
        color=0x7B2FBE,
    )


def _kategori_embed(baslik: str, gems: int, mevcut: str) -> discord.Embed:
    return discord.Embed(
        title=baslik,
        description=(
            f"{GEM} Bakiye: **{gems} Gem**\n"
            f"Aktif: **{_arka_plan_isim(mevcut)}**"
        ),
        color=0x7B2FBE,
    )


# ── SelectOption üretici ──────────────────────────────────────────────────────

def _ap_option(ap: dict, mevcut: str, gems: int, owned: list[str]) -> discord.SelectOption:
    aktif    = ap["id"] == mevcut
    is_owned = ap["fiyat"] == 0 or ap["id"] in owned

    if aktif:
        desc = "✅ Aktif"
    elif is_owned:
        desc = "Sahip ✓"
    else:
        desc = f"{ap['fiyat']} 💎"
        if gems < ap["fiyat"]:
            desc += " — Yetersiz"

    return discord.SelectOption(
        label=(f"✅ {ap['isim']}" if aktif else ap["isim"])[:100],
        description=desc[:100],
        value=ap["id"],
        emoji=ap["emoji"],
        default=aktif,
    )


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

    # ── /profil-magazasi ───────────────────────────────────────────────────────

    @app_commands.command(name="profil-magazasi", description="Profil arka plan mağazası.")
    async def profil_magazasi(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid    = interaction.user.id
        await database.ensure_user(uid, interaction.user.display_name)
        gems   = await database.get_gem_bakiye(uid)
        kayit  = await database.get_user(uid)
        mevcut = kayit["profil_arka_plan"] or "varsayilan"
        owned  = await database.get_sahip_arka_planlar(uid)

        embed = _magazasi_embed(gems, mevcut)
        view  = ArkaPlanMainView(uid, gems, mevcut, owned)
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


# ── Mağaza UI ─────────────────────────────────────────────────────────────────

class ArkaPlanMainView(discord.ui.View):
    """Ana menü: Normal ve Gifli kategorisi butonları."""

    def __init__(self, discord_id: int, gems: int, mevcut: str, owned: list[str]):
        super().__init__(timeout=180)
        self.add_item(KategoriButton(
            label="🖼️ Normal Arka Planlar",
            arka_planlar=PROFIL_ARKA_PLANLAR_STATIK,
            discord_id=discord_id, gems=gems, mevcut=mevcut, owned=owned,
        ))
        self.add_item(KategoriButton(
            label="✨ Gifli Arka Planlar",
            arka_planlar=PROFIL_ARKA_PLANLAR_HAREKETLI,
            discord_id=discord_id, gems=gems, mevcut=mevcut, owned=owned,
        ))


class KategoriButton(discord.ui.Button):
    def __init__(self, label: str, arka_planlar: list, discord_id: int,
                 gems: int, mevcut: str, owned: list[str]):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.arka_planlar = arka_planlar
        self.discord_id   = discord_id
        self.gems         = gems
        self.mevcut       = mevcut
        self.owned        = owned

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return
        embed = _kategori_embed(self.label, self.gems, self.mevcut)
        view  = ArkaPlanKategoriView(
            self.arka_planlar, self.label,
            self.discord_id, self.gems, self.mevcut, self.owned,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ArkaPlanKategoriView(discord.ui.View):
    """Kategori menüsü: Select + Geri butonu."""

    def __init__(self, arka_planlar: list, baslik: str, discord_id: int,
                 gems: int, mevcut: str, owned: list[str]):
        super().__init__(timeout=180)
        self.add_item(ArkaPlanSelect(arka_planlar, baslik, discord_id, gems, mevcut, owned))
        self.add_item(GeriButton(discord_id, gems, mevcut, owned))


class ArkaPlanSelect(discord.ui.Select):
    def __init__(self, arka_planlar: list, baslik: str, discord_id: int,
                 gems: int, mevcut: str, owned: list[str]):
        self.arka_planlar = arka_planlar
        self.baslik       = baslik
        self.discord_id   = discord_id
        self.gems         = gems
        self.mevcut       = mevcut
        self.owned        = owned
        options = [_ap_option(ap, mevcut, gems, owned) for ap in arka_planlar]
        super().__init__(placeholder="Arka plan seç...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu sana ait değil!", ephemeral=True)
            return

        secim = self.values[0]
        ap    = _TUM_AP[secim]
        is_owned = ap["fiyat"] == 0 or secim in self.owned

        new_gems  = self.gems
        new_owned = list(self.owned)

        if not is_owned:
            ok, new_gems = await _satin_al_gem(self.discord_id, ap)
            if not ok:
                await interaction.response.send_message(
                    f"{FAIL} Yetersiz Gem!\n"
                    f"Gerekli: **{ap['fiyat']} {GEM}** — Bakiyen: **{self.gems} {GEM}**",
                    ephemeral=True,
                )
                return
            await database.add_sahip_arka_plan(self.discord_id, secim)
            new_owned.append(secim)

        await database.update_profil(self.discord_id, profil_arka_plan=secim)

        # Mesajı güncelle (yeni ownership/bakiye yansısın)
        embed = _kategori_embed(self.baslik, new_gems, secim)
        view  = ArkaPlanKategoriView(
            self.arka_planlar, self.baslik,
            self.discord_id, new_gems, secim, new_owned,
        )
        await interaction.response.edit_message(embed=embed, view=view)

        if is_owned:
            bilgi = f"✅ **{ap['isim']}** aktif arka plan olarak seçildi!"
        else:
            bilgi = f"✅ **{ap['isim']}** satın alındı ve aktif edildi! ({ap['fiyat']} {GEM} harcandı)"
        await interaction.followup.send(bilgi, ephemeral=True)


class GeriButton(discord.ui.Button):
    def __init__(self, discord_id: int, gems: int, mevcut: str, owned: list[str]):
        super().__init__(label="← Geri", style=discord.ButtonStyle.secondary)
        self.discord_id = discord_id
        self.gems       = gems
        self.mevcut     = mevcut
        self.owned      = owned

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return
        embed = _magazasi_embed(self.gems, self.mevcut)
        view  = ArkaPlanMainView(self.discord_id, self.gems, self.mevcut, self.owned)
        await interaction.response.edit_message(embed=embed, view=view)


# ── Rozet UI ─────────────────────────────────────────────────────────────────

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


# ── Satın alma ────────────────────────────────────────────────────────────────

async def _satin_al_gem(discord_id: int, ap: dict) -> tuple[bool, int]:
    ok    = await database.remove_gem(discord_id, ap["fiyat"], tip="arka_plan", aciklama=f"Arka plan: {ap['isim']}")
    kalan = await database.get_gem_bakiye(discord_id)
    return ok, kalan


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfilCog(bot))
