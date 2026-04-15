"""cogs/pixel_quest.py — Pixel Quest RPG oyunu."""

import os
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

import database
from utils.logger import setup_logger
from config.pixel_quest_data import (
    IRKLAR, CANAVARLAR, LOOT_KATEGORILERI, LOOT_ISIMLERI,
    EKIPMANLAR, EKIPMAN_TURLERI, IKSIRLER,
    SEVIYE_XP, NADIRLIK_RENK, NADIRLIK_EMOJI, SAVAS_COOLDOWN,
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


def _hp_bar(hp: int, max_hp: int, uzunluk: int = 10) -> str:
    oran = max(0, hp / max_hp) if max_hp else 0
    dolu = max(0, round(oran * uzunluk))
    bos = uzunluk - dolu
    if oran > 0.6:
        emoji = "🟩"
    elif oran > 0.3:
        emoji = "🟨"
    else:
        emoji = "🟥"
    return emoji * dolu + "⬛" * bos


def _canavar_sec(seviye: int):
    if seviye >= 6:
        havuz = CANAVARLAR["chaos"]
    else:
        havuz = CANAVARLAR["low"]
    return random.choice(havuz)


def _loot_drop(canavar_tier: str) -> Optional[dict]:
    """Canavar öldürüldüğünde loot düşürme şansı."""
    if random.random() > 0.45:  # %45 şans
        return None

    if canavar_tier == "chaos":
        kategori_key = random.choice(["pirate", "undead"])
    else:
        kategori_key = random.choice(["goblin", "general"])

    kategori = LOOT_KATEGORILERI[kategori_key]
    isimler = LOOT_ISIMLERI.get(kategori_key, ["Bilinmeyen Ganimet"])
    isim = random.choice(isimler)
    ikon = random.randint(1, min(kategori["sayisi"], 48))

    return {
        "isim": isim,
        "kategori": kategori_key,
        "ikon": ikon,
        "tier": kategori["tier"],
    }


def _ekipman_drop(seviye: int) -> Optional[dict]:
    """Savaş sonrası ekipman düşürme şansı."""
    sans = 0.08  # %8
    if random.random() > sans:
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
        elif e["nadirlik"] == "nadir":    agirliklar.append(12)
        elif e["nadirlik"] == "efsanevi": agirliklar.append(5)
        elif e["nadirlik"] == "mitik":    agirliklar.append(1)
        else: agirliklar.append(10)

    ekipman = random.choices(uygun, weights=agirliklar, k=1)[0]
    return {"tur": tur, **ekipman}


def _iksir_drop() -> Optional[dict]:
    """İksir düşürme şansı (%12)."""
    if random.random() > 0.12:
        return None
    agirliklar = []
    for ik in IKSIRLER:
        if ik["nadirlik"] == "yaygın":     agirliklar.append(50)
        elif ik["nadirlik"] == "uncommon": agirliklar.append(25)
        elif ik["nadirlik"] == "nadir":    agirliklar.append(10)
        elif ik["nadirlik"] == "efsanevi": agirliklar.append(3)
        else: agirliklar.append(10)
    return random.choices(IKSIRLER, weights=agirliklar, k=1)[0]


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
                    silah_id    INT,
                    kalkan_id   INT,
                    kemer_id    INT,
                    toplam_kill INT DEFAULT 0,
                    toplam_olum INT DEFAULT 0,
                    en_derin_kat INT DEFAULT 0,
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

        # Avatar görseli
        avatar_path = _icon_path(irk["avatar_klasor"], avatar_ikon)
        embed = discord.Embed(
            title=f"⚔️ Karakter Oluşturuldu!",
            description=(
                f"**{interaction.user.display_name}** olarak **{irk['emoji']} {irk['isim']}** ırkını seçtin!\n\n"
                f"❤️ HP: **{irk['hp']}**\n"
                f"⚔️ Saldırı: **{irk['saldiri']}**\n"
                f"🛡️ Savunma: **{irk['savunma']}**\n"
                f"💨 Hız: **{irk['hiz']}**\n\n"
                f"*`/savaş` yazarak maceraya başla!*"
            ),
            color=0xFFD700,
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

    # ── Stat hesapla (base + ekipman) ────────────────────────
    async def _get_statlar(self, discord_id: int, karakter: dict) -> dict:
        irk = IRKLAR[karakter["irk"]]
        statlar = {
            "saldiri": irk["saldiri"],
            "savunma": irk["savunma"],
            "hiz": irk["hiz"],
            "max_hp": irk["max_hp"],
        }

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

        embed = discord.Embed(
            title="⚔️ Pixel Quest — Irk Seçimi",
            description=(
                "Macerana başlamak için bir ırk seç!\n\n"
                "🧔 **Cüce** — Yüksek savunma, düşük hız\n"
                f"  ❤️ {IRKLAR['cuece']['hp']} HP · ⚔️ {IRKLAR['cuece']['saldiri']} · 🛡️ {IRKLAR['cuece']['savunma']} · 💨 {IRKLAR['cuece']['hiz']}\n\n"
                "🧚 **Peri** — Yüksek büyü, düşük HP\n"
                f"  ❤️ {IRKLAR['peri']['hp']} HP · ⚔️ {IRKLAR['peri']['saldiri']} · 🛡️ {IRKLAR['peri']['savunma']} · 💨 {IRKLAR['peri']['hiz']}\n\n"
                "🐗 **Ork** — Yüksek saldırı, düşük savunma\n"
                f"  ❤️ {IRKLAR['ork']['hp']} HP · ⚔️ {IRKLAR['ork']['saldiri']} · 🛡️ {IRKLAR['ork']['savunma']} · 💨 {IRKLAR['ork']['hiz']}\n\n"
            ),
            color=0xFFD700,
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

        # HP kontrolü
        if karakter["hp"] <= 0:
            # Yeniden doğ
            async with database.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE pq_karakter SET hp=max_hp WHERE discord_id=$1",
                    interaction.user.id)
            karakter["hp"] = karakter["max_hp"]

        # Stat hesapla
        statlar = await self._get_statlar(interaction.user.id, karakter)
        seviye = _seviye_hesapla(karakter["xp"])

        # Canavar seç
        canavar = _canavar_sec(seviye)
        mob_tier = "chaos" if seviye >= 6 else "low"

        # Savaş hesaplaması
        oyuncu_hasar = max(1, statlar["saldiri"] + random.randint(-3, 5) - canavar["savunma"] // 3)
        canavar_hasar = max(1, canavar["saldiri"] + random.randint(-3, 3) - statlar["savunma"] // 3)

        # Hız avantajı — ilk vuran
        oyuncu_ilk = statlar["hiz"] + random.randint(0, 5) >= 10

        canavar_hp = canavar["hp"]
        oyuncu_hp = karakter["hp"]
        turlar = []
        tur_sayisi = 0

        while canavar_hp > 0 and oyuncu_hp > 0 and tur_sayisi < 20:
            tur_sayisi += 1
            if oyuncu_ilk:
                vuruş = oyuncu_hasar + random.randint(-2, 3)
                canavar_hp -= vuruş
                turlar.append(f"⚔️ Sen → **{vuruş}** hasar")
                if canavar_hp <= 0:
                    break
                vuruş2 = canavar_hasar + random.randint(-2, 3)
                oyuncu_hp -= vuruş2
                turlar.append(f"🐾 {canavar['isim']} → **{vuruş2}** hasar")
            else:
                vuruş2 = canavar_hasar + random.randint(-2, 3)
                oyuncu_hp -= vuruş2
                turlar.append(f"🐾 {canavar['isim']} → **{vuruş2}** hasar")
                if oyuncu_hp <= 0:
                    break
                vuruş = oyuncu_hasar + random.randint(-2, 3)
                canavar_hp -= vuruş
                turlar.append(f"⚔️ Sen → **{vuruş}** hasar")

        kazandi = canavar_hp <= 0
        oyuncu_hp = max(0, oyuncu_hp)

        # Sonuçları kaydet
        xp_kazanc = canavar["xp"] if kazandi else 0
        altin_kazanc = random.randint(*canavar["altin"]) if kazandi else 0

        async with database.pool.acquire() as conn:
            await conn.execute("""
                UPDATE pq_karakter SET
                    hp=$2, xp=xp+$3, altin=altin+$4,
                    toplam_kill=toplam_kill+$5, toplam_olum=toplam_olum+$6
                WHERE discord_id=$1
            """, interaction.user.id, oyuncu_hp,
                xp_kazanc, altin_kazanc,
                1 if kazandi else 0, 0 if kazandi else 1)

            await conn.execute("""
                INSERT INTO pq_savas_log (discord_id, canavar, sonuc, hasar, xp, altin)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, interaction.user.id, canavar["isim"],
                "kazandı" if kazandi else "kaybetti",
                oyuncu_hasar * tur_sayisi, xp_kazanc, altin_kazanc)

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
                loot_txt = "\n**Ganimet:**\n" + "\n".join(drops)

        # Seviye atlama kontrolü
        yeni_seviye = _seviye_hesapla(karakter["xp"] + xp_kazanc)
        seviye_txt = ""
        if yeni_seviye > seviye:
            yeni_max_hp = IRKLAR[karakter["irk"]]["hp"] + (yeni_seviye - 1) * 15
            async with database.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE pq_karakter SET max_hp=$2, hp=$2 WHERE discord_id=$1",
                    interaction.user.id, yeni_max_hp)
            seviye_txt = f"\n\n🎉 **SEVİYE ATLADIN!** Seviye **{yeni_seviye}**!"

        # Savaş sonrası son turları göster
        tur_goster = turlar[-6:] if len(turlar) > 6 else turlar

        # Canavar görseli
        mob_klasor = f"mobs/{mob_tier}"
        mob_path = _icon_path(mob_klasor, canavar["ikon"])

        if kazandi:
            embed = discord.Embed(
                title=f"⚔️ Zafer! — {canavar['isim']}",
                description=(
                    f"**Savaş ({tur_sayisi} tur):**\n" +
                    "\n".join(tur_goster) +
                    f"\n\n✅ **{canavar['isim']}** yenildi!\n"
                    f"🏆 **+{xp_kazanc} XP** · 💰 **+{altin_kazanc} altın**\n"
                    f"❤️ Kalan HP: {_hp_bar(oyuncu_hp, statlar['max_hp'])} `{oyuncu_hp}/{statlar['max_hp']}`"
                    f"{loot_txt}{seviye_txt}"
                ),
                color=0x2ECC71,
            )
        else:
            embed = discord.Embed(
                title=f"💀 Yenildin! — {canavar['isim']}",
                description=(
                    f"**Savaş ({tur_sayisi} tur):**\n" +
                    "\n".join(tur_goster) +
                    f"\n\n❌ **{canavar['isim']}** seni yendi!\n"
                    f"💀 Dinlenmen gerekiyor... Sonraki savaşta tam canla başlarsın."
                ),
                color=0xE74C3C,
            )

        try:
            dosya = discord.File(mob_path, filename="mob.png")
            embed.set_thumbnail(url="attachment://mob.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
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

        xp_txt = f"{karakter['xp']}/{sonraki}" if sonraki else f"{karakter['xp']} (MAX)"

        embed = discord.Embed(
            title=f"{irk['emoji']} {interaction.user.display_name}",
            description=(
                f"**Irk:** {irk['isim']} · **Seviye:** {seviye}\n"
                f"**XP:** {xp_txt}\n\n"
                f"❤️ HP: {_hp_bar(karakter['hp'], statlar['max_hp'])} `{karakter['hp']}/{statlar['max_hp']}`\n"
                f"⚔️ Saldırı: **{statlar['saldiri']}** · 🛡️ Savunma: **{statlar['savunma']}** · 💨 Hız: **{statlar['hiz']}**\n"
                f"💰 Altın: **{karakter['altin']:,}**\n\n"
                f"🗡️ Öldürme: **{karakter['toplam_kill']}** · 💀 Ölüm: **{karakter['toplam_olum']}**"
            ),
            color=NADIRLIK_RENK.get("uncommon", 0x2ECC71),
        )

        avatar_path = _icon_path(irk["avatar_klasor"], karakter["avatar_ikon"])
        try:
            dosya = discord.File(avatar_path, filename="avatar.png")
            embed.set_thumbnail(url="attachment://avatar.png")
            await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /envanter ────────────────────────────────────────────
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
                "SELECT * FROM pq_envanter WHERE discord_id=$1 ORDER BY tur, nadirlik DESC",
                interaction.user.id)

        if not esyalar:
            await interaction.followup.send("📦 Envanterin boş! `/savaş` yaparak eşya kazan.", ephemeral=True)
            return

        # Kategorilere ayır
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
            desc_parts.append("**Ekipman:**\n" + "\n".join(ekipman_txt[:15]))
        if malzeme_txt:
            desc_parts.append("**Malzeme:**\n" + "\n".join(malzeme_txt[:15]))
        if iksir_txt:
            desc_parts.append("**İksir:**\n" + "\n".join(iksir_txt[:10]))

        embed = discord.Embed(
            title="📦 Envanter",
            description="\n\n".join(desc_parts) if desc_parts else "Boş",
            color=0xFFD700,
        )
        embed.set_footer(text="/kuşan <eşya adı> · /iksir-kullan <iksir adı>")
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
            item = await conn.fetchrow(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND isim ILIKE $2 AND tur IN ('silah','kalkan','kemer')",
                interaction.user.id, f"%{esya}%")

            if not item:
                await interaction.followup.send(f"❌ **{esya}** envanterde bulunamadı!", ephemeral=True)
                return

            kusanili_tur = f"{item['tur']}_kusanili"

            # Mevcut kuşanılı eşyayı çıkar
            mevcut = await conn.fetchrow(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur=$2",
                interaction.user.id, kusanili_tur)

            if mevcut:
                # Eski eşyayı envantere geri koy
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

        embed = discord.Embed(
            title=f"✅ {tur_isim} Kuşanıldı!",
            description=(
                f"{NADIRLIK_EMOJI.get(item['nadirlik'], '⬜')} **{item['isim']}**\n"
                f"Bonus: **+{item['bonus']}** {tur_isim.lower()}"
            ),
            color=NADIRLIK_RENK.get(item["nadirlik"], 0x2ECC71),
        )

        try:
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
            item = await conn.fetchrow(
                "SELECT * FROM pq_envanter WHERE discord_id=$1 AND tur='iksir' AND isim ILIKE $2",
                interaction.user.id, f"%{iksir}%")

            if not item:
                await interaction.followup.send(f"❌ **{iksir}** envanterde bulunamadı!", ephemeral=True)
                return

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
                yeni_hp = min(karakter["max_hp"], karakter["hp"] + iksir_data["deger"])
                await conn.execute(
                    "UPDATE pq_karakter SET hp=$2 WHERE discord_id=$1",
                    interaction.user.id, yeni_hp)
                etki_txt = f"❤️ +{iksir_data['deger']} HP → `{yeni_hp}/{karakter['max_hp']}`"
            else:
                etki_txt = f"⚡ +{iksir_data['deger']} {iksir_data['etki']} (savaş bonusu yakında)"

            # Adeti düşür
            if item["adet"] > 1:
                await conn.execute("UPDATE pq_envanter SET adet=adet-1 WHERE id=$1", item["id"])
            else:
                await conn.execute("DELETE FROM pq_envanter WHERE id=$1", item["id"])

        embed = discord.Embed(
            title=f"🧪 İksir Kullanıldı!",
            description=f"**{item['isim']}**\n{etki_txt}",
            color=0x2ECC71,
        )
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
            emo = madalya[i] if i < 3 else f"`{i+1}.`"
            seviye = _seviye_hesapla(row["xp"])
            satirlar.append(
                f"{emo} {irk.get('emoji', '❓')} **{isim}** — Sv.{seviye} · {row['toplam_kill']} kill · {row['altin']:,} altın"
            )

        embed = discord.Embed(
            title="⚔️ Pixel Quest Sıralaması",
            description="\n".join(satirlar),
            color=0xFFD700,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PixelQuestCog(bot))
