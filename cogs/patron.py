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
        self.kalan_sure       = 0
        self.indirilen_toplam = 0
        self.unique_yazanlar  = set()
        self._hp_lock         = asyncio.Lock()
        self.bot.loop.create_task(self._dongu())
        self.bot.loop.create_task(self._perk_bildirim_dongu())

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

        patron_id    = str(uuid.uuid4())
        self.patron_hp = PATRON_HP
        bitis_zamani = datetime.now(timezone.utc) + timedelta(minutes=PATRON_SURE_DK)

        embed = discord.Embed(
            title="👹 Bir Patron Belirdi!",
            description=(
                f"Güçlü bir patron sunucuya saldırıyor!\n\n"
                f"❤️ **Can:** {self._hp_bar(PATRON_HP, PATRON_HP)} `{PATRON_HP}/{PATRON_HP}`\n\n"
                f"**⚔️ Saldırı hakkın:** {PATRON_MAX_SALDIRI}\n"
                f"**⏳ Süre:** {PATRON_SURE_DK} dakika\n\n"
                f"Aşağıdaki butona tıklayarak patrona saldır!\n"
                f"En çok hasar veren **3 kişi** Gem ödülü kazanır!\n\n"
                f"🥇 **1.** → 3 {GEM}  |  🥈 **2.** → 2 {GEM}  |  🥉 **3.** → 1 {GEM}"
            ),
            color=0xCC0000,
        )
        embed.set_footer(text=f"Patron ID: {patron_id[:8]} • {PATRON_SURE_DK} dakika içinde yenilmeli!")

        view = SaldiriView(self)

        try:
            dosya = discord.File(PATRON_IMG, filename="patron.png")
            embed.set_image(url="attachment://patron.png")
            mesaj = await kanal.send(file=dosya, embed=embed, view=view)
        except Exception:
            mesaj = await kanal.send(embed=embed, view=view)

        self.aktif_patron = {
            "mesaj":      mesaj,
            "patron_id":  patron_id,
            "bitis":      bitis_zamani,
            "katilimcilar": {},
        }

        log.info(f"Patron doğdu: {patron_id[:8]}")

        # 30 dakika bekle → süre dolunca bitir
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

            self.patron_hp -= hasar
            hp_simdi = max(0, self.patron_hp)

            # Katılımcı kaydı (in-memory)
            if uid not in self.aktif_patron["katilimcilar"]:
                self.aktif_patron["katilimcilar"][uid] = 0
            self.aktif_patron["katilimcilar"][uid] += hasar

        # DB'ye kaydet
        await database.patron_hasar_kaydet(patron_id, uid, hasar, 1)

        # Perk durumlarını al (görsel için)
        guclu_darbe = await database.perk_gunluk_limit_kontrol(uid, "patron_guclu_darbe")
        crit_hasar  = await database.perk_gunluk_limit_kontrol(uid, "patron_kritik_hasar")

        crit_txt  = " 💥 **KRİTİK!**" if crit else ""
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
        loop = asyncio.get_event_loop()
        buf  = await loop.run_in_executor(None, patron_gorseli_olustur,
                                          hp_simdi, PATRON_HP, hasar, crit,
                                          guclu_darbe, crit_hasar,
                                          interaction.user.display_name)

        dosya = discord.File(buf, filename="saldiri.png")
        embed = discord.Embed(
            title=f"{SWORD} Saldırı!",
            description=(
                f"{hasar_aciklama}\n"
                f"❤️ Patron canı: **{hp_simdi}/{PATRON_HP}**\n"
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

        crit_rate = 0.08 if await database.perk_gunluk_limit_kontrol(discord_id, "patron_kritik_sans") else 0.0
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
                        f"❤️ **Can:** {self._hp_bar(hp, PATRON_HP)} `{hp}/{PATRON_HP}`"
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
        self.aktif_patron = None
        self.patron_hp    = 0

        mesaj     = patron["mesaj"]
        patron_id = patron["patron_id"]
        kanal     = mesaj.channel

        # View'ı kapat
        try:
            await mesaj.edit(view=None)
        except Exception:
            pass

        if kacan:
            embed = discord.Embed(
                title="💨 Patron Kaçtı!",
                description="Patron zamanında yenilemedii... Güçlerinizi birleştirin!",
                color=0x95A5A6,
            )
            await kanal.send(embed=embed, delete_after=30)
            log.info(f"Patron kaçtı: {patron_id[:8]}")
            return

        # Ödül dağıt
        siralama = await database.patron_hasar_siralaması(patron_id, limit=3)
        oduller  = [3, 2, 1]
        madalya  = ["🥇", "🥈", "🥉"]

        embed = discord.Embed(
            title=f"{SKULL} Patron Yenildi!",
            description="Topluluk birlikte bu patronu devirdi! İşte en çok hasar verenler:",
            color=0xFFD700,
        )

        odul_satirlari = []
        for i, row in enumerate(siralama):
            gem_odul = oduller[i] if i < len(oduller) else 0
            uye = kanal.guild.get_member(row["discord_id"])
            isim = uye.display_name if uye else f"Kullanıcı#{row['discord_id']}"
            mention = uye.mention if uye else isim
            if gem_odul > 0:
                await database.add_gem(
                    row["discord_id"], gem_odul,
                    tip="patron_odul",
                    aciklama=f"Patron savaşı #{i+1}. sıra"
                )
                odul_satirlari.append(
                    f"{madalya[i]} **{isim}** — {row['toplam_hasar']} hasar → **+{gem_odul} {GEM}**"
                )

        embed.add_field(name="🏆 Sıralama & Ödüller", value="\n".join(odul_satirlari) or "—", inline=False)

        mentions = " ".join([kanal.guild.get_member(r["discord_id"]).mention
                              for r in siralama if kanal.guild.get_member(r["discord_id"])])

        await kanal.send(content=mentions if mentions else None, embed=embed)
        log.info(f"Patron yenildi: {patron_id[:8]} — {len(siralama)} kişi ödül aldı")

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
        if self.indirilen_toplam >= 1800:
            return

        self.unique_yazanlar.add(message.author.id)

        if len(self.unique_yazanlar) >= 10:
            indirim = 1800
            kalan_indirilebilir = 1800 - self.indirilen_toplam
            indirim = min(indirim, kalan_indirilebilir, self.kalan_sure - 10)
            if indirim > 0:
                self.kalan_sure       -= indirim
                self.indirilen_toplam += indirim
                self.unique_yazanlar   = set()
                log.info(
                    f"Patron {indirim//60}dk erken gelecek! "
                    f"(Kalan: {self.kalan_sure//3600}s {(self.kalan_sure%3600)//60}dk)"
                )

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
        kalan = max(0, (bitis - datetime.now(timezone.utc)).seconds // 60)
        katilimci = len(self.aktif_patron["katilimcilar"])

        embed = discord.Embed(
            title="👹 Patron Durumu",
            description=(
                f"❤️ **Can:** {self._hp_bar(hp, PATRON_HP)} `{hp}/{PATRON_HP}`\n"
                f"⏳ **Kalan süre:** {kalan} dakika\n"
                f"👥 **Katılımcı:** {katilimci} kişi"
            ),
            color=0xCC0000,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PatronCog(bot))
