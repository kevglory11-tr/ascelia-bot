"""cogs/skor_tahmin.py — Maç skoru tahmin sistemi."""

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


class SkorModal(discord.ui.Modal, title="Maç Tahmini"):
    kazanan = discord.ui.TextInput(
        label="Kim kazanır?",
        placeholder="Örn: Galatasaray veya Beraberlik",
        min_length=2,
        max_length=50,
    )
    skor = discord.ui.TextInput(
        label="Maç sonucu ne olur?",
        placeholder="Örn: 2-0",
        min_length=3,
        max_length=10,
    )

    def __init__(self, mac_id: str, ev: str, dep: str):
        super().__init__()
        self.mac_id = mac_id
        self.ev     = ev
        self.dep    = dep

    async def on_submit(self, interaction: discord.Interaction):
        skor_val = self.skor.value.strip().replace(" ", "")
        parcalar = skor_val.split("-")
        if len(parcalar) != 2 or not all(p.isdigit() for p in parcalar):
            await interaction.response.send_message(
                "❌ Skor formatı hatalı! Örnek: `2-0` veya `1-1`", ephemeral=True
            )
            return

        async with database.pool.acquire() as conn:
            mac = await conn.fetchrow("SELECT kapali FROM mac_bilgi WHERE mac_id=$1", self.mac_id)
            if not mac or mac["kapali"]:
                await interaction.response.send_message("❌ Bu maçın tahminleri kapandı!", ephemeral=True)
                return

            onceki = await conn.fetchval(
                "SELECT skor FROM mac_tahmin WHERE mac_id=$1 AND discord_id=$2",
                self.mac_id, interaction.user.id
            )
            await conn.execute(
                """INSERT INTO mac_tahmin (mac_id, discord_id, skor, isim)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (mac_id, discord_id) DO UPDATE SET skor=$3, isim=$4, zaman=NOW()""",
                self.mac_id, interaction.user.id, skor_val, interaction.user.display_name
            )

        if onceki:
            await interaction.response.send_message(
                f"{OK} Tahminin güncellendi!\n"
                f"⚽ Kazanan: **{self.kazanan.value}**\n"
                f"📊 Skor: **{skor_val}**",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{OK} Tahminin kaydedildi!\n"
                f"⚽ Kazanan: **{self.kazanan.value}**\n"
                f"📊 Skor: **{skor_val}**\n\n"
                f"🎟️ İlk **5 doğru skor tahmini** → **100 MP Kuponu** kazanır!",
                ephemeral=True,
            )
        log.info(f"Tahmin: {interaction.user} → {self.kazanan.value} / {skor_val} ({self.mac_id})")


class TahminView(discord.ui.View):
    def __init__(self, mac_id: str, ev: str, dep: str):
        super().__init__(timeout=None)
        self.mac_id = mac_id
        self.ev     = ev
        self.dep    = dep

    @discord.ui.button(label="⚽ Tahmin Yap", style=discord.ButtonStyle.primary, custom_id="tahmin_yap_btn")
    async def tahmin_yap(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with database.pool.acquire() as conn:
            mac = await conn.fetchrow("SELECT kapali FROM mac_bilgi WHERE mac_id=$1", self.mac_id)
        if not mac or mac["kapali"]:
            await interaction.response.send_message("❌ Bu maçın tahminleri kapandı!", ephemeral=True)
            return
        await interaction.response.send_modal(SkorModal(self.mac_id, self.ev, self.dep))


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
                log.info(f"Tahminler {int(bekle//60)}dk {int(bekle%60)}s sonra kapanacak: {mac_id}")
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
                    embed = self._embed_olustur(mac, tahmin_sayisi, kapali=True)
                    await mesaj.edit(embed=embed, view=None)
                except Exception:
                    pass
            log.info(f"Tahminler kapandı: {mac_id}")
        except Exception as e:
            log.error(f"Otomatik kapama hatası ({mac_id}): {e}")

    def _embed_olustur(self, mac, tahmin_sayisi=0, kapali=False, gercek_skor=None) -> discord.Embed:
        embed = discord.Embed(
            title="⚽ Maç Skoru Tahmini",
            description=(
                f"📅 **{mac['mac_zamani']}**\n"
                f"👥 Tahmin sayısı: **{tahmin_sayisi}**\n\n"
                f"🏆 İlk **5 doğru tahmin** → 🎟️ **100 MP Kuponu**\n\n"
                + ("⏰ **Tahminler kapandı!**" if kapali else "⏳ Tahminler maç saatine kadar açık!")
            ),
            color=0x95A5A6 if kapali else 0x2ECC71,
        )
        embed.set_footer(text=f"Maç ID: {mac['mac_id']}")
        return embed

    def _admin_mi(self, interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        rol = discord.utils.get(interaction.guild.roles, name="Admin")
        return bool(rol and rol in interaction.user.roles)

    @app_commands.command(name="skor-tahmin", description="[Admin] Yeni maç tahmini oluştur.")
    @app_commands.describe(
        ev_takim="Ev sahibi takım adı", ev_logo="Ev sahibi logo URL",
        dep_takim="Deplasman takım adı", dep_logo="Deplasman logo URL",
        tarih="Maç tarihi (GG.AA.YYYY)", saat="Maç saati (SS:DD)",
        kanal="Tahminin yayınlanacağı kanal",
    )
    async def skor_tahmin(self, interaction: discord.Interaction,
        ev_takim: str, ev_logo: str, dep_takim: str, dep_logo: str,
        tarih: str, saat: str, kanal: discord.TextChannel):

        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            mac_zamani = datetime.strptime(f"{tarih} {saat}", "%d.%m.%Y %H:%M")
        except ValueError:
            await interaction.followup.send("❌ Örnek format: tarih `10.03.2026` saat `20:45`", ephemeral=True)
            return

        mac_id    = f"{ev_takim[:3].upper()}{dep_takim[:3].upper()}{mac_zamani.strftime('%d%m%H%M')}"
        zaman_str = mac_zamani.strftime("%d.%m.%Y %H:%M")

        async with database.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO mac_bilgi (mac_id,ev,ev_logo,dep,dep_logo,mac_zamani,kanal_id,kapali)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,FALSE)
                   ON CONFLICT (mac_id) DO UPDATE
                   SET ev=$2,ev_logo=$3,dep=$4,dep_logo=$5,mac_zamani=$6,kanal_id=$7,kapali=FALSE""",
                mac_id, ev_takim, ev_logo, dep_takim, dep_logo, zaman_str, kanal.id
            )

        # Banner görseli oluştur
        try:
            loop   = asyncio.get_event_loop()
            banner = await loop.run_in_executor(
                None, mac_banner_olustur, ev_logo, dep_logo, ev_takim, dep_takim
            )
            dosya  = discord.File(banner, filename="mac_banner.gif")
        except Exception as e:
            log.warning(f"Banner oluşturulamadı: {e}")
            dosya = None

        mac_row = {"mac_id": mac_id, "ev": ev_takim, "ev_logo": ev_logo,
                   "dep": dep_takim, "dep_logo": dep_logo, "mac_zamani": zaman_str, "kapali": False}
        embed   = self._embed_olustur(mac_row, 0, False)
        if dosya:
            embed.set_image(url="attachment://mac_banner.gif")

        view = TahminView(mac_id, ev_takim, dep_takim)
        if dosya:
            # GIF önce ayrı mesaj olarak gönder (embed set_image animasyonu dondurur)
            gif_mesaj = await kanal.send(file=dosya)
            mesaj = await kanal.send(embed=embed, view=view)
        else:
            mesaj = await kanal.send(embed=embed, view=view)

        async with database.pool.acquire() as conn:
            await conn.execute("UPDATE mac_bilgi SET mesaj_id=$1 WHERE mac_id=$2", mesaj.id, mac_id)

        await interaction.followup.send(
            f"{OK} Tahmin başlatıldı! ID: `{mac_id}`\n"
            f"Sonuç için: `/sonuclar {mac_id} <skor>`",
            ephemeral=True,
        )
        asyncio.create_task(self._otomatik_kapat(mac_id, zaman_str, kanal.id, mesaj.id))
        log.info(f"Yeni maç: {mac_id} — {ev_takim} vs {dep_takim}")

    @app_commands.command(name="sonuclar", description="[Admin] Maç sonucunu gir ve kazananları ilan et.")
    @app_commands.describe(
        mac_id="Maç ID'si",
        gercek_skor="Gerçek skor (örn: 2-1)",
        kazanan_takim="Kazanan takım adı (beraberlik için 'Beraberlik' yaz)",
    )
    async def sonuclar(self, interaction: discord.Interaction, mac_id: str, gercek_skor: str, kazanan_takim: str):
        if not self._admin_mi(interaction):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return

        await interaction.response.defer()

        async with database.pool.acquire() as conn:
            mac = await conn.fetchrow("SELECT * FROM mac_bilgi WHERE mac_id=$1", mac_id)
            if not mac:
                await interaction.followup.send(f"❌ `{mac_id}` bulunamadı!", ephemeral=True)
                return

            skor_val = gercek_skor.strip().replace(" ", "")
            if len(skor_val.split("-")) != 2:
                await interaction.followup.send("❌ Format: `2-1`", ephemeral=True)
                return

            await conn.execute("UPDATE mac_bilgi SET kapali=TRUE WHERE mac_id=$1", mac_id)
            kazananlar    = await conn.fetch(
                "SELECT * FROM mac_tahmin WHERE mac_id=$1 AND skor=$2 ORDER BY zaman ASC LIMIT 5",
                mac_id, skor_val
            )
            tahmin_sayisi = await conn.fetchval("SELECT COUNT(*) FROM mac_tahmin WHERE mac_id=$1", mac_id)

        # Kazanan takımın logosunu belirle
        if kazanan_takim.lower() in (mac["ev"].lower(), "ev", "home"):
            logo_url = mac["ev_logo"]
        elif kazanan_takim.lower() in (mac["dep"].lower(), "dep", "away"):
            logo_url = mac["dep_logo"]
        else:
            logo_url = None  # beraberlik

        embed = discord.Embed(
            title=f"{TROPHY} Maç Sonucu",
            description=(
                f"**{mac['ev']}  🆚  {mac['dep']}**\n\n"
                f"{COIN_ANIM} **Gerçek Skor: {gercek_skor}**\n"
                f"🏆 **Kazanan: {kazanan_takim}**\n\n"
                f"📊 Toplam tahmin: **{tahmin_sayisi}**\n"
                f"{OK} Doğru tahmin: **{len(kazananlar)}**\n"
            ),
            color=0xFFD700,
        )

        if logo_url:
            embed.set_thumbnail(url=logo_url)

        if kazananlar:
            embed.description += "\n🎟️ **100 MP Kupon Kazananları:**\n"
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
                    bitis = self._embed_olustur(mac, tahmin_sayisi, kapali=True)
                    bitis.add_field(name="🏆 Sonuç", value=f"Gerçek skor: **{gercek_skor}**", inline=False)
                    await mesaj.edit(embed=bitis, view=None)
                except Exception:
                    pass

        await interaction.followup.send(f"{OK} Sonuçlar ilan edildi! {len(kazananlar)} kazanan.", ephemeral=True)
        log.info(f"Sonuç: {mac_id} → {gercek_skor} | {len(kazananlar)} kazanan")


async def setup(bot: commands.Bot):
    await bot.add_cog(SkorTahminCog(bot))
