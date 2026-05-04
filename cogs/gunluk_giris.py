"""cogs/gunluk_giris.py — /günlük-giriş komutu."""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta

import database
from utils.logger import setup_logger
from config.coin_settings import GUNLUK_COIN

log       = setup_logger("gunluk_giris")
TR_OFFSET = timedelta(hours=3)
M2B       = "<:m2bcoin:1480481551337783437>"
OK        = "<a:check:1478394670856933429>"
FAIL      = "❌"
COIN_ANIM = "<a:coin:1478390167310958734>"


def _bugun_tr() -> str:
    return (datetime.now(timezone.utc) + TR_OFFSET).strftime("%Y-%m-%d")


def _seri_bonusu(seri: int) -> tuple[int, str]:
    """(bonus_miktar, açıklama) döndürür."""
    if seri == 7:
        return 5, "🎉 **1. hafta tamamlandı!** +5 Coin bonus!"
    elif seri >= 14:
        return 10, "🏆 **2+ hafta serisi!** +10 Coin bonus!"
    return 0, ""


class GunlukGirisCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _gunluk_giris(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            kayit  = await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bugun  = _bugun_tr()
            son    = str(kayit["son_giris"]) if kayit["son_giris"] else None

            if son == bugun:
                embed = discord.Embed(
                    title=f"{FAIL} Bugünkü Ödülünü Zaten Aldın!",
                    description=(
                        f"Yarın **00:00 TR** saatinde tekrar kullanabilirsin.\n\n"
                        f"{M2B} Bakiyen: **{kayit['bakiye']:,} M2B Coin**"
                    ),
                    color=0xE74C3C,
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                await interaction.followup.send(embed=embed)
                return

            coin      = GUNLUK_COIN
            yeni_seri = await database.set_son_giris(interaction.user.id, bugun)

            # Haftalık seri bonusu
            seri_bonus, seri_mesaj = _seri_bonusu(yeni_seri)

            # Luminary kalıcı bonusu
            user_row       = await database.get_user(interaction.user.id)
            luminary_bonus = user_row["luminary_bonus"] if user_row and "luminary_bonus" in user_row.keys() else 0

            # Giriş Takviyesi perki
            giris_takviyesi = await database.get_aktif_perk(interaction.user.id, "giris_takviyesi")
            perk_bonus      = 5 if giris_takviyesi else 0

            toplam      = coin + seri_bonus + luminary_bonus + perk_bonus
            yeni_bakiye = await database.add_coins(
                interaction.user.id, interaction.user.display_name, toplam,
                aciklama=f"Günlük giriş (seri: {yeni_seri})"
            )

            # Açıklama satırları
            satirlar = [f"{COIN_ANIM} {interaction.user.mention} **{coin} M2B Coin** kazandı!"]
            if seri_mesaj:
                satirlar.append(seri_mesaj)
            if luminary_bonus > 0:
                satirlar.append(f"👑 **Luminary bonusu:** +{luminary_bonus} Coin")
            if perk_bonus > 0:
                satirlar.append(f"☀️ **Giriş Takviyesi perki:** +{perk_bonus} Coin")
            satirlar.append(f"\n{M2B} Yeni bakiyen: **{yeni_bakiye:,} M2B Coin**")
            satirlar.append(f"🔥 Giriş seriniz: **{yeni_seri} gün**")
            satirlar.append("📅 Yarın tekrar gel!")

            embed = discord.Embed(
                title=f"{OK} Günlük Giriş Ödülü!",
                description="\n".join(satirlar),
                color=0x2ECC71,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="/bakiye · /market · /günlük-görev · /gem-mağaza")
            await interaction.followup.send(embed=embed)
            log.info(f"Günlük: {interaction.user} → +{toplam} coin (seri: {yeni_seri})")

        except Exception as e:
            log.error(f"günlük-giriş hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)

    @app_commands.command(name="günlük-giriş", description="Günlük 50 M2B Coin kazan!")
    async def gunluk_giris(self, interaction: discord.Interaction):
        await self._gunluk_giris(interaction)

    @app_commands.command(name="günlük", description="Günlük 50 M2B Coin kazan!")
    async def gunluk(self, interaction: discord.Interaction):
        await self._gunluk_giris(interaction)

    @app_commands.command(name="streak", description="Günlük giriş serinizi görüntüle.")
    async def streak(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            kayit = await database.get_user(interaction.user.id)
            if not kayit:
                await interaction.followup.send(
                    "Henüz giriş kaydın yok. `/günlük-giriş` kullanarak başla!",
                    ephemeral=True)
                return

            seri   = kayit["giris_serisi"] or 0
            maks   = (kayit["giris_serisi_max"] if "giris_serisi_max" in kayit.keys() else 0) or 0
            son    = str(kayit["son_giris"]) if kayit["son_giris"] else None
            koruma = await database.get_aktif_perk(interaction.user.id, "seri_koruma")

            # Tier: (min_seri, ikon, isim, renk)
            TIERLER = [
                (100, "👑", "Ölümsüz",    0xFFD700),
                (60,  "💜", "Titan",      0x9B59B6),
                (30,  "🧡", "Efsanevi",   0xE67E22),
                (21,  "💛", "Sürekli",    0xF1C40F),
                (14,  "💚", "Kararlı",    0x2ECC71),
                (7,   "💙", "Devam Eden", 0x3498DB),
                (1,   "🤍", "Başlangıç",  0x95A5A6),
                (0,   "💤", "Başlamadı",  0x2C3E50),
            ]
            tier_ikon, tier_isim, tier_renk = "💤", "Başlamadı", 0x2C3E50
            for esik, ikon, isim, renk in TIERLER:
                if seri >= esik:
                    tier_ikon, tier_isim, tier_renk = ikon, isim, renk
                    break

            # Aktif bonus
            if seri >= 14:
                bonus_txt = "+10 coin (her giriş)"
            elif seri >= 7:
                bonus_txt = "+5 coin (bu giriş)"
            else:
                kalan_7 = 7 - seri
                bonus_txt = f"Yok — **{kalan_7} gün** sonra +5 coin"

            # Giriş durumu & geri sayım (TR saati)
            now_tr = datetime.now(timezone.utc) + TR_OFFSET
            bugun  = now_tr.date().isoformat()
            yarin  = now_tr.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            kalan  = yarin - now_tr
            k_saat = int(kalan.total_seconds() // 3600)
            k_dk   = int(kalan.total_seconds() % 3600 // 60)

            if son == bugun:
                durum_satir = f"✅ Bugün girildi\n⏳ Yenileniyor: **{k_saat}s {k_dk}dk**"
            elif seri > 0:
                durum_satir = f"⚠️ **Bugün giriş yap!**\n⏳ Süresi dolacak: **{k_saat}s {k_dk}dk**"
            else:
                durum_satir = "❌ `/günlük-giriş` ile seri başlat!"

            if koruma:
                durum_satir += "\n🛡️ **Seri Koruma** hazır!"

            # Milestone yol haritası
            MILESTONES = [
                (7,   "+5 Coin"),
                (14,  "+10 Coin/gün"),
                (21,  "Sürekli rozeti"),
                (30,  "Efsanevi rozeti"),
                (60,  "Titan rozeti"),
                (100, "👑 Ölümsüz"),
            ]
            yol = ""
            next_shown = False
            for i, (hedef, odul) in enumerate(MILESTONES):
                if seri >= hedef:
                    yol += f"✅ **{hedef} gün** — {odul}\n"
                elif not next_shown:
                    onceki   = MILESTONES[i - 1][0] if i > 0 else 0
                    aralik   = hedef - onceki
                    ilerleme = max(seri - onceki, 0)
                    dolu     = min(int(ilerleme / aralik * 8), 8)
                    bos      = 8 - dolu
                    kalan_g  = hedef - seri
                    yol += f"▶️ **{hedef} gün** — {odul}\n`{'█' * dolu}{'░' * bos}` {kalan_g} gün\n"
                    next_shown = True
                else:
                    yol += f"⬜ {hedef} gün — {odul}\n"

            embed = discord.Embed(
                title=f"{tier_ikon} Giriş Serisi — {tier_isim}",
                color=tier_renk,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(
                name="📊 Seri",
                value=(
                    f"🔥 Mevcut: **{seri} gün**\n"
                    f"🏆 Rekor: **{maks} gün**\n"
                    f"⚡ Bonus: {bonus_txt}"
                ),
                inline=True,
            )
            embed.add_field(
                name="⏰ Durum",
                value=durum_satir,
                inline=True,
            )
            embed.add_field(name="🎯 Yol Haritası", value=yol or "—", inline=False)
            embed.set_footer(text="Her gün /günlük-giriş yap, seriyi koru!")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            log.error(f"streak hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunlukGirisCog(bot))
