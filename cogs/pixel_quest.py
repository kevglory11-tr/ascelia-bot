"""cogs/pixel_quest.py — Pixel Quest RPG oyunu (v2 — dengeli)."""

import asyncio
import os
import random
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

import database
from utils.logger import setup_logger
from utils import ui
from config.pixel_quest_data import (
    IRKLAR, CANAVARLAR, LOOT_KATEGORILERI, LOOT_ISIMLERI, LOOT_IKON,
    EKIPMANLAR, EKIPMAN_TURLERI, IKSIRLER,
    SEVIYE_XP, NADIRLIK_RENK, NADIRLIK_EMOJI, NADIRLIK_SIRA, SAVAS_COOLDOWN,
    SEVIYE_STAT_BONUS, DUKKAN, MALZEME_FIYAT,
    MALZEME_DROP_SANS, EKIPMAN_DROP_SANS, IKSIR_DROP_SANS,
    MOB_IKON_KLASOR, SKILL_KLASORLERI,
)

log = setup_logger("pixel_quest")
_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "pixel_quest")


# ── Yardımcı fonksiyonlar ─────────────────────────────────
def _icon_path(klasor: str, ikon_no: int) -> str:
    return os.path.join(_ASSETS, klasor, f"Icon{ikon_no}.png")


def _seviye_hesapla(xp: int) -> int:
    seviye = 1
    for s, gerekli in SEVIYE_XP.items():
        if xp >= gerekli:
            seviye = s
    return seviye


def _sonraki_seviye_xp(seviye: int) -> Optional[int]:
    return SEVIYE_XP.get(seviye + 1)


def _hp_bar(hp: int, max_hp: int, uzunluk: int = 12) -> str:
    return ui.progress_bar(hp, max_hp, uzunluk, style="hp")


def _xp_bar(xp: int, max_xp: int, uzunluk: int = 12) -> str:
    return ui.progress_bar(xp, max_xp, uzunluk, style="xp")


def _canavar_sec(seviye: int):
    """Seviyeye göre canavar havuzundan seç (tier'lar arası yumuşak geçiş)."""
    # Yumuşak geçiş: tier sınırlarında %20-30 alt tier şansı
    if seviye >= 17:
        tier = "elit"
    elif seviye >= 15:
        tier = random.choices(["elit", "chaos"], weights=[70, 30], k=1)[0]
    elif seviye >= 10:
        tier = "chaos"
    elif seviye >= 8:
        tier = random.choices(["chaos", "low"], weights=[70, 30], k=1)[0]
    else:
        tier = "low"
    return random.choice(CANAVARLAR[tier]), tier


def _loot_drop(canavar_tier: str) -> Optional[dict]:
    """Canavar öldürüldüğünde loot düşürme şansı.

    İkonlar LOOT_IKON ile deterministic: aynı isimli item her yerde aynı görsel.
    Elit tier'da şanslı mineral (değerli maden) dropu da mümkündür.
    """
    if random.random() > MALZEME_DROP_SANS:
        return None

    if canavar_tier == "elit":
        # %20 şans mineral, %80 undead/pirate
        kategori_key = random.choices(
            ["mineral", "undead", "pirate"], weights=[20, 50, 30], k=1)[0]
    elif canavar_tier == "chaos":
        kategori_key = random.choices(
            ["pirate", "undead"], weights=[55, 45], k=1)[0]
    else:
        kategori_key = random.choices(
            ["goblin", "general"], weights=[50, 50], k=1)[0]

    kategori = LOOT_KATEGORILERI[kategori_key]
    isimler = LOOT_ISIMLERI.get(kategori_key, ["Bilinmeyen Ganimet"])
    isim = random.choice(isimler)
    ikon = LOOT_IKON.get(isim, random.randint(1, min(kategori["sayisi"], 48)))

    return {
        "isim": isim,
        "kategori": kategori_key,
        "ikon": ikon,
        "tier": kategori["tier"],
    }


def _ekipman_drop(seviye: int) -> Optional[dict]:
    """Savaş sonrası ekipman düşürme şansı."""
    if random.random() > EKIPMAN_DROP_SANS:
        return None

    tur = random.choice(["silah", "kalkan", "kemer"])
    uygun = [e for e in EKIPMANLAR[tur] if e["seviye"] <= seviye + 1]
    if not uygun:
        uygun = [EKIPMANLAR[tur][0]]

    # Nadirlik ağırlıklı seçim
    agirliklar = []
    for e in uygun:
        if e["nadirlik"] == "yaygın":     agirliklar.append(50)
        elif e["nadirlik"] == "uncommon": agirliklar.append(25)
        elif e["nadirlik"] == "nadir":    agirliklar.append(10)
        elif e["nadirlik"] == "efsanevi": agirliklar.append(3)
        elif e["nadirlik"] == "mitik":    agirliklar.append(1)
        else: agirliklar.append(10)

    ekipman = random.choices(uygun, weights=agirliklar, k=1)[0]
    return {"tur": tur, **ekipman}


def _iksir_drop() -> Optional[dict]:
    """İksir düşürme şansı."""
    if random.random() > IKSIR_DROP_SANS:
        return None
    agirliklar = []
    for ik in IKSIRLER:
        if ik["nadirlik"] == "yaygın":     agirliklar.append(50)
        elif ik["nadirlik"] == "uncommon": agirliklar.append(25)
        elif ik["nadirlik"] == "nadir":    agirliklar.append(10)
        elif ik["nadirlik"] == "efsanevi": agirliklar.append(3)
        else: agirliklar.append(10)
    return random.choices(IKSIRLER, weights=agirliklar, k=1)[0]


# ── Savaş mekaniği ──────────────────────────────────────
def _hasar_hesapla(saldiri: int, savunma: int) -> int:
    """Hasar = saldırı * rastgele(0.85-1.15) - savunma * 0.4"""
    return max(1, round(saldiri * random.uniform(0.85, 1.15) - savunma * 0.4))


# Crit/dodge maksimum şans %30 — iksir yığmanın aşırı snowball'unu engeller
_SANS_CAP = 0.30


def _kritik_mi(hiz: int) -> bool:
    """Kritik vuruş şansı: hız * 0.8%, cap %30 (Peri:16%, Ork:8%, Cüce:4%)."""
    return random.random() < min(hiz * 0.008, _SANS_CAP)


def _dodge_mi(hiz: int) -> bool:
    """Dodge şansı: hız * 0.8%, cap %30 (Peri:16%, Ork:8%, Cüce:4%)."""
    return random.random() < min(hiz * 0.008, _SANS_CAP)


def _en_iyi_eslesme(aranan: str, adaylar: list[str]) -> Optional[str]:
    """Kullanıcı girdisiyle en iyi eşleşmeyi bul (exact > startswith > contains)."""
    aranan_l = aranan.lower().strip()
    if not aranan_l:
        return None
    # 1. Tam eşleşme
    for a in adaylar:
        if a.lower() == aranan_l:
            return a
    # 2. Başlangıç eşleşmesi
    for a in adaylar:
        if a.lower().startswith(aranan_l):
            return a
    # 3. İçerme eşleşmesi
    for a in adaylar:
        if aranan_l in a.lower():
            return a
    return None


# ── Irk Seçim View ───────────────────────────────────────
class IrkSecimView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=60)
        self.cog = cog

    @discord.ui.button(label="Cüce", style=discord.ButtonStyle.primary, emoji="🧔")
    async def cuece(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._karakter_kaydet(interaction, "cuece")

    @discord.ui.button(label="Peri", style=discord.ButtonStyle.success, emoji="🧚")
    async def peri(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._karakter_kaydet(interaction, "peri")

    @discord.ui.button(label="Ork", style=discord.ButtonStyle.danger, emoji="🐗")
    async def ork(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._karakter_kaydet(interaction, "ork")


# ── Ana Cog ───────────────────────────────────────────────
class PixelQuestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cooldowns: dict[int, float] = {}
        self._buffs: dict[int, dict] = {}  # geçici iksir buffları

    async def cog_load(self):
        async with database.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pq_karakter (
                    discord_id  BIGINT PRIMARY KEY,
                    irk         TEXT NOT NULL,
                    avatar_ikon INT DEFAULT 1,
                    hp          INT NOT NULL,
                    max_hp      INT NOT NULL,
                    xp          INT DEFAULT 0,
                    altin       INT DEFAULT 0,
                    toplam_kill INT DEFAULT 0,
                    toplam_olum INT DEFAULT 0,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pq_envanter (
                    id          SERIAL PRIMARY KEY,
                    discord_id  BIGINT NOT NULL,
                    tur         TEXT NOT NULL,
                    isim        TEXT NOT NULL,
                    kategori    TEXT,
                    ikon        INT DEFAULT 1,
                    bonus       INT DEFAULT 0,
                    nadirlik    TEXT DEFAULT 'yaygın',
                    adet        INT DEFAULT 1,
                    UNIQUE (discord_id, tur, isim)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pq_savas_log (
                    id          SERIAL PRIMARY KEY,
                    discord_id  BIGINT NOT NULL,
                    canavar     TEXT NOT NULL,
                    sonuc       TEXT NOT NULL,
                    hasar       INT DEFAULT 0,
                    xp          INT DEFAULT 0,
                    altin       INT DEFAULT 0,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        log.info("Pixel Quest tabloları hazır")

    # ── Karakter kaydet ──────────────────────────────────────
    async def _karakter_kaydet(self, interaction: discord.Interaction, irk_key: str):
        irk = IRKLAR[irk_key]
        avatar_ikon = random.randint(1, 48)

        async with database.pool.acquire() as conn:
            mevcut = await conn.fetchval(
                "SELECT discord_id FROM pq_karakter WHERE discord_id=$1",
                interaction.user.id)
            if mevcut:
                await interaction.response.send_message(
                    "❌ Zaten bir karakterin var! `/pq-profil` ile bak.", ephemeral=True)
                return

            await conn.execute("""
                INSERT INTO pq_karakter (discord_id, irk, avatar_ikon, hp, max_hp)
                VALUES ($1, $2, $3, $4, $5)
            """, interaction.user.id, irk_key, avatar_ikon, irk["hp"], irk["hp"])

        avatar_path = _icon_path(irk["avatar_klasor"], avatar_ikon)
        body = (
            f"**{interaction.user.display_name}**, **{irk['emoji']} {irk['isim']}** "
            f"yolunu seçtin.\n\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.stat_line(ui.Icon.HP, 'HP', irk['hp'])}\n"
            f"{ui.stat_line(ui.Icon.ATK, 'Saldırı', irk['saldiri'])}\n"
            f"{ui.stat_line(ui.Icon.DEF, 'Savunma', irk['savunma'])}\n"
            f"{ui.stat_line(ui.Icon.SPD, 'Hız', irk['hiz'])}\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.Icon.ARROW} `/savaş` komutuyla maceraya başla."
        )
        embed = ui.panel(
            "Karakter Oluşturuldu",
            body,
            badge=ui.Icon.SPARK,
            color=ui.Palette.GOLD,
            guild=interaction.guild,
        )

        try:
            dosya = discord.File(avatar_path, filename="avatar.png")
            embed.set_thumbnail(url="attachment://avatar.png")
            await interaction.response.send_message(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.response.send_message(embed=embed, ephemeral=True)

        log.info(f"Yeni karakter: {interaction.user} → {irk['isim']}")

    # ── Karakter bilgisi çek ─────────────────────────────────
    async def _get_karakter(self, discord_id: int) -> Optional[dict]:
        async with database.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM pq_karakter WHERE discord_id=$1", discord_id)
            return dict(row) if row else None

    # ── Stat hesapla (base + seviye büyümesi + ekipman) ──────
    async def _get_statlar(self, discord_id: int, karakter: dict) -> dict:
        irk = IRKLAR[karakter["irk"]]
        seviye = _seviye_hesapla(karakter["xp"])

        statlar = {
            "saldiri": irk["saldiri"] + (seviye - 1) * SEVIYE_STAT_BONUS["saldiri"],
            "savunma": irk["savunma"] + (seviye - 1) * SEVIYE_STAT_BONUS["savunma"],
            "hiz": irk["hiz"],  # hız seviyeyle artmaz — ırk avantajı kalıcı
            "max_hp": irk["hp"] + (seviye - 1) * SEVIYE_STAT_BONUS["hp"],
        }

        # Ekipman bonusları
        async with database.pool.acquire() as conn:
            ekipmanlar = await conn.fetch(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur IN ('silah_kusanili','kalkan_kusanili','kemer_kusanili')",
                discord_id)
            for ek in ekipmanlar:
                if "silah" in ek["tur"]:
                    statlar["saldiri"] += ek["bonus"]
                elif "kalkan" in ek["tur"]:
                    statlar["savunma"] += ek["bonus"]
                elif "kemer" in ek["tur"]:
                    statlar["max_hp"] += ek["bonus"]

        # Geçici iksir buffları
        buff = self._buffs.get(discord_id, {})
        statlar["saldiri"] += buff.get("saldiri", 0)
        statlar["savunma"] += buff.get("savunma", 0)
        statlar["hiz"] += buff.get("hiz", 0)

        return statlar

    # ── /karakter-oluştur ────────────────────────────────────
    @app_commands.command(name="karakter-oluştur", description="Pixel Quest'e başla! Irkını seç.")
    async def karakter_olustur(self, interaction: discord.Interaction):
        async with database.pool.acquire() as conn:
            mevcut = await conn.fetchval(
                "SELECT discord_id FROM pq_karakter WHERE discord_id=$1",
                interaction.user.id)
        if mevcut:
            await interaction.response.send_message(
                "❌ Zaten bir karakterin var! `/pq-profil` ile bak.", ephemeral=True)
            return

        def irk_karti(key: str, baslik: str, vurgu: str) -> str:
            i = IRKLAR[key]
            return (
                f"{i['emoji']} **{i['isim']}** {ui.Icon.DIAMOND} *{vurgu}*\n"
                f"`{ui.Icon.HP} {i['hp']:>3}` "
                f"`{ui.Icon.ATK} {i['saldiri']:>3}` "
                f"`{ui.Icon.DEF} {i['savunma']:>3}` "
                f"`{ui.Icon.SPD} {i['hiz']:>3}`"
            )

        body = (
            ui.header_banner("PIXEL QUEST  —  IRK SEÇIMI")
            + "\n"
            + irk_karti("cuece", "Cüce", "Tank · yüksek HP & savunma")
            + "\n\n"
            + irk_karti("peri", "Peri", "Assassin · yüksek hız & saldırı")
            + "\n\n"
            + irk_karti("ork", "Ork",  "Dengeli · güçlü saldırı")
            + f"\n\n{ui.DIVIDER_THIN}\n"
            + f"{ui.Icon.SPARK} **Hız** {ui.Icon.ARROW} kritik & kaçınma şansı\n"
            + f"{ui.Icon.DEF} **Savunma** {ui.Icon.ARROW} hasar azaltma\n"
            + f"{ui.Icon.ATK} **Saldırı** {ui.Icon.ARROW} vuruş gücü"
        )

        embed = ui.panel(
            "Pixel Quest",
            body,
            badge=ui.Icon.SCROLL,
            color=ui.Palette.GOLD,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, view=IrkSecimView(self), ephemeral=True)

    # ── /savaş ───────────────────────────────────────────────
    @app_commands.command(name="savaş", description="Canavar savaşı! Savaşarak güçlen.")
    async def savas(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send(
                "❌ Önce `/karakter-oluştur` ile bir karakter oluştur!", ephemeral=True)
            return

        # Cooldown kontrolü
        now = datetime.now(timezone.utc).timestamp()
        son = self._cooldowns.get(interaction.user.id, 0)
        kalan = SAVAS_COOLDOWN - (now - son)
        if kalan > 0:
            await interaction.followup.send(
                f"⏳ Dinleniyorsun! **{int(kalan)}** saniye sonra tekrar savaşabilirsin.", ephemeral=True)
            return
        self._cooldowns[interaction.user.id] = now

        # Stat hesapla (seviye + ekipman + buff)
        statlar = await self._get_statlar(interaction.user.id, karakter)
        seviye = _seviye_hesapla(karakter["xp"])

        # Max HP (seviye + ekipman + buff dahil)
        gercek_max_hp = statlar["max_hp"]

        # HP kontrolü — ölüyse gerçek max HP'ye dirilt (eski db.max_hp değil)
        if karakter["hp"] <= 0:
            async with database.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE pq_karakter SET hp=$2, max_hp=$2 WHERE discord_id=$1",
                    interaction.user.id, gercek_max_hp)
            karakter["hp"] = gercek_max_hp

        # Buff bu savaşta kullanıldı — temizle (statlar zaten hesaplandı)
        self._buffs.pop(interaction.user.id, None)

        # Canavar seç
        canavar, mob_tier = _canavar_sec(seviye)

        # ── Karşılaşma animasyonu ───────────────────────────
        mob_klasor_on = MOB_IKON_KLASOR.get(mob_tier, "mobs/low")
        mob_path_on = _icon_path(mob_klasor_on, canavar["ikon"])
        intro_body = (
            f"{ui.TIER_BADGE[mob_tier]} {ui.Icon.BULLET} **{canavar['isim']}** belirdi!\n"
            f"{ui.DIVIDER_THIN}\n"
            f"🐾 HP `{canavar['hp']}` {ui.Icon.BULLET} "
            f"{ui.Icon.ATK} `{canavar['saldiri']}` {ui.Icon.BULLET} "
            f"{ui.Icon.DEF} `{canavar['savunma']}` {ui.Icon.BULLET} "
            f"{ui.Icon.SPD} `{canavar.get('hiz', 8)}`\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.Icon.FIRE} _Silahlar hazırlanıyor..._"
        )
        intro = ui.panel("Karşılaşma", intro_body, badge="⚡",
                         color=ui.TIER_COLOR[mob_tier], guild=interaction.guild)
        intro_msg = None
        try:
            intro.set_thumbnail(url="attachment://mob.png")
            intro_msg = await interaction.followup.send(
                embed=intro,
                file=discord.File(mob_path_on, filename="mob.png"),
                ephemeral=True,
                wait=True,
            )
        except Exception:
            try:
                intro_msg = await interaction.followup.send(embed=intro, ephemeral=True, wait=True)
            except Exception:
                intro_msg = None
        await asyncio.sleep(1.2)

        # ── Savaş simülasyonu ────────────────────────────────
        # HP'yi max'a clamp et (kemer çıkarılmış olabilir)
        oyuncu_hp = min(karakter["hp"], gercek_max_hp)
        canavar_hp = canavar["hp"]
        canavar_max_hp = canavar["hp"]
        turlar = []
        tur_sayisi = 0
        toplam_hasar = 0  # canavara verilen toplam hasar

        # Hız: kim önce vuruyor
        oyuncu_ilk = statlar["hiz"] >= canavar.get("hiz", 8)

        # Oyuncu ırk emojisi (savaş logunda kullanılır)
        oyuncu_emoji = IRKLAR[karakter["irk"]]["emoji"]

        while canavar_hp > 0 and oyuncu_hp > 0 and tur_sayisi < 25:
            tur_sayisi += 1

            if oyuncu_ilk:
                # Oyuncu saldırır
                canavar_dodge = _dodge_mi(canavar.get("hiz", 8))
                if canavar_dodge:
                    turlar.append(f"{oyuncu_emoji} Sen → ❌ Kaçınıldı!")
                else:
                    hasar = _hasar_hesapla(statlar["saldiri"], canavar["savunma"])
                    crit = _kritik_mi(statlar["hiz"])
                    if crit:
                        hasar = round(hasar * 1.5)
                        turlar.append(f"{oyuncu_emoji} Sen → **{hasar}** hasar 💥 KRİTİK!")
                    else:
                        turlar.append(f"{oyuncu_emoji} Sen → **{hasar}** hasar")
                    canavar_hp -= hasar
                    toplam_hasar += hasar

                if canavar_hp <= 0:
                    break

                # Canavar saldırır
                oyuncu_dodge = _dodge_mi(statlar["hiz"])
                if oyuncu_dodge:
                    turlar.append(f"🐾 {canavar['isim']} → ❌ Kaçındın!")
                else:
                    hasar = _hasar_hesapla(canavar["saldiri"], statlar["savunma"])
                    mob_crit = _kritik_mi(canavar.get("hiz", 8))
                    if mob_crit:
                        hasar = round(hasar * 1.5)
                        turlar.append(f"🐾 {canavar['isim']} → **{hasar}** hasar 💥 KRİTİK!")
                    else:
                        turlar.append(f"🐾 {canavar['isim']} → **{hasar}** hasar")
                    oyuncu_hp -= hasar
            else:
                # Canavar önce saldırır
                oyuncu_dodge = _dodge_mi(statlar["hiz"])
                if oyuncu_dodge:
                    turlar.append(f"🐾 {canavar['isim']} → ❌ Kaçındın!")
                else:
                    hasar = _hasar_hesapla(canavar["saldiri"], statlar["savunma"])
                    mob_crit = _kritik_mi(canavar.get("hiz", 8))
                    if mob_crit:
                        hasar = round(hasar * 1.5)
                        turlar.append(f"🐾 {canavar['isim']} → **{hasar}** hasar 💥 KRİTİK!")
                    else:
                        turlar.append(f"🐾 {canavar['isim']} → **{hasar}** hasar")
                    oyuncu_hp -= hasar

                if oyuncu_hp <= 0:
                    break

                # Oyuncu saldırır
                canavar_dodge = _dodge_mi(canavar.get("hiz", 8))
                if canavar_dodge:
                    turlar.append(f"{oyuncu_emoji} Sen → ❌ Kaçınıldı!")
                else:
                    hasar = _hasar_hesapla(statlar["saldiri"], canavar["savunma"])
                    crit = _kritik_mi(statlar["hiz"])
                    if crit:
                        hasar = round(hasar * 1.5)
                        turlar.append(f"{oyuncu_emoji} Sen → **{hasar}** hasar 💥 KRİTİK!")
                    else:
                        turlar.append(f"{oyuncu_emoji} Sen → **{hasar}** hasar")
                    canavar_hp -= hasar
                    toplam_hasar += hasar

        kazandi = canavar_hp <= 0
        olduruldu = oyuncu_hp <= 0
        berabere = (not kazandi) and (not olduruldu)  # tur limiti, ikisi de ayakta
        oyuncu_hp = max(0, oyuncu_hp)

        # Sonuçları kaydet
        xp_kazanc = canavar["xp"] if kazandi else 0
        altin_kazanc = random.randint(*canavar["altin"]) if kazandi else 0

        if berabere:
            sonuc = "berabere"
            kill_delta, olum_delta = 0, 0
        elif kazandi:
            sonuc = "kazandı"
            kill_delta, olum_delta = 1, 0
        else:
            sonuc = "kaybetti"
            kill_delta, olum_delta = 0, 1

        async with database.pool.acquire() as conn:
            # Max HP'yi seviyeye göre güncelle
            await conn.execute("""
                UPDATE pq_karakter SET
                    hp=$2, max_hp=$3, xp=xp+$4, altin=altin+$5,
                    toplam_kill=toplam_kill+$6, toplam_olum=toplam_olum+$7
                WHERE discord_id=$1
            """, interaction.user.id, oyuncu_hp, gercek_max_hp,
                xp_kazanc, altin_kazanc, kill_delta, olum_delta)

            await conn.execute("""
                INSERT INTO pq_savas_log (discord_id, canavar, sonuc, hasar, xp, altin)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, interaction.user.id, canavar["isim"], sonuc,
                toplam_hasar, xp_kazanc, altin_kazanc)

        # Loot kontrolü
        loot_txt = ""
        if kazandi:
            loot = _loot_drop(mob_tier)
            ekipman = _ekipman_drop(seviye)
            iksir = _iksir_drop()

            drops = []
            async with database.pool.acquire() as conn:
                if loot:
                    await conn.execute("""
                        INSERT INTO pq_envanter (discord_id, tur, isim, kategori, ikon, adet)
                        VALUES ($1, 'malzeme', $2, $3, $4, 1)
                        ON CONFLICT (discord_id, tur, isim) DO UPDATE SET adet = pq_envanter.adet + 1
                    """, interaction.user.id, loot["isim"], loot["kategori"], loot["ikon"])
                    drops.append(f"📦 **{loot['isim']}**")

                if ekipman:
                    await conn.execute("""
                        INSERT INTO pq_envanter (discord_id, tur, isim, ikon, bonus, nadirlik)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (discord_id, tur, isim) DO UPDATE SET adet = pq_envanter.adet + 1
                    """, interaction.user.id, ekipman["tur"], ekipman["isim"],
                        ekipman["ikon"], ekipman["bonus"], ekipman["nadirlik"])
                    drops.append(f"{NADIRLIK_EMOJI[ekipman['nadirlik']]} **{ekipman['isim']}** ({ekipman['tur']})")

                if iksir:
                    await conn.execute("""
                        INSERT INTO pq_envanter (discord_id, tur, isim, ikon, bonus, nadirlik)
                        VALUES ($1, 'iksir', $2, $3, $4, $5)
                        ON CONFLICT (discord_id, tur, isim) DO UPDATE SET adet = pq_envanter.adet + 1
                    """, interaction.user.id, iksir["isim"], iksir["ikon"],
                        iksir["deger"], iksir["nadirlik"])
                    drops.append(f"🧪 **{iksir['isim']}**")

            if drops:
                loot_txt = f"\n{ui.DIVIDER_THIN}\n{ui.section('Ganimet', ui.Icon.LOOT)}\n" + "\n".join(drops)

        # Seviye atlama kontrolü
        yeni_seviye = _seviye_hesapla(karakter["xp"] + xp_kazanc)
        seviye_txt = ""
        if yeni_seviye > seviye:
            # Kemer + ekipman bonuslarını koru: gerçek max_hp yeniden hesapla
            karakter["xp"] += xp_kazanc
            yeni_statlar = await self._get_statlar(interaction.user.id, karakter)
            yeni_max_hp = yeni_statlar["max_hp"]
            async with database.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE pq_karakter SET max_hp=$2, hp=$2 WHERE discord_id=$1",
                    interaction.user.id, yeni_max_hp)
            seviye_txt = (
                f"\n{ui.DIVIDER_THIN}\n{ui.Icon.UP} **SEVİYE {yeni_seviye}!** "
                f"`+1 {ui.Icon.ATK}`  `+1 {ui.Icon.DEF}`  `+10 {ui.Icon.HP}`"
            )
            # Tier geçiş
            if yeni_seviye == 8:
                seviye_txt += f"\n{ui.Icon.FIRE} **Chaos bölgesi açıldı.** Dikkatli ol..."
            elif yeni_seviye == 15:
                seviye_txt += f"\n{ui.Icon.SKULL} **Elit bölgesi açıldı.** Gerçek tehlike başlıyor!"

        # Son turları göster (max 8)
        tur_goster = turlar[-8:] if len(turlar) > 8 else turlar

        # Canavar görseli
        mob_klasor = MOB_IKON_KLASOR.get(mob_tier, "mobs/low")
        mob_path = _icon_path(mob_klasor, canavar["ikon"])

        # Irka özel skill ikonu (savaş stilini yansıtır)
        skill_klasor = SKILL_KLASORLERI.get(karakter["irk"], "skills/swordman")
        skill_ikon_no = random.randint(1, 48)
        skill_path = _icon_path(skill_klasor, skill_ikon_no)

        # Tur logu
        log_bloku = "\n".join(tur_goster)

        # HP bar & özet
        hp_bloku = (
            f"{ui.Icon.HP} **Sen** `{oyuncu_hp}/{gercek_max_hp}`\n"
            f"{_hp_bar(oyuncu_hp, gercek_max_hp)}\n"
            f"🐾 **{canavar['isim']}** `{max(0, canavar_hp)}/{canavar_max_hp}`\n"
            f"{_hp_bar(max(0, canavar_hp), canavar_max_hp)}"
        )

        if berabere:
            body = (
                f"{ui.TIER_BADGE[mob_tier]} {ui.Icon.BULLET} **{canavar['isim']}** "
                f"{ui.Icon.BULLET} `{tur_sayisi} tur`\n"
                f"{ui.DIVIDER_THIN}\n{log_bloku}\n{ui.DIVIDER_THIN}\n{hp_bloku}\n"
                f"{ui.DIVIDER_THIN}\n⚖️ _Savaş uzadı, ikiniz de geri çekildi. Ganimet yok._"
            )
            embed = ui.panel("Berabere", body, badge="⚖️",
                             color=ui.Palette.NEUTRAL, guild=interaction.guild)
        elif kazandi:
            odul = (
                f"{ui.Icon.TROPHY} `+{xp_kazanc} XP`  "
                f"{ui.Icon.BULLET}  {ui.Icon.GOLD} `+{altin_kazanc} altın`  "
                f"{ui.Icon.BULLET}  {ui.Icon.ATK} `{toplam_hasar} hasar`"
            )
            body = (
                f"{ui.TIER_BADGE[mob_tier]} {ui.Icon.BULLET} **{canavar['isim']}** "
                f"{ui.Icon.BULLET} `{tur_sayisi} tur`\n"
                f"{ui.DIVIDER_THIN}\n{log_bloku}\n{ui.DIVIDER_THIN}\n{hp_bloku}\n"
                f"{ui.DIVIDER_THIN}\n{odul}"
                f"{loot_txt}{seviye_txt}"
            )
            embed = ui.panel("Zafer", body, badge=ui.Icon.TROPHY,
                             color=ui.TIER_COLOR[mob_tier], guild=interaction.guild)
        else:
            body = (
                f"{ui.TIER_BADGE[mob_tier]} {ui.Icon.BULLET} **{canavar['isim']}** "
                f"{ui.Icon.BULLET} `{tur_sayisi} tur`\n"
                f"{ui.DIVIDER_THIN}\n{log_bloku}\n{ui.DIVIDER_THIN}\n{hp_bloku}\n"
                f"{ui.DIVIDER_THIN}\n{ui.Icon.SKULL} _Yenildin. Sonraki savaşta tam canla başlayacaksın._"
            )
            embed = ui.panel("Yenilgi", body, badge=ui.Icon.SKULL,
                             color=ui.Palette.ERROR, guild=interaction.guild)

        try:
            files = [discord.File(mob_path, filename="mob.png")]
            embed.set_thumbnail(url="attachment://mob.png")
            # Kazanılan savaşlarda ırka özel skill ikonu author kısmında
            if kazandi and os.path.exists(skill_path):
                files.append(discord.File(skill_path, filename="skill.png"))
                embed.set_author(
                    name=f"{interaction.user.display_name} • {IRKLAR[karakter['irk']]['isim']}",
                    icon_url="attachment://skill.png",
                )
            # Intro mesajı varsa düzenle (tek mesaj kalır), yoksa yeni gönder
            if intro_msg:
                await intro_msg.edit(embed=embed, attachments=files)
            else:
                await interaction.followup.send(embed=embed, files=files, ephemeral=True)
        except Exception:
            try:
                if intro_msg:
                    await intro_msg.edit(embed=embed)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-profil ───────────────────────────────────────────
    @app_commands.command(name="pq-profil", description="Pixel Quest karakterini görüntüle.")
    async def pq_profil(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send(
                "❌ Önce `/karakter-oluştur` ile bir karakter oluştur!", ephemeral=True)
            return

        irk = IRKLAR[karakter["irk"]]
        seviye = _seviye_hesapla(karakter["xp"])
        sonraki = _sonraki_seviye_xp(seviye)
        statlar = await self._get_statlar(interaction.user.id, karakter)

        # Tier
        if seviye >= 15:
            tier_key = "elit"
        elif seviye >= 8:
            tier_key = "chaos"
        else:
            tier_key = "low"

        # XP bar
        onceki_gerekli = SEVIYE_XP.get(seviye, 0)
        if sonraki:
            xp_cur = karakter["xp"] - onceki_gerekli
            xp_need = sonraki - onceki_gerekli
            xp_bar_txt = f"{_xp_bar(xp_cur, xp_need)} `{karakter['xp']:,}/{sonraki:,}`"
        else:
            xp_bar_txt = f"{'🟦' * 12} `{karakter['xp']:,} (MAX)`"

        kd = karakter['toplam_kill'] / max(1, karakter['toplam_olum'])
        body = (
            f"{ui.Icon.CROWN} `Seviye {seviye}` {ui.Icon.BULLET} "
            f"{ui.TIER_BADGE[tier_key]} {ui.Icon.BULLET} **{irk['isim']}**\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.Icon.HP} `{karakter['hp']}/{statlar['max_hp']}`\n"
            f"{_hp_bar(karakter['hp'], statlar['max_hp'])}\n"
            f"{ui.Icon.SPARK} `XP`\n"
            f"{xp_bar_txt}\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.Icon.ATK} **{statlar['saldiri']}** "
            f"{ui.Icon.BULLET} {ui.Icon.DEF} **{statlar['savunma']}** "
            f"{ui.Icon.BULLET} {ui.Icon.SPD} **{statlar['hiz']}**\n"
            f"{ui.Icon.GOLD} **{karakter['altin']:,}** altın\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.Icon.TARGET} Kill **{karakter['toplam_kill']}** "
            f"{ui.Icon.BULLET} {ui.Icon.SKULL} Ölüm **{karakter['toplam_olum']}** "
            f"{ui.Icon.BULLET} K/D `{kd:.2f}`"
        )
        embed = ui.panel(
            interaction.user.display_name,
            body,
            badge=irk["emoji"],
            color=ui.TIER_COLOR[tier_key],
            guild=interaction.guild,
        )

        avatar_path = _icon_path(irk["avatar_klasor"], karakter["avatar_ikon"])
        try:
            dosya = discord.File(avatar_path, filename="avatar.png")
            embed.set_thumbnail(url="attachment://avatar.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-envanter ─────────────────────────────────────────
    @app_commands.command(name="pq-envanter", description="Eşyalarını ve malzemelerini gör.")
    async def pq_envanter(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send(
                "❌ Önce `/karakter-oluştur` ile bir karakter oluştur!", ephemeral=True)
            return

        async with database.pool.acquire() as conn:
            esyalar = await conn.fetch(
                "SELECT * FROM pq_envanter WHERE discord_id=$1",
                interaction.user.id)

        if not esyalar:
            await interaction.followup.send("📦 Envanterin boş! `/savaş` yaparak eşya kazan.", ephemeral=True)
            return

        # Sıralama: kuşanılı önce, sonra tür, sonra nadirlik (yüksek → düşük)
        _tur_oncelik = {
            "silah_kusanili": 0, "kalkan_kusanili": 0, "kemer_kusanili": 0,
            "silah": 1, "kalkan": 1, "kemer": 1,
            "iksir": 2, "malzeme": 3,
        }
        esyalar = sorted(
            esyalar,
            key=lambda e: (_tur_oncelik.get(e["tur"], 9),
                           -NADIRLIK_SIRA.get(e["nadirlik"], 0),
                           e["isim"])
        )

        ekipman_txt = []
        malzeme_txt = []
        iksir_txt = []

        for e in esyalar:
            satir = f"{NADIRLIK_EMOJI.get(e['nadirlik'], '⬜')} **{e['isim']}**"
            if e["adet"] > 1:
                satir += f" x{e['adet']}"
            if e["bonus"] > 0 and e["tur"] not in ("malzeme",):
                satir += f" (+{e['bonus']})"

            if e["tur"] in ("silah", "kalkan", "kemer"):
                ekipman_txt.append(satir)
            elif e["tur"] == "malzeme":
                malzeme_txt.append(satir)
            elif e["tur"] == "iksir":
                iksir_txt.append(satir)
            elif "kusanili" in e["tur"]:
                ekipman_txt.append(f"✅ {satir}")

        desc_parts = []
        if ekipman_txt:
            desc_parts.append(ui.section("Ekipman", ui.Icon.WEAPON) + "\n" + "\n".join(ekipman_txt[:15]))
        if iksir_txt:
            desc_parts.append(ui.section("İksir", ui.Icon.POTION) + "\n" + "\n".join(iksir_txt[:10]))
        if malzeme_txt:
            desc_parts.append(ui.section("Malzeme", ui.Icon.LOOT) + "\n" + "\n".join(malzeme_txt[:15]))

        body = f"\n\n{ui.DIVIDER_THIN}\n\n".join(desc_parts) if desc_parts else "_Boş_"
        embed = ui.panel(
            "Envanter",
            body,
            badge=ui.Icon.BAG,
            color=ui.Palette.GOLD,
            guild=interaction.guild,
        )
        embed.set_footer(text=f"/kuşan  {ui.Icon.BULLET}  /pq-çıkar  {ui.Icon.BULLET}  /iksir-kullan  {ui.Icon.BULLET}  /pq-sat  {ui.Icon.BULLET}  /pq-dükkan")

        # Thumbnail: en nadir kuşanılı veya ekipman, yoksa iksir, yoksa malzeme
        try:
            adaylar = [e for e in esyalar if "kusanili" in e["tur"]]
            if not adaylar:
                adaylar = [e for e in esyalar if e["tur"] in ("silah","kalkan","kemer")]
            if not adaylar:
                adaylar = [e for e in esyalar if e["tur"] == "iksir"]
            if not adaylar:
                adaylar = list(esyalar)

            best = max(adaylar, key=lambda e: NADIRLIK_SIRA.get(e["nadirlik"], 0))
            tur_anahtar = best["tur"].replace("_kusanili", "")
            if tur_anahtar in EKIPMAN_TURLERI:
                klasor = EKIPMAN_TURLERI[tur_anahtar]["klasor"]
            elif best["tur"] == "iksir":
                klasor = "potions"
            elif best["tur"] == "malzeme":
                kat = LOOT_KATEGORILERI.get(best["kategori"] or "")
                klasor = kat["klasor"] if kat else None
            else:
                klasor = None

            if klasor:
                ikon_path = _icon_path(klasor, best["ikon"])
                dosya = discord.File(ikon_path, filename="inv.png")
                embed.set_thumbnail(url="attachment://inv.png")
                await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
                return
        except Exception:
            pass
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /kuşan ───────────────────────────────────────────────
    @app_commands.command(name="kuşan", description="Envanterdeki bir ekipmanı kuşan.")
    @app_commands.describe(esya="Kuşanmak istediğin eşyanın adı")
    async def kusan(self, interaction: discord.Interaction, esya: str):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce karakter oluştur!", ephemeral=True)
            return

        async with database.pool.acquire() as conn:
            adaylar = await conn.fetch(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND isim ILIKE $2 AND tur IN ('silah','kalkan','kemer')",
                interaction.user.id, f"%{esya}%")

            if not adaylar:
                await interaction.followup.send(f"❌ **{esya}** envanterde bulunamadı!", ephemeral=True)
                return

            # En iyi eşleşmeyi seç (exact > startswith > contains)
            isimler = [r["isim"] for r in adaylar]
            secilen_isim = _en_iyi_eslesme(esya, isimler) or isimler[0]
            item = next(r for r in adaylar if r["isim"] == secilen_isim)

            # Seviye kontrolü
            seviye = _seviye_hesapla(karakter["xp"])
            ekipman_data = None
            for ek in EKIPMANLAR.get(item["tur"], []):
                if ek["isim"] == item["isim"]:
                    ekipman_data = ek
                    break
            if ekipman_data and ekipman_data.get("seviye", 1) > seviye:
                await interaction.followup.send(
                    f"❌ **{item['isim']}** için seviye **{ekipman_data['seviye']}** gerekli! (Seviyen: {seviye})",
                    ephemeral=True)
                return

            kusanili_tur = f"{item['tur']}_kusanili"

            # Mevcut kuşanılı eşyayı çıkar
            mevcut = await conn.fetchrow(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur=$2",
                interaction.user.id, kusanili_tur)

            if mevcut:
                await conn.execute("""
                    INSERT INTO pq_envanter (discord_id, tur, isim, ikon, bonus, nadirlik)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (discord_id, tur, isim) DO UPDATE SET adet = pq_envanter.adet + 1
                """, interaction.user.id, item["tur"], mevcut["isim"],
                    mevcut["ikon"], mevcut["bonus"], mevcut["nadirlik"])
                await conn.execute(
                    "DELETE FROM pq_envanter WHERE id=$1", mevcut["id"])

            # Yeni eşyayı kuşan
            await conn.execute("""
                INSERT INTO pq_envanter (discord_id, tur, isim, ikon, bonus, nadirlik)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (discord_id, tur, isim) DO UPDATE SET bonus=$5
            """, interaction.user.id, kusanili_tur, item["isim"],
                item["ikon"], item["bonus"], item["nadirlik"])

            # Envanterdeki adeti düşür
            if item["adet"] > 1:
                await conn.execute(
                    "UPDATE pq_envanter SET adet=adet-1 WHERE id=$1", item["id"])
            else:
                await conn.execute(
                    "DELETE FROM pq_envanter WHERE id=$1", item["id"])

        tur_isim = EKIPMAN_TURLERI.get(item["tur"], {}).get("isim", item["tur"])
        ikon_path = _icon_path(EKIPMAN_TURLERI.get(item["tur"], {}).get("klasor", "equipment/bow"), item["ikon"])

        embed = ui.panel(
            f"{tur_isim} Kuşanıldı",
            (
                f"{NADIRLIK_EMOJI.get(item['nadirlik'], '⬜')} **{item['isim']}**\n"
                f"{ui.DIVIDER_THIN}\n"
                f"{ui.Icon.UP} Bonus `+{item['bonus']}` {tur_isim.lower()}"
            ),
            badge=ui.Icon.CHECK,
            color=ui.RARITY_COLOR.get(item["nadirlik"], ui.Palette.SUCCESS),
            guild=interaction.guild,
        )

        try:
            dosya = discord.File(ikon_path, filename="equip.png")
            embed.set_thumbnail(url="attachment://equip.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-çıkar ────────────────────────────────────────────
    @app_commands.command(name="pq-çıkar", description="Kuşanılı bir ekipmanı çıkar ve envantere geri koy.")
    @app_commands.describe(slot="Çıkarmak istediğin slot")
    @app_commands.choices(slot=[
        app_commands.Choice(name="Silah", value="silah"),
        app_commands.Choice(name="Kalkan", value="kalkan"),
        app_commands.Choice(name="Kemer", value="kemer"),
    ])
    async def pq_cikar(self, interaction: discord.Interaction, slot: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce karakter oluştur!", ephemeral=True)
            return

        kusanili_tur = f"{slot.value}_kusanili"
        async with database.pool.acquire() as conn:
            mevcut = await conn.fetchrow(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur=$2",
                interaction.user.id, kusanili_tur)

            if not mevcut:
                await interaction.followup.send(
                    f"❌ {slot.name} slotunda kuşanılı eşya yok!", ephemeral=True)
                return

            await conn.execute("""
                INSERT INTO pq_envanter (discord_id, tur, isim, ikon, bonus, nadirlik)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (discord_id, tur, isim) DO UPDATE SET adet = pq_envanter.adet + 1
            """, interaction.user.id, slot.value, mevcut["isim"],
                mevcut["ikon"], mevcut["bonus"], mevcut["nadirlik"])
            await conn.execute("DELETE FROM pq_envanter WHERE id=$1", mevcut["id"])

            # HP'yi max_hp'ye clamp et (kemer çıkarılınca max_hp düşebilir)
            statlar = await self._get_statlar(interaction.user.id, karakter)
            if karakter["hp"] > statlar["max_hp"]:
                await conn.execute(
                    "UPDATE pq_karakter SET hp=$2 WHERE discord_id=$1",
                    interaction.user.id, statlar["max_hp"])

        embed = ui.panel(
            f"{slot.name} Çıkarıldı",
            f"{NADIRLIK_EMOJI.get(mevcut['nadirlik'], '⬜')} **{mevcut['isim']}** envantere geri konuldu.",
            badge=ui.Icon.DOWN,
            color=ui.Palette.NEUTRAL,
            guild=interaction.guild,
        )
        # Ekipman ikonu thumbnail
        try:
            klasor = EKIPMAN_TURLERI.get(slot.value, {}).get("klasor", "equipment/bow")
            ikon_path = _icon_path(klasor, mevcut["ikon"])
            dosya = discord.File(ikon_path, filename="equip.png")
            embed.set_thumbnail(url="attachment://equip.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /iksir-kullan ────────────────────────────────────────
    @app_commands.command(name="iksir-kullan", description="Bir iksir kullanarak iyileş veya güçlen.")
    @app_commands.describe(iksir="Kullanmak istediğin iksirin adı")
    async def iksir_kullan(self, interaction: discord.Interaction, iksir: str):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce karakter oluştur!", ephemeral=True)
            return

        async with database.pool.acquire() as conn:
            adaylar = await conn.fetch(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur='iksir' AND isim ILIKE $2",
                interaction.user.id, f"%{iksir}%")

            if not adaylar:
                await interaction.followup.send(f"❌ **{iksir}** envanterde bulunamadı!", ephemeral=True)
                return

            isimler = [r["isim"] for r in adaylar]
            secilen_isim = _en_iyi_eslesme(iksir, isimler) or isimler[0]
            item = next(r for r in adaylar if r["isim"] == secilen_isim)

            # İksir bilgisini bul
            iksir_data = None
            for ik in IKSIRLER:
                if ik["isim"] == item["isim"]:
                    iksir_data = ik
                    break

            if not iksir_data:
                await interaction.followup.send("❌ İksir verisi bulunamadı!", ephemeral=True)
                return

            if iksir_data["etki"] == "hp":
                statlar = await self._get_statlar(interaction.user.id, karakter)
                yeni_hp = min(statlar["max_hp"], karakter["hp"] + iksir_data["deger"])
                await conn.execute(
                    "UPDATE pq_karakter SET hp=$2 WHERE discord_id=$1",
                    interaction.user.id, yeni_hp)
                etki_txt = f"❤️ +{iksir_data['deger']} HP → `{yeni_hp}/{statlar['max_hp']}`"
            else:
                # Geçici buff — sonraki savaşta aktif
                buff = self._buffs.get(interaction.user.id, {})
                buff[iksir_data["etki"]] = buff.get(iksir_data["etki"], 0) + iksir_data["deger"]
                self._buffs[interaction.user.id] = buff
                stat_emoji = {"saldiri": "⚔️", "savunma": "🛡️", "hiz": "💨"}.get(iksir_data["etki"], "⚡")
                etki_txt = f"{stat_emoji} +{iksir_data['deger']} {iksir_data['etki']} *(sonraki savaşta aktif)*"

            # Adeti düşür
            if item["adet"] > 1:
                await conn.execute("UPDATE pq_envanter SET adet=adet-1 WHERE id=$1", item["id"])
            else:
                await conn.execute("DELETE FROM pq_envanter WHERE id=$1", item["id"])

        embed = ui.panel(
            "İksir Kullanıldı",
            f"**{item['isim']}**\n{ui.DIVIDER_THIN}\n{etki_txt}",
            badge=ui.Icon.POTION,
            color=ui.RARITY_COLOR.get(item["nadirlik"], ui.Palette.SUCCESS),
            guild=interaction.guild,
        )
        try:
            ikon_path = _icon_path("potions", item["ikon"])
            dosya = discord.File(ikon_path, filename="potion.png")
            embed.set_thumbnail(url="attachment://potion.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-dükkan ───────────────────────────────────────────
    @app_commands.command(name="pq-dükkan", description="Altınla iksir satın al.")
    async def pq_dukkan(self, interaction: discord.Interaction):
        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.response.send_message(
                "❌ Önce `/karakter-oluştur` ile bir karakter oluştur!", ephemeral=True)
            return

        satirlar = []
        for i, item in enumerate(DUKKAN, 1):
            satirlar.append(
                f"`{i:>2}` {ui.Icon.POTION} **{item['isim']}** "
                f"{ui.Icon.BULLET} {ui.Icon.GOLD} `{item['fiyat']}`\n"
                f"     {ui.Icon.ARROW} _{item['aciklama']}_"
            )

        body = (
            "\n".join(satirlar)
            + f"\n{ui.DIVIDER_THIN}\n"
            + f"{ui.Icon.GOLD} Bakiye {ui.Icon.BULLET} **{karakter['altin']:,}** altın\n"
            + f"{ui.Icon.CART} `/pq-satın-al <ürün>` ile satın al."
        )
        embed = ui.panel("Dükkan", body, badge=ui.Icon.SHOP,
                         color=ui.Palette.GOLD, guild=interaction.guild)
        try:
            ikon_path = _icon_path("potions", DUKKAN[0]["ikon"])
            dosya = discord.File(ikon_path, filename="shop.png")
            embed.set_thumbnail(url="attachment://shop.png")
            await interaction.response.send_message(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /pq-satın-al ─────────────────────────────────────────
    @app_commands.command(name="pq-satın-al", description="Dükkandan ürün satın al.")
    @app_commands.describe(urun="Satın almak istediğin ürünün adı")
    async def pq_satin_al(self, interaction: discord.Interaction, urun: str):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce karakter oluştur!", ephemeral=True)
            return

        # Dükkan ürününü bul (exact > startswith > contains)
        isimler = [item["isim"] for item in DUKKAN]
        secilen_isim = _en_iyi_eslesme(urun, isimler)
        item_data = next((i for i in DUKKAN if i["isim"] == secilen_isim), None) if secilen_isim else None

        if not item_data:
            await interaction.followup.send(f"❌ **{urun}** dükkanda bulunamadı! `/pq-dükkan` ile ürünleri gör.", ephemeral=True)
            return

        if karakter["altin"] < item_data["fiyat"]:
            await interaction.followup.send(
                f"❌ Yetersiz altın! **{item_data['isim']}**: {item_data['fiyat']} altın · Sende: {karakter['altin']} altın",
                ephemeral=True)
            return

        async with database.pool.acquire() as conn:
            # Atomik altın düşürme (race condition koruması)
            result = await conn.execute(
                "UPDATE pq_karakter SET altin=altin-$2 WHERE discord_id=$1 AND altin>=$2",
                interaction.user.id, item_data["fiyat"])
            if result == "UPDATE 0":
                await interaction.followup.send(
                    "❌ Bakiye yetersiz! (eşzamanlı işlem tespit edildi)", ephemeral=True)
                return

            await conn.execute("""
                INSERT INTO pq_envanter (discord_id, tur, isim, ikon, bonus, nadirlik)
                VALUES ($1, 'iksir', $2, $3, $4, $5)
                ON CONFLICT (discord_id, tur, isim) DO UPDATE SET adet = pq_envanter.adet + 1
            """, interaction.user.id, item_data["isim"], item_data["ikon"],
                item_data["deger"], item_data["nadirlik"])

        embed = ui.panel(
            "Satın Alındı",
            (
                f"{ui.Icon.POTION} **{item_data['isim']}** envantere eklendi.\n"
                f"{ui.DIVIDER_THIN}\n"
                f"{ui.Icon.DOWN} `-{item_data['fiyat']}` "
                f"{ui.Icon.BULLET} Kalan {ui.Icon.GOLD} `{karakter['altin'] - item_data['fiyat']:,}`"
            ),
            badge=ui.Icon.CART,
            color=ui.RARITY_COLOR.get(item_data["nadirlik"], ui.Palette.SUCCESS),
            guild=interaction.guild,
        )
        try:
            ikon_path = _icon_path("potions", item_data["ikon"])
            dosya = discord.File(ikon_path, filename="potion.png")
            embed.set_thumbnail(url="attachment://potion.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-sat ──────────────────────────────────────────────
    @app_commands.command(name="pq-sat", description="Tüm malzemelerini altına çevir.")
    async def pq_sat(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce karakter oluştur!", ephemeral=True)
            return

        async with database.pool.acquire() as conn:
            malzemeler = await conn.fetch(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur='malzeme'",
                interaction.user.id)

            if not malzemeler:
                await interaction.followup.send("📦 Satılacak malzemen yok!", ephemeral=True)
                return

            toplam = 0
            detay = []
            for m in malzemeler:
                fiyat = MALZEME_FIYAT.get(m["kategori"], 3)
                kazanc = fiyat * m["adet"]
                toplam += kazanc
                detay.append(f"📦 {m['isim']} x{m['adet']} → **{kazanc}** altın")

            # Malzemeleri sil
            await conn.execute(
                "DELETE FROM pq_envanter WHERE discord_id=$1 AND tur='malzeme'",
                interaction.user.id)

            # Altın ekle
            await conn.execute(
                "UPDATE pq_karakter SET altin=altin+$2 WHERE discord_id=$1",
                interaction.user.id, toplam)

        fazla = len(detay) - 20
        fazla_txt = f"\n_...ve {fazla} malzeme daha_" if fazla > 0 else ""
        embed = ui.panel(
            "Malzemeler Satıldı",
            (
                "\n".join(detay[:20])
                + fazla_txt
                + f"\n{ui.DIVIDER_THIN}\n"
                + f"{ui.Icon.UP} Toplam {ui.Icon.GOLD} `+{toplam:,}`\n"
                + f"{ui.Icon.GOLD} Yeni bakiye **{karakter['altin'] + toplam:,}**"
            ),
            badge=ui.Icon.GOLD,
            color=ui.Palette.GOLD,
            guild=interaction.guild,
        )
        # En değerli malzemeyi thumbnail yap
        try:
            en_degerli = max(
                malzemeler,
                key=lambda m: MALZEME_FIYAT.get(m["kategori"], 3) * m["adet"],
            )
            kat = LOOT_KATEGORILERI.get(en_degerli["kategori"])
            if kat:
                ikon_path = _icon_path(kat["klasor"], en_degerli["ikon"])
                dosya = discord.File(ikon_path, filename="loot.png")
                embed.set_thumbnail(url="attachment://loot.png")
                await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
                return
        except Exception:
            pass
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-sıralama ────────────────────────────────────────
    @app_commands.command(name="pq-sıralama", description="Pixel Quest sıralamasını gör.")
    async def pq_siralama(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with database.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT discord_id, irk, xp, toplam_kill, altin
                FROM pq_karakter ORDER BY xp DESC LIMIT 10
            """)

        if not rows:
            await interaction.followup.send("Henüz kimse oynamıyor!", ephemeral=True)
            return

        madalya = ["🥇", "🥈", "🥉"]
        satirlar = []
        for i, row in enumerate(rows):
            uye = interaction.guild.get_member(row["discord_id"])
            isim = uye.display_name if uye else f"Oyuncu#{row['discord_id']}"
            irk = IRKLAR.get(row["irk"], {})
            emo = madalya[i] if i < 3 else f"`{i+1:>2}`"
            seviye = _seviye_hesapla(row["xp"])
            satirlar.append(
                f"{emo} {irk.get('emoji', '❓')} **{isim}**\n"
                f"      {ui.Icon.CROWN} `Sv.{seviye}` "
                f"{ui.Icon.BULLET} {ui.Icon.TARGET} `{row['toplam_kill']}` "
                f"{ui.Icon.BULLET} {ui.Icon.GOLD} `{row['altin']:,}`"
            )

        embed = ui.panel(
            "Pixel Quest — Sıralama",
            "\n".join(satirlar),
            badge=ui.Icon.TROPHY,
            color=ui.Palette.GOLD,
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


    # ── /pq-durum ────────────────────────────────────────────
    @app_commands.command(name="pq-durum", description="Hızlı durum: cooldown, buff, kuşanılı ekipman.")
    async def pq_durum(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce `/karakter-oluştur` çalıştır!", ephemeral=True)
            return

        irk = IRKLAR[karakter["irk"]]
        statlar = await self._get_statlar(interaction.user.id, karakter)

        # Cooldown
        now = datetime.now(timezone.utc).timestamp()
        kalan = max(0, int(SAVAS_COOLDOWN - (now - self._cooldowns.get(interaction.user.id, 0))))
        cd_txt = f"{ui.Icon.CHECK} Hazır" if kalan == 0 else f"⏳ `{kalan}s`"

        # Kuşanılı
        async with database.pool.acquire() as conn:
            kusanili = await conn.fetch(
                "SELECT tur, isim, bonus, nadirlik FROM pq_envanter "
                "WHERE discord_id=$1 AND tur IN ('silah_kusanili','kalkan_kusanili','kemer_kusanili')",
                interaction.user.id)
        slot_emoji = {"silah_kusanili": ui.Icon.WEAPON,
                      "kalkan_kusanili": ui.Icon.SHIELD,
                      "kemer_kusanili": ui.Icon.BELT}
        if kusanili:
            ek_sat = [
                f"{slot_emoji.get(k['tur'], '◆')} {NADIRLIK_EMOJI.get(k['nadirlik'], '⬜')} "
                f"**{k['isim']}** `+{k['bonus']}`"
                for k in kusanili
            ]
            ek_txt = "\n".join(ek_sat)
        else:
            ek_txt = "_Kuşanılı eşyan yok_"

        # Buff
        buff = self._buffs.get(interaction.user.id, {})
        if buff:
            buff_sat = [f"{ui.Icon.SPARK} **+{v}** {k}" for k, v in buff.items()]
            buff_txt = "\n".join(buff_sat)
        else:
            buff_txt = "_Aktif buff yok_"

        body = (
            f"{ui.Icon.HP} `{karakter['hp']}/{statlar['max_hp']}`  "
            f"{_hp_bar(karakter['hp'], statlar['max_hp'], 8)}\n"
            f"{ui.DIVIDER_THIN}\n"
            f"{ui.section('Savaş', '⏱️')} {cd_txt}\n\n"
            f"{ui.section('Kuşanılı', ui.Icon.WEAPON)}\n{ek_txt}\n\n"
            f"{ui.section('Aktif Buff', ui.Icon.POTION)}\n{buff_txt}"
        )
        embed = ui.panel(
            "Durum", body, badge=irk["emoji"],
            color=ui.Palette.GOLD, guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /pq-rehber ───────────────────────────────────────────
    @app_commands.command(name="pq-rehber", description="Pixel Quest oynanış rehberi.")
    async def pq_rehber(self, interaction: discord.Interaction):
        body = (
            f"{ui.header_banner('PIXEL QUEST — REHBER')}\n"
            f"{ui.section('1. Karakter', '🧬')}\n"
            f"{ui.Icon.ARROW} `/karakter-oluştur` ile ırk seç: Cüce, Peri, Ork\n"
            f"{ui.Icon.ARROW} Her ırkın benzersiz stat dağılımı vardır\n\n"
            f"{ui.section('2. Savaş', ui.Icon.ATK)}\n"
            f"{ui.Icon.ARROW} `/savaş` ile canavarla çatış ({SAVAS_COOLDOWN}s cooldown)\n"
            f"{ui.Icon.ARROW} Seviyene göre Low → Chaos (Sv.8) → Elit (Sv.15) bölge\n"
            f"{ui.Icon.ARROW} Hız hem kritik hem kaçınma şansını belirler (max %30)\n\n"
            f"{ui.section('3. Ekipman', ui.Icon.WEAPON)}\n"
            f"{ui.Icon.ARROW} `/kuşan <isim>` — silah/kalkan/kemer\n"
            f"{ui.Icon.ARROW} `/pq-çıkar <slot>` — kuşanılıyı çıkar\n"
            f"{ui.Icon.ARROW} Kemer HP'yi arttırır; çıkarıldığında HP clamp'lenir\n\n"
            f"{ui.section('4. Ekonomi', ui.Icon.GOLD)}\n"
            f"{ui.Icon.ARROW} `/pq-sat` — malzemeleri altına çevir\n"
            f"{ui.Icon.ARROW} `/pq-dükkan` + `/pq-satın-al <isim>` — iksir al\n"
            f"{ui.Icon.ARROW} Mineral (Elit drop) en değerli malzeme (35💰/adet)\n\n"
            f"{ui.section('5. İksirler', ui.Icon.POTION)}\n"
            f"{ui.Icon.ARROW} HP iksiri anında kullanılır\n"
            f"{ui.Icon.ARROW} Saldırı/Savunma/Hız buff'ı **sonraki savaşta** aktif olur\n"
            f"{ui.Icon.ARROW} Buff kullanılınca tüketilir (stack edilebilir)\n\n"
            f"{ui.section('6. İlerleme', ui.Icon.UP)}\n"
            f"{ui.Icon.ARROW} 20 seviyelik grind, toplam 70.000 XP\n"
            f"{ui.Icon.ARROW} Her seviyede +1 ATK, +1 DEF, +10 HP\n"
            f"{ui.Icon.ARROW} Seviye atlayınca HP tam dolar\n\n"
            f"{ui.section('Komutlar', ui.Icon.SCROLL)}\n"
            f"`/pq-profil` `/pq-envanter` `/pq-durum` `/pq-sıralama` `/pq-avatar`"
        )
        embed = ui.panel("Rehber", body, badge=ui.Icon.BOOK,
                         color=ui.Palette.GOLD, guild=interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /pq-avatar ───────────────────────────────────────────
    @app_commands.command(name="pq-avatar", description="Karakter avatarını yeniden rastgele seç.")
    async def pq_avatar(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        karakter = await self._get_karakter(interaction.user.id)
        if not karakter:
            await interaction.followup.send("❌ Önce karakter oluştur!", ephemeral=True)
            return

        yeni_ikon = random.randint(1, 48)
        # Aynı ikonu tekrar seçmeyelim
        for _ in range(4):
            if yeni_ikon != karakter["avatar_ikon"]:
                break
            yeni_ikon = random.randint(1, 48)

        async with database.pool.acquire() as conn:
            await conn.execute(
                "UPDATE pq_karakter SET avatar_ikon=$2 WHERE discord_id=$1",
                interaction.user.id, yeni_ikon)

        irk = IRKLAR[karakter["irk"]]
        avatar_path = _icon_path(irk["avatar_klasor"], yeni_ikon)
        embed = ui.panel(
            "Avatar Değişti",
            f"{irk['emoji']} **{irk['isim']}** için yeni bir görünüm seçildi.",
            badge=ui.Icon.SPARK,
            color=ui.Palette.GOLD,
            guild=interaction.guild,
        )
        try:
            dosya = discord.File(avatar_path, filename="avatar.png")
            embed.set_thumbnail(url="attachment://avatar.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PixelQuestCog(bot))
