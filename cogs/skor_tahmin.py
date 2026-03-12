"""cogs/skor_tahmin.py — Kim kazanır? tahmin sistemi."""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
import asyncio

import database
from utils.logger import setup_logger
from utils.mac_gorseli import mac_banner_olustur

log       = setup_logger("skor_tahmin")
TR_OFFSET = timedelta(hours=3)
OK        = "<a:check:1478394670856933429>"
M2B       = "<:m2bcoin:1480481551337783437>"
COIN_ANIM = "<a:coin:1478390167310958734>"
TROPHY    = "<a:bildirim:1478390691334979645>"


def _embed_olustur(mac, tahmin_sayisi=0, kapali=False, gercek_kazanan=None) -> discord.Embed:
    durum = "⏰ **Tahminler kapandı!**" if kapali else "⏳ Maç saatine kadar açık!"
    odul  = mac.get("odul", "100 MP Kuponu") if isinstance(mac, dict) else (mac["odul"] if "odul" in mac.keys() else "100 MP Kuponu")
    desc  = (
        f"📅 **{mac['mac_zamani']}**\n"
        f"👥 Tahmin sayısı: **{tahmin_sayisi}**\n\n"
        f"🏆 İlk **10 doğru tahmin** → 🎟️ **{odul}**\n\n"
        f"{durum}"
    )
    if gercek_kazanan:
        desc += f"\n\n✅ **Sonuç: {gercek_kazanan}**"

    embed = discord.Embed(
        title="⚽ Kim Kazanır?",
        description=desc,
        color=0x95A5A6 if kapali else 0x2ECC71,
    )
    embed.set_footer(text=f"Maç ID: {mac['mac_id']}")
    return embed


class TahminButon(discord.ui.Button):
    def __init__(self, mac_id: str, etiket: str, deger: str, style):
        super().__init__(
            label=etiket,
            style=style,
            custom_id=f"tahmin_{mac_id}_{deger}",
        )
        self.mac_id = mac_id
        self.deger  = deger

    async def callback(self, interaction: discord.Interaction):
        async with database.pool.acquire() as conn:
            mac = await conn.fetchrow("SELECT * FROM mac_bilgi WHERE mac_id=$1", self.mac_id)
            if not mac or mac["kapali"]:
                await interaction.response.send_message("❌ Tahminler kapandı!", ephemeral=True)
                return

            onceki = await conn.fetchval(
                "SELECT skor FROM mac_tahmin WHERE mac_id=$1 AND discord_id=$2",
                self.mac_id, interaction.user.id
            )
            if onceki:
                secim_text = {"ev": mac["ev"], "beraberlik": "Beraberlik", "dep": mac["dep"]}.get(onceki, onceki)
                await interaction.response.send_message(
                    f"❌ Zaten tahmin yaptın: **{secim_text}**\nTahminler değiştirilemez!",
                    ephemeral=True
                )
                return

            await conn.execute(
                """INSERT INTO mac_tahmin (mac_id, discord_id, skor, isim)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (mac_id, discord_id) DO NOTHING""",
                self.mac_id, interaction.user.id, self.deger, interaction.user.display_name
            )
            tahmin_sayisi = await conn.fetchval(
                "SELECT COUNT(*) FROM mac_tahmin WHERE mac_id=$1", self.mac_id
            )

        try:
            embed = _embed_olustur(mac, tahmin_sayisi, kapali=False)
            await interaction.message.edit(embed=embed)
        except Exception:
            pass

        secim_text = {"ev": mac["ev"], "beraberlik": "Beraberlik", "dep": mac["dep"]}.get(self.deger, self.deger)
        odul = mac["odul"] if "odul" in mac.keys() else "100 MP Kuponu"
        msg = (
            f"✅ Tahminin kaydedildi!\n"
            f"🏆 Seçimin: **{secim_text}**\n\n"
            f"🎟️ İlk **10 doğru tahmin** → **{odul}** kazanır!\n"
            f"⚠️ Tahminler **değiştirilemez!**"
        )
        await interaction.response.send_message(msg, ephemeral=True)


class TahminSecimView(discord.ui.View):
    def __init__(self, mac_id: str, ev: str, dep: str):
        super().__init__(timeout=None)
        self.add_item(TahminButon(mac_id, ev,           "ev",         discord.ButtonStyle.primary))
        self.add_item(TahminButon(mac_id, "Beraberlik", "beraberlik", discord.ButtonStyle.secondary))
        self.add_item(TahminButon(mac_id, dep,          "dep",        discord.ButtonStyle.danger))


class SkorTahminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self._kapat_gorevi_yukle())

    async def _kapat_gorevi_yukle(self):
        await self.bot.wait_until_ready()
        async with database.pool.acquire() as conn:
            maclar = await conn.fetch("SELECT * FROM mac_bilgi WHERE kapali=FALSE")
        for mac in maclar:
            asyncio.create_task(self._otomatik_kapat(
                mac["mac_id"], mac["mac_zamani"], mac["kanal_id"], mac["mesaj_id"]
            ))
        log.info(f"{len(maclar)} aktif maç yüklendi.")

    async def _otomatik_kapat(self, mac_id, mac_zamani_str, kanal_id, mesaj_id):
        try:
            mac_zamani = datetime.strptime(mac_zamani_str, "%d.%m.%Y %H:%M")
            mac_utc    = mac_zamani.replace(tzinfo=timezone(TR_OFFSET))
            bekle      = (mac_utc - datetime.now(timezone.utc)).total_seconds()
            if bekle > 0:
                await asyncio.sleep(bekle)

            async with database.pool.acquire() as conn:
                mac = await conn.fetchrow("SELECT * FROM mac_bilgi WHERE mac_id=$1", mac_id)
                if not mac or mac["kapali"]:
                    return
                await conn.execute("UPDATE mac_bilgi SET kapali=TRUE WHERE mac_id=$1", mac_id)
                tahmin_sayisi = await conn.fetchval("SELECT COUNT(*) FROM mac_tahmin WHERE mac_id=$1", mac_id)

            kanal = self.bot.get_channel(kanal_id)
            if kanal and mesaj_id:
                try:
                    mesaj = await kanal.fetch_message(mesaj_id)
                    embed = _embed_olustur(mac, tahmin_sayisi, kapali=True)
                    await mesaj.edit(embed=embed, view=None)
                except Exception:
                    pass
            log.info(f"Tahminler kapandı: {mac_id}")
        except Exception as e:
            log.error(f"Otomatik kapama hatası ({mac_id}): {e}")

    def _admin_mi(self, interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        rol = discord.utils.get(interaction.guild.roles, name="Admin")
        return bool(rol and rol in interaction.user.roles)

    @app_commands.command(name="skor-tahmin", description="[Admin] Kim kazanır tahmini başlat.")
    @app_commands.describe(
        ev_takim="Ev sahibi takım adı", ev_logo="Ev sahibi logo URL",
        dep_takim="Deplasman takım adı", dep_logo="Deplasman logo URL",
        tarih="Maç tarihi (GG.AA.YYYY)", saat="Maç saati (SS:DD)",
        kanal="Tahminin yayınlanacağı kanal",
        odul="Kazananlara verilecek ödül (örn: 100 MP Kuponu)",
    )
    async def skor_tahmin(self, interaction: discord.Interaction,
        ev_takim: str, ev_logo: str, dep_takim: str, dep_logo: str,
        tarih: str, saat: str, kanal: discord.TextChannel,
        odul: str = "100 MP Kuponu"):

        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            mac_zamani = datetime.strptime(f"{tarih} {saat}", "%d.%m.%Y %H:%M")
        except ValueError:
            await interaction.followup.send("❌ Format: tarih `10.03.2026` saat `20:45`", ephemeral=True)
            return

        mac_id    = f"{ev_takim[:3].upper()}{dep_takim[:3].upper()}{mac_zamani.strftime('%d%m%Y%H%M')}"
        zaman_str = mac_zamani.strftime("%d.%m.%Y %H:%M")

        async with database.pool.acquire() as conn:
            await conn.execute(
                "ALTER TABLE mac_bilgi ADD COLUMN IF NOT EXISTS odul TEXT DEFAULT '100 MP Kuponu'"
            )
            await conn.execute(
                """INSERT INTO mac_bilgi (mac_id,ev,ev_logo,dep,dep_logo,mac_zamani,kanal_id,kapali,odul)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,FALSE,$8)
                   ON CONFLICT (mac_id) DO UPDATE
                   SET ev=$2,ev_logo=$3,dep=$4,dep_logo=$5,mac_zamani=$6,kanal_id=$7,kapali=FALSE,odul=$8""",
                mac_id, ev_takim, ev_logo, dep_takim, dep_logo, zaman_str, kanal.id, odul
            )

        try:
            loop   = asyncio.get_event_loop()
            banner = await loop.run_in_executor(
                None, mac_banner_olustur, ev_logo, dep_logo, ev_takim, dep_takim
            )
            dosya = discord.File(banner, filename="mac_banner.gif")
        except Exception as e:
            log.warning(f"Banner oluşturulamadı: {e}")
            dosya = None

        mac_row = {"mac_id": mac_id, "ev": ev_takim, "ev_logo": ev_logo,
                   "dep": dep_takim, "dep_logo": dep_logo, "mac_zamani": zaman_str,
                   "kapali": False, "odul": odul}
        embed = _embed_olustur(mac_row, 0, False)
        if dosya:
            embed.set_image(url="attachment://mac_banner.gif")

        view = TahminSecimView(mac_id, ev_takim, dep_takim)
        if dosya:
            await kanal.send(file=dosya)
        mesaj = await kanal.send(embed=embed, view=view)

        async with database.pool.acquire() as conn:
            await conn.execute("UPDATE mac_bilgi SET mesaj_id=$1 WHERE mac_id=$2", mesaj.id, mac_id)

        await interaction.followup.send(
            f"{OK} Tahmin başlatıldı! ID: `{mac_id}`\nSonuç için: `/sonuclar {mac_id} ev/dep/beraberlik`",
            ephemeral=True,
        )
        asyncio.create_task(self._otomatik_kapat(mac_id, zaman_str, kanal.id, mesaj.id))
        log.info(f"Yeni maç: {mac_id} — {ev_takim} vs {dep_takim} | ödül: {odul}")

    @app_commands.command(name="sonuclar", description="[Admin] Maç sonucunu gir ve kazananları ilan et.")
    @app_commands.describe(
        mac_id="Maç ID'si",
        kazanan="Kazanan takım adı (örn: Fenerbahçe) veya 'Beraberlik'",
        gercek_skor="Gerçek skor (görüntü için, örn: 2-1)",
    )
    async def sonuclar(self, interaction: discord.Interaction,
                       mac_id: str, kazanan: str, gercek_skor: str = ""):
        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer()

        async with database.pool.acquire() as conn:
            mac = await conn.fetchrow("SELECT * FROM mac_bilgi WHERE mac_id=$1", mac_id)
            if not mac:
                await interaction.followup.send(f"❌ `{mac_id}` bulunamadı!", ephemeral=True)
                return

        # Girilen takım adını ev/dep/beraberlik değerine çevir
        kazanan_temiz = kazanan.strip().lower()
        if kazanan_temiz in ("beraberlik", "berabere", "draw"):
            kazanan_deger = "beraberlik"
            kazanan_text  = "Beraberlik"
        elif kazanan_temiz == mac["ev"].strip().lower():
            kazanan_deger = "ev"
            kazanan_text  = mac["ev"]
        elif kazanan_temiz == mac["dep"].strip().lower():
            kazanan_deger = "dep"
            kazanan_text  = mac["dep"]
        else:
            await interaction.followup.send(
                f"❌ Takım adı tanınamadı!\n"
                f"Geçerli seçenekler: `{mac['ev']}`, `{mac['dep']}`, `Beraberlik`",
                ephemeral=True
            )
            return

        async with database.pool.acquire() as conn:
            await conn.execute(
                "UPDATE mac_bilgi SET kapali=TRUE, gercek_skor=$2 WHERE mac_id=$1",
                mac_id, kazanan_deger
            )
            kazananlar = await conn.fetch(
                "SELECT * FROM mac_tahmin WHERE mac_id=$1 AND skor=$2 ORDER BY zaman ASC LIMIT 10",
                mac_id, kazanan_deger
            )
            tahmin_sayisi = await conn.fetchval(
                "SELECT COUNT(*) FROM mac_tahmin WHERE mac_id=$1", mac_id
            )

        odul = mac["odul"] if "odul" in mac.keys() else "100 MP Kuponu"

        embed = discord.Embed(
            title=f"{TROPHY} Maç Sonucu",
            description=(
                f"**{mac['ev']}  🆚  {mac['dep']}**\n\n"
                + (f"{COIN_ANIM} **Skor: {gercek_skor}**\n" if gercek_skor else "")
                + f"🏆 **Kazanan: {kazanan_text}**\n\n"
                f"📊 Toplam tahmin: **{tahmin_sayisi}**\n"
                f"✅ Doğru tahmin: **{len(kazananlar)}**\n"
            ),
            color=0xFFD700,
        )

        if kazanan_deger == "ev":
            embed.set_thumbnail(url=mac["ev_logo"])
        elif kazanan_deger == "dep":
            embed.set_thumbnail(url=mac["dep_logo"])

        if kazananlar:
            embed.description += f"\n🎟️ **{odul} Kazananları:**\n"
            for i, row in enumerate(kazananlar, 1):
                uye     = interaction.guild.get_member(row["discord_id"])
                mention = uye.mention if uye else row["isim"]
                embed.description += f"> **{i}.** {mention}\n"
            embed.description += "\n⚠️ Kazananlar ticket açsın!"
        else:
            embed.description += "\n😔 Doğru tahmin yapan olmadı!"

        embed.set_footer(text=f"Maç ID: {mac_id}")

        kanal = self.bot.get_channel(mac["kanal_id"])
        if kanal:
            await kanal.send(embed=embed)
            if mac["mesaj_id"]:
                try:
                    mesaj = await kanal.fetch_message(mac["mesaj_id"])
                    bitis = _embed_olustur(mac, tahmin_sayisi, kapali=True, gercek_kazanan=kazanan_text)
                    await mesaj.edit(embed=bitis, view=None)
                except Exception:
                    pass

        await interaction.followup.send(f"{OK} Sonuç kaydedildi!", ephemeral=True)
        log.info(f"Sonuç: {mac_id} → {kazanan_deger} | {len(kazananlar)} kazanan")

    @app_commands.command(name="tahmin-sıralaması", description="En başarılı tahmin yapanları gör!")
    async def tahmin_siralaması(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with database.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    t.discord_id,
                    t.isim,
                    COUNT(*) FILTER (WHERE t.skor = b.gercek_skor) AS dogru,
                    COUNT(*) AS toplam
                FROM mac_tahmin t
                JOIN mac_bilgi b ON t.mac_id = b.mac_id
                WHERE b.kapali = TRUE AND b.gercek_skor IS NOT NULL
                GROUP BY t.discord_id, t.isim
                HAVING COUNT(*) > 0
                ORDER BY dogru DESC, toplam ASC
                LIMIT 10
            """)

            # Her kullanıcı için güncel seri hesapla
            seri_map = {}
            for row in rows:
                gecmis = await conn.fetch("""
                    SELECT t.skor, b.gercek_skor
                    FROM mac_tahmin t
                    JOIN mac_bilgi b ON t.mac_id = b.mac_id
                    WHERE t.discord_id = $1
                      AND b.kapali = TRUE
                      AND b.gercek_skor IS NOT NULL
                    ORDER BY b.mac_zamani DESC
                """, row["discord_id"])
                seri = 0
                for g in gecmis:
                    if g["skor"] == g["gercek_skor"]:
                        seri += 1
                    else:
                        break
                seri_map[row["discord_id"]] = seri

        if not rows:
            await interaction.followup.send("Henüz sonuçlanmış maç tahmini yok!", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Tahmin Sıralaması", description="", color=0xFFD700)
        madalyalar = ["<a:gold:1478525208766709833>", "<a:silver:1478525216069259487>", "<a:bronze:1478525229583302656>"]
        siralama   = ""
        for i, row in enumerate(rows):
            madalya   = madalyalar[i] if i < 3 else f"`{i+1}.`"
            oran      = f"{row['dogru']}/{row['toplam']}"
            yuzde     = int(row["dogru"] / row["toplam"] * 100)
            seri      = seri_map.get(row["discord_id"], 0)
            seri_text = f" 🔥 **{seri} seri**" if seri >= 2 else ""
            siralama += f"{madalya} **{row['isim']}** — {oran} doğru (%{yuzde}){seri_text}\n"

        embed.description = siralama
        embed.set_footer(text="Sonuçlanmış maçlar baz alınır • 🔥 = üst üste doğru tahmin")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SkorTahminCog(bot))
