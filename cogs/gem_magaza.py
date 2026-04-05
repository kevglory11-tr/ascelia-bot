"""cogs/gem_magaza.py — Gem Mağazası sistemi."""

import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import date

import database
from utils.logger import setup_logger
from config.coin_settings import GEM_COIN_KURU

log       = setup_logger("gem_magaza")
M2B       = "<:m2bcoin:1480481551337783437>"
GEM       = "💎"
OK        = "<a:olumlutick:1478524954688356494>"
FAIL_EMO  = "<a:no:1478524993670479942>"
COIN_ANIM = "<a:coin:1478390167310958734>"

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

PERKLER = {
    "gunluk_gorev_yenile": {
        "isim":      "Görev Yenile",
        "aciklama":  "Bugünkü günlük görevini değiştirir.",
        "maliyet":   5,
        "limit_turu": "haftalik",
        "sure_gun":  0,
        "patron":    False,
        "ikon":      "perk_gorev_yenile.png",
        "emoji":     "🔄",
    },
    "gunluk_gorev_satin_al": {
        "isim":      "Ek Görev Hakkı",
        "aciklama":  "Bugün için 1 ekstra görev hakkı kazanırsın.",
        "maliyet":   8,
        "limit_turu": "haftalik",
        "sure_gun":  0,
        "patron":    False,
        "ikon":      "perk_gorev_satin_al.png",
        "emoji":     "➕",
    },
    "giris_takviyesi": {
        "isim":      "Giriş Takviyesi",
        "aciklama":  "3 gün boyunca günlük girişe +5 Coin bonus.",
        "maliyet":   4,
        "limit_turu": "haftalik",
        "sure_gun":  3,
        "patron":    False,
        "ikon":      "perk_giris_takviyesi.png",
        "emoji":     "📈",
    },
    "gorev_takviyesi": {
        "isim":      "Görev Takviyesi",
        "aciklama":  "3 gün boyunca görev ödülüne +10 Coin (MP kuponu hariç).",
        "maliyet":   5,
        "limit_turu": "haftalik",
        "sure_gun":  3,
        "patron":    False,
        "ikon":      "perk_gorev_takviyesi.png",
        "emoji":     "⚡",
    },
    "patron_guclu_darbe": {
        "isim":      "Güçlü Darbe",
        "aciklama":  "Patron saldırısında +8 flat hasar.",
        "maliyet":   3,
        "limit_turu": "gunluk",
        "sure_gun":  0,
        "patron":    True,
        "ikon":      "perk_guclu_darbe.png",
        "emoji":     "💪",
    },
    "patron_kritik_sans": {
        "isim":      "Kritik Şans",
        "aciklama":  "%8 ekstra kritik vuruş ihtimali.",
        "maliyet":   3,
        "limit_turu": "gunluk",
        "sure_gun":  0,
        "patron":    True,
        "ikon":      "perk_kritik_sans.png",
        "emoji":     "🎯",
    },
    "patron_kritik_hasar": {
        "isim":      "Kritik Hasar",
        "aciklama":  "Kritik vuruşlarda ×1.15 ekstra hasar.",
        "maliyet":   3,
        "limit_turu": "gunluk",
        "sure_gun":  0,
        "patron":    True,
        "ikon":      "perk_kritik_hasar.png",
        "emoji":     "💥",
    },
    "patron_ekstra_saldiri": {
        "isim":      "Ekstra Saldırı",
        "aciklama":  "+1 saldırı hakkı (3 → 4).",
        "maliyet":   5,
        "limit_turu": "gunluk",
        "sure_gun":  0,
        "patron":    True,
        "ikon":      "perk_ekstra_saldiri.png",
        "emoji":     "⚔️",
    },
}


class PerkSatinAlButon(discord.ui.Button):
    def __init__(self, perk_id: str, perk: dict):
        super().__init__(
            label=f"{perk['isim']} ({perk['maliyet']} 💎)",
            emoji=perk.get("emoji", "🔹"),
            style=discord.ButtonStyle.primary,
            custom_id=f"perk_{perk_id}",
        )
        self.perk_id = perk_id
        self.perk    = perk

    async def callback(self, interaction: discord.Interaction):
        pid   = self.perk_id
        perk  = self.perk
        uid   = interaction.user.id

        # Perk ikonunu dosya olarak hazırla
        ikon_yolu = os.path.join(_ASSETS, perk["ikon"])
        ikon_dosya = None
        ikon_url   = None
        if os.path.exists(ikon_yolu):
            ikon_dosya = discord.File(ikon_yolu, filename=perk["ikon"])
            ikon_url   = f"attachment://{perk['ikon']}"

        await interaction.response.defer(ephemeral=True)

        # Limit kontrolü
        if perk["limit_turu"] == "haftalik":
            limit_doldu = await database.perk_haftalik_limit_kontrol(uid, pid)
        else:
            limit_doldu = await database.perk_gunluk_limit_kontrol(uid, pid)

        if limit_doldu:
            limit_txt = "Bu hafta" if perk["limit_turu"] == "haftalik" else "Bugün"
            await interaction.followup.send(
                f"{FAIL_EMO} **{limit_txt}** bu perki zaten satın aldın!", ephemeral=True)
            return

        # Aktif perk çakışması (süreli perkler)
        if perk["sure_gun"] > 0:
            aktif = await database.get_aktif_perk(uid, pid)
            if aktif:
                await interaction.followup.send(
                    f"{FAIL_EMO} Bu perk zaten aktif!", ephemeral=True)
                return

        # Gem bakiye kontrolü
        bakiye = await database.get_gem_bakiye(uid)
        if bakiye < perk["maliyet"]:
            await interaction.followup.send(
                f"{FAIL_EMO} Yetersiz Gem! Bakiyen: **{bakiye} {GEM}** — Gerekli: **{perk['maliyet']} {GEM}**",
                ephemeral=True)
            return

        # Gem düş
        ok = await database.remove_gem(uid, perk["maliyet"], tip="perk_satin_al",
                                       aciklama=perk["isim"])
        if not ok:
            await interaction.followup.send(f"{FAIL_EMO} İşlem başarısız, tekrar dene.", ephemeral=True)
            return

        # Perki kaydet
        await database.perk_satin_alma_kaydet(uid, pid)

        # Süreli perkse aktif_perk tablosuna yaz
        if perk["sure_gun"] > 0:
            bitis = await database.set_aktif_perk(uid, pid, sure_gun=perk["sure_gun"])
            bitis_str = bitis.strftime("%d.%m.%Y %H:%M")
            sure_txt  = f"\n⏳ **{perk['sure_gun']} gün** boyunca aktif.\nBitiş: `{bitis_str}`"
        else:
            sure_txt = ""

        # Görev Yenile — anlık etki (in-memory tracker'ı sıfırla + yenileme sayacını artır)
        if pid == "gunluk_gorev_yenile":
            from cogs.gunluk_gorev import _tracker, _yenileme
            if interaction.user.id in _tracker:
                del _tracker[interaction.user.id]
            _yenileme[interaction.user.id] = _yenileme.get(interaction.user.id, 0) + 1
            extra = "\n🔄 Günlük görevin yenilendi! `/günlük-görev` ile yeni görevini al."
        else:
            extra = ""

        yeni_bakiye = await database.get_gem_bakiye(uid)

        embed = discord.Embed(
            title=f"{OK} {perk['isim']} Satın Alındı!",
            description=(
                f"{perk['aciklama']}{sure_txt}{extra}\n\n"
                f"Kalan Gem: **{yeni_bakiye} {GEM}**"
            ),
            color=0x7B2FBE,
        )
        if ikon_url:
            embed.set_thumbnail(url=ikon_url)

        if ikon_dosya:
            await interaction.followup.send(embed=embed, file=ikon_dosya, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Perk satın alındı: {interaction.user} → {pid}")


class GemMagazaView(discord.ui.View):
    def __init__(self, kategori: str):
        super().__init__(timeout=120)
        for pid, perk in PERKLER.items():
            if kategori == "patron" and perk["patron"]:
                self.add_item(PerkSatinAlButon(pid, perk))
            elif kategori == "genel" and not perk["patron"]:
                self.add_item(PerkSatinAlButon(pid, perk))


class GemMagazaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /gem-mağaza ─────────────────────────────────────────────
    @app_commands.command(name="gem-mağaza", description="Gem Mağazası — perkler ve gem bilgisi.")
    async def gem_magaza(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid     = interaction.user.id
        bakiye  = await database.get_gem_bakiye(uid)
        perkler = await database.get_tum_aktif_perkler(uid)
        aktif_ids = {r["perk_id"] for r in perkler}

        # Her perk için satın alma durumunu önceden topla (async)
        limit_durum: dict[str, bool] = {}
        for pid, perk in PERKLER.items():
            if perk["limit_turu"] == "haftalik":
                limit_durum[pid] = await database.perk_haftalik_limit_kontrol(uid, pid)
            else:
                limit_durum[pid] = await database.perk_gunluk_limit_kontrol(uid, pid)

        embed = discord.Embed(
            title=f"{GEM} Gem Mağazası",
            description=(
                f"Coin harcayarak Gem al, Gemlerle özel perkler satın al!\n"
                f"**1 Gem = {GEM_COIN_KURU} {M2B}**\n\n"
                f"{GEM} Gem bakiyen: **{bakiye}**"
            ),
            color=0x7B2FBE,
        )

        # Genel perkler
        genel_txt = ""
        for pid, perk in PERKLER.items():
            if perk["patron"]:
                continue
            if pid in aktif_ids:
                durum = "✅ Aktif"
            elif limit_durum.get(pid):
                durum = "⏳ Bu hafta alındı" if perk["limit_turu"] == "haftalik" else "⏳ Bugün alındı"
            else:
                durum = ""
            limit = "Haftada 1" if perk["limit_turu"] == "haftalik" else "Günde 1"
            emo = perk.get("emoji", "🔹")
            genel_txt += f"{emo} **{perk['isim']}** — {perk['maliyet']} 💎\n"
            genel_txt += f"> {perk['aciklama']}\n"
            genel_txt += f"> *{limit}* {durum}\n\n"
        embed.add_field(name="🌟 Genel Perkler", value=genel_txt or "—", inline=False)

        # Patron perkleri
        patron_txt = ""
        for pid, perk in PERKLER.items():
            if not perk["patron"]:
                continue
            if limit_durum.get(pid):
                durum = "⏳ Bugün alındı"
            else:
                durum = ""
            emo = perk.get("emoji", "🔹")
            patron_txt += f"{emo} **{perk['isim']}** — {perk['maliyet']} 💎\n"
            patron_txt += f"> {perk['aciklama']}\n"
            patron_txt += f"> *Günde 1* {durum}\n\n"
        embed.add_field(name="⚔️ Patron Perkleri", value=patron_txt or "—", inline=False)

        embed.set_footer(text=f"/gem-al ile Coin → Gem dönüştür • /perklerim ile aktif perklerini gör")

        # İki kategori butonu
        view = discord.ui.View(timeout=120)

        genel_btn = discord.ui.Button(label="Genel Perkler", style=discord.ButtonStyle.success, emoji="🌟")
        patron_btn = discord.ui.Button(label="Patron Perkleri", style=discord.ButtonStyle.danger, emoji="⚔️")

        async def genel_cb(i: discord.Interaction):
            bakiye = await database.get_gem_bakiye(i.user.id)
            e = discord.Embed(
                title="🌟 Genel Perkler",
                description=f"💎 Gem bakiyen: **{bakiye}**\nSatın almak istediğin perki seç:",
                color=0x2ECC71,
            )
            for pid, p in PERKLER.items():
                if not p["patron"]:
                    limit = "Haftada 1" if p["limit_turu"] == "haftalik" else "Günde 1"
                    emo = p.get("emoji", "🔹")
                    e.add_field(
                        name=f"{emo} {p['isim']} — {p['maliyet']} 💎",
                        value=f"> {p['aciklama']}\n> *{limit}*",
                        inline=False,
                    )
            await i.response.send_message(embed=e, view=GemMagazaView("genel"), ephemeral=True)

        async def patron_cb(i: discord.Interaction):
            bakiye = await database.get_gem_bakiye(i.user.id)
            e = discord.Embed(
                title="⚔️ Patron Perkleri",
                description=f"💎 Gem bakiyen: **{bakiye}**\nSatın almak istediğin perki seç:",
                color=0xCC0000,
            )
            for pid, p in PERKLER.items():
                if p["patron"]:
                    emo = p.get("emoji", "🔹")
                    e.add_field(
                        name=f"{emo} {p['isim']} — {p['maliyet']} 💎",
                        value=f"> {p['aciklama']}\n> *Günde 1*",
                        inline=False,
                    )
            try:
                patron_dosya = discord.File(os.path.join(_ASSETS, "patron.png"), filename="patron.png")
                e.set_thumbnail(url="attachment://patron.png")
                await i.response.send_message(embed=e, file=patron_dosya, view=GemMagazaView("patron"), ephemeral=True)
            except Exception:
                await i.response.send_message(embed=e, view=GemMagazaView("patron"), ephemeral=True)

        genel_btn.callback  = genel_cb
        patron_btn.callback = patron_cb
        view.add_item(genel_btn)
        view.add_item(patron_btn)

        try:
            gem_dosya = discord.File(os.path.join(_ASSETS, "gem.png"), filename="gem.png")
            embed.set_thumbnail(url="attachment://gem.png")
            await interaction.followup.send(embed=embed, file=gem_dosya, view=view, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ── /gem-al ─────────────────────────────────────────────────
    @app_commands.command(name="gem-al", description="Coin harcayarak Gem satın al.")
    @app_commands.describe(adet="Kaç Gem almak istiyorsun?")
    async def gem_al(self, interaction: discord.Interaction, adet: int):
        await interaction.response.defer(ephemeral=True)
        if adet <= 0:
            await interaction.followup.send(f"{FAIL_EMO} Geçersiz miktar!", ephemeral=True)
            return

        maliyet = adet * GEM_COIN_KURU
        kayit   = await database.ensure_user(interaction.user.id, interaction.user.display_name)

        if kayit["bakiye"] < maliyet:
            await interaction.followup.send(
                f"{FAIL_EMO} Yetersiz Coin! Gerekli: **{maliyet:,} {M2B}** — Bakiyen: **{kayit['bakiye']:,} {M2B}**",
                ephemeral=True)
            return

        ok = await database.remove_coins(interaction.user.id, maliyet,
                                         aciklama=f"{adet} Gem satın alındı")
        if not ok:
            await interaction.followup.send(f"{FAIL_EMO} İşlem başarısız, tekrar dene.", ephemeral=True)
            return

        yeni_gem = await database.add_gem(interaction.user.id, adet,
                                          tip="gem_al", aciklama=f"{maliyet} coin ile {adet} gem")

        embed = discord.Embed(
            title=f"{OK} Gem Satın Alındı!",
            description=(
                f"{GEM} **+{adet} Gem** hesabına eklendi!\n"
                f"Harcanan: **{maliyet:,} {M2B}**\n"
                f"Toplam Gem: **{yeni_gem} {GEM}**"
            ),
            color=0x7B2FBE,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Gem alındı: {interaction.user} → {adet} gem ({maliyet} coin)")

    # ── /perklerim ───────────────────────────────────────────────
    @app_commands.command(name="perklerim", description="Aktif perklerini görüntüle.")
    async def perklerim(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        perkler = await database.get_tum_aktif_perkler(interaction.user.id)
        bakiye  = await database.get_gem_bakiye(interaction.user.id)

        embed = discord.Embed(
            title=f"{GEM} Aktif Perklerim",
            color=0x7B2FBE,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        if not perkler:
            embed.description = f"Aktif perkin yok.\n\n{GEM} Gem bakiyen: **{bakiye}**\n`/gem-mağaza` ile perk satın alabilirsin."
        else:
            txt = ""
            for r in perkler:
                pid  = r["perk_id"]
                perk = PERKLER.get(pid, {})
                isim = perk.get("isim", pid)
                bitis = r["bitis_tarihi"].strftime("%d.%m.%Y %H:%M")
                txt  += f"**{isim}**\n> ⏳ Bitiş: `{bitis}`\n\n"
            embed.description = txt
            embed.set_footer(text=f"Gem bakiyen: {bakiye} 💎")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /görev-istatistik ────────────────────────────────────────
    @app_commands.command(name="görev-istatistik", description="Görev istatistiklerini görüntüle.")
    async def gorev_istatistik(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid    = interaction.user.id
        sayi   = await database.get_lifetime_gorev_sayisi(uid)
        bakiye = await database.get_gem_bakiye(uid)

        # Mevcut rol
        esikler  = [3, 6, 9, 12]
        rol_isim = {3: "Vanguard", 6: "Harbinger", 9: "Sentinel", 12: "Luminary"}
        mevcut_rol = "—"
        sonraki_esik = None
        for e in esikler:
            if sayi >= e:
                mevcut_rol = rol_isim[e]
            else:
                if sonraki_esik is None:
                    sonraki_esik = e
                break

        embed = discord.Embed(
            title="📊 Görev İstatistikleri",
            color=0x2ECC71,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="✅ Toplam Görev", value=f"**{sayi}** görev", inline=True)
        embed.add_field(name="🏆 Mevcut Rol", value=f"**{mevcut_rol}**", inline=True)
        embed.add_field(name=f"{GEM} Gem Bakiye", value=f"**{bakiye}**", inline=True)

        if sonraki_esik:
            kalan = sonraki_esik - sayi
            embed.add_field(
                name=f"➡️ Sonraki: {rol_isim[sonraki_esik]}",
                value=f"**{kalan}** görev daha tamamla",
                inline=False,
            )
        else:
            embed.add_field(name="👑 Maksimum Seviye", value="Tüm rollere ulaştın!", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GemMagazaCog(bot))
