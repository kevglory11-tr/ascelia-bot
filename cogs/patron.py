"""cogs/patron.py — Patron Sistemi. Random doğar, topluluk birlikte savaşır."""

import os, random, asyncio, uuid
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import database
from utils.logger import setup_logger
from utils.patron_gorseli import patron_gorseli_olustur
from config.coin_settings import (
    PATRON_KANAL_ID, PATRON_MIN_SAAT, PATRON_MAX_SAAT,
    PATRON_HP, PATRON_SURE_DK, PATRON_MAX_SALDIRI,
    PATRON_HASAR_MIN, PATRON_HASAR_MAX, BILDIRIM_KANAL_ID,
    PATRON_MAX_INDIRIM_SN, PATRON_INDIRIM_ESIK,
)

log       = setup_logger("patron")
GEM       = "💎"
OK        = "<a:olumlutick:1478524954688356494>"
FAIL_EMO  = "<a:no:1478524993670479942>"
SWORD     = "⚔️"
SKULL     = "💀"

_ASSETS    = os.path.join(os.path.dirname(__file__), "..", "assets")
PATRON_IMG = os.path.join(_ASSETS, "patron.png")

# Bildirim verilecek perk'ler
BILDIRIM_PERKLER = ["giris_takviyesi", "gorev_takviyesi"]


class SaldiriView(discord.ui.View):
    def __init__(self, cog: "PatronCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Saldır!", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="patron_saldir_btn")
    async def saldir_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._saldiri_isle(interaction)


class PatronCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot              = bot
        self.aktif_patron     = None   # {"mesaj", "patron_id", "bitis", "katilimcilar": {uid: hasar}}
        self.patron_hp        = 0
        self.patron_max_hp    = 0      # Scaling ile büyüyen max HP
        self.kalan_sure       = 0
        self.indirilen_toplam = 0
        self.unique_yazanlar  = set()
        self._hp_lock         = asyncio.Lock()
        self.bot.loop.create_task(self._dongu())
        self.bot.loop.create_task(self._perk_bildirim_dongu())
        self.bot.loop.create_task(self._haftalik_odul_dongu())

    # ── Ana döngü ────────────────────────────────────────────────
    async def _dongu(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                self.kalan_sure       = random.randint(
                    int(PATRON_MIN_SAAT * 3600), int(PATRON_MAX_SAAT * 3600))
                self.indirilen_toplam = 0
                self.unique_yazanlar  = set()
                log.info(f"Sonraki patron: {self.kalan_sure//3600}s {(self.kalan_sure%3600)//60}dk sonra")

                while self.kalan_sure > 0:
                    await asyncio.sleep(1)
                    self.kalan_sure -= 1

                await self._gonder()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Patron döngüsü hatası: {e}", exc_info=True)
                await asyncio.sleep(60)

    # ── Patron gönder ────────────────────────────────────────────
    async def _gonder(self):
        if not PATRON_KANAL_ID:
            log.warning("PATRON_KANAL_ID ayarlanmamış!")
            return
        if self.aktif_patron:
            return

        kanal = self.bot.get_channel(PATRON_KANAL_ID)
        if not kanal:
            try:
                kanal = await self.bot.fetch_channel(PATRON_KANAL_ID)
            except Exception as e:
                log.error(f"Patron kanalı fetch edilemedi: {e}")
                return

        patron_id          = str(uuid.uuid4())
        self.patron_hp     = PATRON_HP
        self.patron_max_hp = PATRON_HP
        bitis_zamani       = datetime.now(timezone.utc) + timedelta(minutes=PATRON_SURE_DK)

        embed = discord.Embed(
            title="👹 Bir Patron Belirdi!",
            description=(
                f"Güçlü bir patron sunucuya saldırıyor!\n\n"
                f"❤️ **Can:** {self._hp_bar(PATRON_HP, PATRON_HP)} `{PATRON_HP}/{PATRON_HP}`\n\n"
                f"⚔️ **Saldırı hakkın:** {PATRON_MAX_SALDIRI}\n"
                f"⏳ **Süre:** {PATRON_SURE_DK} dakika\n\n"
                f"Aşağıdaki butona tıklayarak patrona saldır!\n"
                f"Hafta sonunda en çok hasar veren **3 kişi** Gem ödülü kazanır!\n\n"
                f"🥇 **1.** → 3 {GEM}  |  🥈 **2.** → 2 {GEM}  |  🥉 **3.** → 1 {GEM}\n"
                f"*(Ödüller her Pazartesi 00:00 TR'de dağıtılır)*"
            ),
            color=0xCC0000,
        )
        embed.set_footer(text=f"Patron ID: {patron_id[:8]} • {PATRON_SURE_DK} dakika içinde yenilmeli!")

        view = SaldiriView(self)
        mesaj = await kanal.send(embed=embed, view=view)

        self.aktif_patron = {
            "mesaj":      mesaj,
            "patron_id":  patron_id,
            "bitis":      bitis_zamani,
            "katilimcilar": {},
        }

        log.info(f"Patron doğdu: {patron_id[:8]}")

        # Süre dolunca bitir
        await asyncio.sleep(PATRON_SURE_DK * 60)
        if self.aktif_patron and self.aktif_patron["patron_id"] == patron_id:
            await self._patron_bitis(kacan=True)

    # ── Saldırı işle ─────────────────────────────────────────────
    async def _saldiri_isle(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self.aktif_patron:
            await interaction.followup.send(f"{FAIL_EMO} Aktif patron yok!", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        if now >= self.aktif_patron["bitis"]:
            await interaction.followup.send(f"{FAIL_EMO} Patron savaşı sona erdi!", ephemeral=True)
            return

        uid       = interaction.user.id
        patron_id = self.aktif_patron["patron_id"]

        # Saldırı hakkı kontrolü
        ekstra = await database.perk_gunluk_limit_kontrol(uid, "patron_ekstra_saldiri")
        maks   = PATRON_MAX_SALDIRI + (1 if ekstra else 0)
        mevcut = await database.patron_saldiri_sayisi_al(patron_id, uid)

        if mevcut >= maks:
            await interaction.followup.send(
                f"{FAIL_EMO} Saldırı hakkın bitti! (Maks: **{maks}**)", ephemeral=True)
            return

        # Hasar hesapla
        hasar, crit = await self._hasar_hesapla(uid)

        async with self._hp_lock:
            if self.patron_hp <= 0:
                await interaction.followup.send(f"{FAIL_EMO} Patron zaten yenildi!", ephemeral=True)
                return

            ilk_saldiri = uid not in self.aktif_patron["katilimcilar"]
            if ilk_saldiri:
                self.aktif_patron["katilimcilar"][uid] = 0

            self.patron_hp -= hasar
            hp_simdi        = max(0, self.patron_hp)
            max_hp_simdi    = self.patron_max_hp

            # Katılımcı kaydı (in-memory)
            self.aktif_patron["katilimcilar"][uid] += hasar

        # DB'ye kaydet
        await database.patron_hasar_kaydet(patron_id, uid, hasar, 1)

        # Perk durumlarını al (görsel için)
        guclu_darbe = await database.perk_gunluk_limit_kontrol(uid, "patron_guclu_darbe")
        crit_hasar  = await database.perk_gunluk_limit_kontrol(uid, "patron_kritik_hasar")

        kalan_hak = maks - (mevcut + 1)

        # Perk renkli hasar açıklaması
        if crit and crit_hasar:
            hasar_aciklama = f"💜 **KRİTİK + Hasar Artışı:** -{hasar}"
        elif crit:
            hasar_aciklama = f"🟠 **KRİTİK Vuruş:** -{hasar}"
        elif guclu_darbe:
            hasar_aciklama = f"🔴 **Güçlü Darbe:** -{hasar}"
        else:
            hasar_aciklama = f"⚔️ **Hasar:** -{hasar}"

        # Saldırı görseli oluştur (asyncio executor ile bloklamayı önle)
        loop = asyncio.get_running_loop()
        buf  = await loop.run_in_executor(None, patron_gorseli_olustur,
                                          hp_simdi, max_hp_simdi, hasar, crit,
                                          guclu_darbe, crit_hasar,
                                          interaction.user.display_name)

        dosya = discord.File(buf, filename="saldiri.png")
        embed = discord.Embed(
            title=f"{SWORD} Saldırı!",
            description=(
                f"{hasar_aciklama}\n"
                f"❤️ Patron canı: **{hp_simdi}/{max_hp_simdi}**\n"
                f"Kalan saldırı hakkın: **{kalan_hak}**"
            ),
            color=0xFF0000 if crit else 0xCC4400,
        )
        embed.set_image(url="attachment://saldiri.png")
        await interaction.followup.send(embed=embed, file=dosya, ephemeral=True)

        # Ana embed HP bar güncelle
        await self._embed_guncelle(hp_simdi)

        # Patron öldü mü?
        if hp_simdi <= 0:
            await self._patron_bitis(kacan=False)

    # ── Hasar hesapla ────────────────────────────────────────────
    async def _hasar_hesapla(self, discord_id: int) -> tuple[int, bool]:
        base = random.randint(PATRON_HASAR_MIN, PATRON_HASAR_MAX)

        guclu = await database.perk_gunluk_limit_kontrol(discord_id, "patron_guclu_darbe")
        if guclu:
            base += 8

        crit_rate = 0.25 if await database.perk_gunluk_limit_kontrol(discord_id, "patron_kritik_sans") else 0.0
        crit      = random.random() < crit_rate

        if crit:
            crit_carpan = 1.15 if await database.perk_gunluk_limit_kontrol(discord_id, "patron_kritik_hasar") else 1.0
            hasar = int(base * crit_carpan)
        else:
            hasar = base

        return hasar, crit

    # ── Embed güncelle ───────────────────────────────────────────
    async def _embed_guncelle(self, hp: int):
        if not self.aktif_patron:
            return
        try:
            mesaj = self.aktif_patron["mesaj"]
            embed = mesaj.embeds[0] if mesaj.embeds else None
            if not embed:
                return

            yeni_embed = embed.copy()
            # HP satırını güncelle
            desc = embed.description or ""
            for line in desc.split("\n"):
                if "❤️ **Can:**" in line:
                    desc = desc.replace(
                        line,
                        f"❤️ **Can:** {self._hp_bar(hp, self.patron_max_hp)} `{hp}/{self.patron_max_hp}`"
                    )
                    break
            yeni_embed.description = desc
            await mesaj.edit(embed=yeni_embed)
        except Exception as e:
            log.debug(f"Embed güncelleme hatası: {e}")

    # ── HP bar ───────────────────────────────────────────────────
    def _hp_bar(self, hp: int, max_hp: int, uzunluk: int = 10) -> str:
        oran = hp / max_hp if max_hp else 0
        dolu = max(0, round(oran * uzunluk))
        bos  = uzunluk - dolu
        if oran > 0.6:
            emoji = "🟩"   # Yeşil — sağlıklı
        elif oran > 0.3:
            emoji = "🟨"   # Sarı — yarı can
        else:
            emoji = "🟥"   # Kırmızı — kritik
        return emoji * dolu + "⬛" * bos

    # ── Patron bitiş ─────────────────────────────────────────────
    async def _patron_bitis(self, kacan: bool = False):
        if not self.aktif_patron:
            return

        patron     = self.aktif_patron
        self.aktif_patron  = None
        self.patron_hp     = 0
        self.patron_max_hp = 0

        mesaj     = patron["mesaj"]
        patron_id = patron["patron_id"]
        kanal     = mesaj.channel

        # Ana patron mesajını sil
        try:
            await mesaj.delete()
        except Exception:
            pass

        # Sıralama sonuç kanalı
        SONUC_KANAL_ID = 1465132633494388828
        sonuc_kanal = self.bot.get_channel(SONUC_KANAL_ID)
        if not sonuc_kanal:
            try:
                sonuc_kanal = await self.bot.fetch_channel(SONUC_KANAL_ID)
            except Exception:
                sonuc_kanal = kanal  # fallback: aynı kanala at

        if kacan:
            siralama = await database.patron_hasar_siralaması(patron_id, limit=10)
            embed = discord.Embed(
                title="💨 Patron Kaçtı!",
                description="Süre doldu, patron kaçtı!",
                color=0x95A5A6,
            )
            await kanal.send(embed=embed, delete_after=10)
            # Sıralamayı sonuç kanalına at
            if siralama:
                s_embed = discord.Embed(
                    title="💨 Patron Kaçtı — Hasar Sıralaması",
                    description=self._hasar_listesi(siralama, kanal.guild),
                    color=0x95A5A6,
                )
                await sonuc_kanal.send(embed=s_embed)
            log.info(f"Patron kaçtı: {patron_id[:8]}")
            return

        siralama = await database.patron_hasar_siralaması(patron_id, limit=10)
        hafta_no = self._hafta_no()
        haftalik = await database.patron_haftalik_siralama(hafta_no, limit=5)

        # Patron kanalına kısa bilgi (10 sn sonra silinir)
        embed = discord.Embed(
            title=f"{SKULL} Patron Yenildi!",
            description=f"Topluluk patronu devirdi! Sıralama <#{SONUC_KANAL_ID}> kanalında.",
            color=0xFFD700,
        )
        await kanal.send(embed=embed, delete_after=10)

        # Sonuç kanalına detaylı sıralama
        hasar_txt = self._hasar_listesi(siralama, kanal.guild) if siralama else "—"
        haftalik_txt = self._haftalik_liste(haftalik, kanal.guild) if haftalik else ""

        desc_parts = [f"🏆 Top 3 → `{3}/{2}/{1}` {GEM}\n\n**Baskın Sıralaması:**\n{hasar_txt}"]
        if haftalik_txt:
            desc_parts.append(f"**Haftalık Top 5:**\n{haftalik_txt}")

        s_embed = discord.Embed(
            title=f"{SKULL} Patron Yenildi!",
            description="\n\n".join(desc_parts),
            color=0xFFD700,
        )
        s_embed.set_footer(text=f"Ödüller Pazartesi 00:00 TR · {hafta_no}")

        mentions = " ".join([
            kanal.guild.get_member(r["discord_id"]).mention
            for r in siralama[:3]
            if kanal.guild.get_member(r["discord_id"])
        ])
        await sonuc_kanal.send(content=mentions if mentions else None, embed=s_embed)
        log.info(f"Patron yenildi: {patron_id[:8]} — {len(siralama)} katılımcı")

    # ── Yardımcı: hafta numarası (TR saatiyle ISO) ───────────────
    def _hafta_no(self, dt: datetime = None) -> str:
        """Örnek çıktı: '2026-14'  (SQL TO_CHAR IYYY-IW ile uyumlu)"""
        TR_OFFSET = timedelta(hours=3)
        if dt is None:
            dt = datetime.now(timezone.utc)
        tr_zaman = dt + TR_OFFSET
        iso = tr_zaman.isocalendar()
        return f"{iso[0]}-{iso[1]:02d}"

    # ── Yardımcı: baskın hasar listesi metni ─────────────────────
    def _hasar_listesi(self, siralama, guild) -> str:
        madalya = ["🥇", "🥈", "🥉"]
        satirlar = []
        for i, row in enumerate(siralama):
            uye  = guild.get_member(row["discord_id"])
            isim = uye.display_name if uye else f"Kullanıcı#{row['discord_id']}"
            emo  = madalya[i] if i < 3 else f"`{i+1}.`"
            satirlar.append(f"{emo} **{isim}** — {row['toplam_hasar']} hasar")
        return "\n".join(satirlar) or "—"

    # ── Yardımcı: haftalık liste metni ───────────────────────────
    def _haftalik_liste(self, siralama, guild) -> str:
        madalya = ["🥇", "🥈", "🥉"]
        satirlar = []
        for i, row in enumerate(siralama):
            uye  = guild.get_member(row["discord_id"])
            isim = uye.display_name if uye else f"Kullanıcı#{row['discord_id']}"
            emo  = madalya[i] if i < 3 else f"`{i+1}.`"
            satirlar.append(f"{emo} **{isim}** — {row['haftalik_hasar']} hasar")
        return "\n".join(satirlar) or "—"

    # ── Haftalık ödül döngüsü (Pazartesi 00:00 TR) ───────────────
    async def _haftalik_odul_dongu(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(1800)  # Her 30 dakikada kontrol

                TR_OFFSET = timedelta(hours=3)
                simdi_tr  = datetime.now(timezone.utc) + TR_OFFSET

                # Sadece Pazartesi (weekday=0) saat 00:00-01:00 arasında çalış
                if simdi_tr.weekday() != 0 or simdi_tr.hour != 0:
                    continue

                # Geçen haftanın numarası (Pazar sonu = Pazartesi sabahı önceki hafta)
                gecen_hafta_dt = datetime.now(timezone.utc) - timedelta(days=1)
                gecen_hafta_no = self._hafta_no(gecen_hafta_dt)

                # Zaten verildi mi?
                if await database.patron_haftalik_odul_verildi(gecen_hafta_no):
                    await asyncio.sleep(3600)  # 1 saat atla, tekrar kontrol etme
                    continue

                # Haftalık sıralama al
                siralama = await database.patron_haftalik_siralama(gecen_hafta_no, limit=20)
                if not siralama:
                    # Kimse patron oynamadı, yine de işaretleyelim
                    await database.patron_haftalik_odul_kaydet(gecen_hafta_no, 0, 0, 0)
                    continue

                # Ödüller: {sira: gem}
                odul_map  = {1: 3, 2: 2, 3: 1}
                madalya   = {1: "🥇", 2: "🥈", 3: "🥉"}
                odul_satirlari = []

                sira_sayac   = 1
                onceki_hasar = None
                atanan_sira  = 1

                for row in siralama:
                    hasar = row["haftalik_hasar"]
                    if hasar != onceki_hasar:
                        atanan_sira  = sira_sayac
                        onceki_hasar = hasar

                    if atanan_sira > 3:
                        break

                    gem_odul = odul_map[atanan_sira]
                    uid      = row["discord_id"]

                    await database.add_gem(uid, gem_odul,
                                           tip="haftalik_patron_odul",
                                           aciklama=f"Haftalık patron {atanan_sira}. ({gecen_hafta_no})")
                    await database.patron_haftalik_odul_kaydet(gecen_hafta_no, uid, atanan_sira, gem_odul)

                    # Guild'den isim al
                    isim = f"Kullanıcı#{uid}"
                    for guild in self.bot.guilds:
                        uye = guild.get_member(uid)
                        if uye:
                            isim = uye.display_name
                            break

                    emo = madalya.get(atanan_sira, "🏅")
                    odul_satirlari.append(
                        f"{emo} **{isim}** — {hasar} hasar → **+{gem_odul} {GEM}**"
                    )
                    sira_sayac += 1

                # Duyuru
                if PATRON_KANAL_ID:
                    kanal = self.bot.get_channel(PATRON_KANAL_ID)
                    if kanal:
                        embed = discord.Embed(
                            title=f"{GEM} Haftalık Patron Ödülleri Dağıtıldı!",
                            description=(
                                f"**{gecen_hafta_no}** haftasının en iyi patron avcıları:\n\n"
                                + ("\n".join(odul_satirlari) or "Bu hafta kimse patron oynamadı.")
                            ),
                            color=0xFFD700,
                        )
                        embed.set_footer(text="Tebrikler! Gemleriniz hesabınıza eklendi.")
                        await kanal.send(embed=embed)

                log.info(f"Haftalık patron ödülleri dağıtıldı: {gecen_hafta_no} — {len(odul_satirlari)} kişi")

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Haftalık ödül döngüsü hatası: {e}", exc_info=True)

    # ── Perk bitiş bildirim döngüsü ──────────────────────────────
    async def _perk_bildirim_dongu(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(3600)  # her saat
                biten = await database.temizle_suresi_dolan_perkler(BILDIRIM_PERKLER)
                if not biten or not BILDIRIM_KANAL_ID:
                    continue

                kanal = self.bot.get_channel(BILDIRIM_KANAL_ID)
                if not kanal:
                    continue

                from cogs.gem_magaza import PERKLER
                for discord_id, perk_id in biten:
                    perk  = PERKLER.get(perk_id, {})
                    isim  = perk.get("isim", perk_id)
                    uye   = kanal.guild.get_member(discord_id) if kanal.guild else None
                    mention = uye.mention if uye else f"<@{discord_id}>"
                    try:
                        await kanal.send(
                            f"⏰ {mention} **{isim}** perkin sona erdi! "
                            f"Yenilemek için `/gem-mağaza` kullanabilirsin."
                        )
                    except Exception as e:
                        log.warning(f"Perk bildirim gönderilemedi: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Perk bildirim döngüsü hatası: {e}", exc_info=True)

    # ── Mesaj dinleyici (süre kısaltma) ──────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.kalan_sure <= 0 or self.aktif_patron:
            return
        if self.indirilen_toplam >= PATRON_MAX_INDIRIM_SN:
            return

        self.unique_yazanlar.add(message.author.id)

        if len(self.unique_yazanlar) >= PATRON_INDIRIM_ESIK:
            indirim = 1800  # Her tetiklemede 30 dk indirim
            kalan_indirilebilir = PATRON_MAX_INDIRIM_SN - self.indirilen_toplam
            indirim = min(indirim, kalan_indirilebilir, self.kalan_sure - 10)
            if indirim > 0:
                self.kalan_sure       -= indirim
                self.indirilen_toplam += indirim
                self.unique_yazanlar   = set()
                log.info(
                    f"Patron {indirim//60}dk erken gelecek! "
                    f"(Toplam indirim: {self.indirilen_toplam//3600}s {(self.indirilen_toplam%3600)//60}dk, "
                    f"Kalan: {self.kalan_sure//3600}s {(self.kalan_sure%3600)//60}dk)"
                )

    # ── /patron-sıralama ─────────────────────────────────────────
    @app_commands.command(name="patron-sıralama", description="Bu haftaki patron hasar sıralamasını gör.")
    async def patron_siralama(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        hafta_no = self._hafta_no()
        siralama = await database.patron_haftalik_siralama(hafta_no, limit=10)

        embed = discord.Embed(
            title="📊 Haftalık Patron Sıralaması",
            color=0xCC0000,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        if not siralama:
            embed.description = "Bu hafta henüz kimse patrona saldırmadı!"
        else:
            liste = self._haftalik_liste(siralama, interaction.guild)
            embed.description = liste
            embed.add_field(
                name="🏆 Haftalık Ödüller",
                value=f"🥇 1. → 3 {GEM}  ·  🥈 2. → 2 {GEM}  ·  🥉 3. → 1 {GEM}",
                inline=False,
            )

        embed.set_footer(text=f"Hafta: {hafta_no} • Ödüller Pazartesi 00:00 TR'de dağıtılır.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /patron-test ─────────────────────────────────────────────
    @app_commands.command(name="patron-test", description="Bulunduğun kanala test patronu spawn et.")
    @app_commands.checks.has_permissions(administrator=True)
    async def patron_test(self, interaction: discord.Interaction):
        if self.aktif_patron:
            await interaction.response.send_message(f"{FAIL_EMO} Zaten aktif bir patron var!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        kanal = interaction.channel
        patron_id          = f"test-{uuid.uuid4()}"
        test_hp            = 100  # Test için düşük HP
        self.patron_hp     = test_hp
        self.patron_max_hp = test_hp
        bitis_zamani       = datetime.now(timezone.utc) + timedelta(minutes=PATRON_SURE_DK)

        embed = discord.Embed(
            title="👹 Bir Patron Belirdi! *(TEST)*",
            description=(
                f"Güçlü bir patron sunucuya saldırıyor!\n\n"
                f"❤️ **Can:** {self._hp_bar(test_hp, test_hp)} `{test_hp}/{test_hp}`\n\n"
                f"⚔️ **Saldırı hakkın:** {PATRON_MAX_SALDIRI}\n"
                f"⏳ **Süre:** {PATRON_SURE_DK} dakika\n\n"
                f"Aşağıdaki butona tıklayarak patrona saldır!\n"
                f"Hafta sonunda en çok hasar veren **3 kişi** Gem ödülü kazanır!\n\n"
                f"🥇 **1.** → 3 {GEM}  |  🥈 **2.** → 2 {GEM}  |  🥉 **3.** → 1 {GEM}\n"
                f"*(Ödüller her Pazartesi 00:00 TR'de dağıtılır)*"
            ),
            color=0xCC0000,
        )
        embed.set_footer(text=f"{patron_id[:8]} • TEST MODU")

        view = SaldiriView(self)
        mesaj = await kanal.send(embed=embed, view=view)

        self.aktif_patron = {
            "mesaj":      mesaj,
            "patron_id":  patron_id,
            "bitis":      bitis_zamani,
            "katilimcilar": {},
        }

        log.info(f"TEST patron doğdu: {patron_id[:8]} kanal: {kanal.id}")
        await interaction.followup.send("✅ Test patronu spawn edildi!", ephemeral=True)

        # Süre dolunca bitir
        async def _test_sure():
            await asyncio.sleep(PATRON_SURE_DK * 60)
            if self.aktif_patron and self.aktif_patron["patron_id"] == patron_id:
                await self._patron_bitis(kacan=True)
        self.bot.loop.create_task(_test_sure())

    # ── /patron-durum ────────────────────────────────────────────
    @app_commands.command(name="patron-durum", description="Aktif patronun durumunu göster.")
    async def patron_durum(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.aktif_patron:
            await interaction.followup.send(
                f"{FAIL_EMO} Şu an aktif patron yok. Bekle bakalım!", ephemeral=True)
            return

        hp   = max(0, self.patron_hp)
        bitis = self.aktif_patron["bitis"]
        kalan = max(0, int((bitis - datetime.now(timezone.utc)).total_seconds()) // 60)
        katilimci = len(self.aktif_patron["katilimcilar"])

        embed = discord.Embed(
            title="👹 Patron Durumu",
            description=(
                f"❤️ **Can:** {self._hp_bar(hp, self.patron_max_hp)} `{hp}/{self.patron_max_hp}`\n"
                f"⏳ **Kalan süre:** {kalan} dakika\n"
                f"👥 **Katılımcı:** {katilimci} kişi"
            ),
            color=0xCC0000,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PatronCog(bot))
