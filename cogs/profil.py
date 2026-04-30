"""
cogs/profil.py — /profil, /profil-duzenle, /rozet-sec komutları.
EXP sistemi (mesaj başına) + dinamik profil kartı görsel üretimi.
"""

import io
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
import random

import database
from utils.logger import setup_logger
from utils.profil_karti import profil_karti_olustur
from config.coin_settings import OZEL_ROZETLER, PROFIL_ARKA_PLANLAR, ROZET_MAGAZA

def _tum_rozetler() -> list:
    return OZEL_ROZETLER + ROZET_MAGAZA

M2B  = "<:m2bcoin:1480481551337783437>"
OK   = "<a:olumlutick:1478524954688356494>"
FAIL = "❌"

log = setup_logger("profil")

EXP_MESAJ_MIN   = 5
EXP_MESAJ_MAX   = 15
EXP_COOLDOWN_SN = 60

# Arka plan URL haritası — buraya istediğin oyun görsellerini ekle
ARKA_PLAN_URL_MAP: dict[str, str] = {
    "varsayilan": None,
    "kirmizi":    "https://i.imgur.com/8iMhMaS.png",
    "mavi":       "https://i.imgur.com/Qzf7OK5.png",
    "mor":        "https://i.imgur.com/VG2tSXm.png",
    "altin":      "https://i.imgur.com/nSuDFBv.png",
    "zumrut":     "https://i.imgur.com/jMhXEqJ.png",
    "gunes":      "https://i.imgur.com/8iMhMaS.png",
    "galaksi":    "https://i.imgur.com/Qzf7OK5.png",
    "ejder":      "https://i.imgur.com/VG2tSXm.png",
    "efsane":     "https://i.imgur.com/nSuDFBv.png",
}


def _arka_plan_renk(ap_id: str) -> str:
    ap = next((a for a in PROFIL_ARKA_PLANLAR if a["id"] == ap_id), None)
    return ap["renk"] if ap else "2b2d31"


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

            arka_plan_url = ARKA_PLAN_URL_MAP.get(ap_id)
            avatar_url    = str(hedef.display_avatar.url)

            # Profil kartı görsel üret
            try:
                buf = await profil_karti_olustur(
                    kullanici_adi  = hedef.display_name,
                    avatar_url     = avatar_url,
                    level          = level,
                    exp            = exp,
                    gereken_exp    = gereken,
                    bakiye         = bakiye,
                    siralama       = sira,
                    aktif_rozet    = aktif_rozet_isim,
                    arka_plan_url  = arka_plan_url,
                    renk_hex       = renk,
                    bio            = kayit["profil_bio"],
                )
                dosya = discord.File(buf, filename="profil.png")
            except Exception as e:
                log.error(f"Kart üretimi başarısız: {e}", exc_info=True)
                dosya = None

            # Rozet listesi (embed olarak aşağı ekle)
            rozet_listesi = await database.get_rozet_listesi(hedef.id)
            kostumler     = await database.get_costumes(hedef.id)

            embed = discord.Embed(color=int(renk, 16) if renk else 0x2b2d31)
            if dosya:
                embed.set_image(url="attachment://profil.png")

            if rozet_listesi:
                tum = [r["isim"] for r in _tum_rozetler() if r["id"] in rozet_listesi]
                satirlar = []
                toplam   = 0
                for isim in tum:
                    satir = f"🏅 {isim}"
                    if toplam + len(satir) + 1 > 1000:
                        satirlar.append(f"_...ve {len(tum) - len(satirlar)} tane daha_")
                        break
                    satirlar.append(satir)
                    toplam += len(satir) + 1
                embed.add_field(
                    name=f"🏅 Rozetler ({len(tum)}/{len(_tum_rozetler())})",
                    value="\n".join(satirlar),
                    inline=False,
                )

            if kostumler:
                son3 = [f"{k['costume_name']} `{k['rarity']}`" for k in kostumler[:5]]
                embed.add_field(
                    name=f"🎭 Kostümler ({len(kostumler)} adet)",
                    value="\n".join(son3),
                    inline=False,
                )

            if dosya:
                await interaction.followup.send(file=dosya, embed=embed)
            else:
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
        uid   = interaction.user.id
        kayit = await database.ensure_user(uid, interaction.user.display_name)
        bakiye = kayit["bakiye"]
        mevcut = kayit["profil_arka_plan"] or "varsayilan"

        embed = discord.Embed(
            title="🖼️ Profil Arka Planı",
            description=(
                f"Arka plan profil kartına yansır.\n"
                f"{M2B} Bakiyen: **{bakiye:,} Coin**\n"
                f"Mevcut: **{next((a['isim'] for a in PROFIL_ARKA_PLANLAR if a['id'] == mevcut), mevcut)}**"
            ),
            color=0x7B2FBE,
        )
        for ap in PROFIL_ARKA_PLANLAR:
            aktif  = " ✅" if ap["id"] == mevcut else ""
            fiyat  = "Ücretsiz" if ap["fiyat"] == 0 else f"{ap['fiyat']:,} {M2B}"
            kilit  = "" if bakiye >= ap["fiyat"] else " 🔒"
            embed.add_field(
                name=f"{ap['emoji']} {ap['isim']}{aktif}",
                value=f"{fiyat}{kilit}",
                inline=True,
            )

        view = ArkaPlanView(uid, bakiye, mevcut)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ── /rozet-sec ─────────────────────────────────────────────────────────────

    @app_commands.command(name="rozet-sec", description="Profilinde gösterilecek aktif rozeti seç.")
    async def rozet_sec(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            sahip = await database.get_rozet_listesi(interaction.user.id)
            if not sahip:
                await interaction.followup.send(
                    "Henüz rozet sahibi değilsin! `/market` → Rozet Mağazası'ndan satın alabilirsin.", ephemeral=True
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


class ArkaPlanSelect(discord.ui.Select):
    def __init__(self, discord_id: int, bakiye: int, mevcut: str):
        self.discord_id = discord_id
        options = []
        for ap in PROFIL_ARKA_PLANLAR:
            aktif = ap["id"] == mevcut
            fiyat_txt = "Ücretsiz" if ap["fiyat"] == 0 else f"{ap['fiyat']:,} Coin"
            if bakiye < ap["fiyat"] and not aktif:
                fiyat_txt += " — Yetersiz bakiye"
            label = f"{'✅ ' if aktif else ''}{ap['isim']}"
            options.append(discord.SelectOption(
                label=label[:100],
                description=fiyat_txt,
                value=ap["id"],
                emoji=ap["emoji"],
                default=aktif,
            ))
        super().__init__(placeholder="Arka plan seç...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return

        secim = self.values[0]
        ap    = next(a for a in PROFIL_ARKA_PLANLAR if a["id"] == secim)
        await interaction.response.defer(ephemeral=True)

        if ap["fiyat"] > 0:
            ok = await database.remove_coins(
                self.discord_id, ap["fiyat"], aciklama=f"Arka plan: {ap['isim']}"
            )
            if not ok:
                kayit = await database.get_user(self.discord_id)
                bakiye = kayit["bakiye"] if kayit else 0
                await interaction.followup.send(
                    f"{FAIL} Yetersiz coin!\nGerekli: **{ap['fiyat']:,}** — Bakiyen: **{bakiye:,}**",
                    ephemeral=True,
                )
                return

        await database.update_profil(self.discord_id, profil_arka_plan=secim)

        embed = discord.Embed(
            title=f"{OK} Arka Plan Güncellendi!",
            description=(
                f"{ap['emoji']} **{ap['isim']}** seçildi."
                + (f"\n{M2B} **{ap['fiyat']:,} Coin** harcandı." if ap["fiyat"] > 0 else "")
                + "\n\n`/profil` ile kontrol edebilirsin."
            ),
            color=int(ap["renk"], 16),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class ArkaPlanView(discord.ui.View):
    def __init__(self, discord_id: int, bakiye: int, mevcut: str):
        super().__init__(timeout=120)
        self.add_item(ArkaPlanSelect(discord_id, bakiye, mevcut))


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
        rozet = next((r for r in OZEL_ROZETLER if r["id"] == self.values[0]), None)
        await interaction.followup.send(
            f"✅ **{rozet['isim']}** aktif rozet olarak seçildi!", ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfilCog(bot))
