# cogs/yedek.py - Otomatik gunluk DB yedekleme
# pg_dump gerektirmez, asyncpg ile direkt CSV/ZIP olusturur.
# Local: Masaustu/Ascelia Yedek klasorune kaydeder
# Railway: YEDEK_KANAL_ID Discord kanalina yukler

import io
import os
import zipfile
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

import database
from utils.logger import setup_logger

log = setup_logger("yedek")

YEDEK_KLASOR = r"C:\Users\ALP\Desktop\Ascelia Yedek"
MAX_YEDEK    = 14
IS_LOCAL     = os.path.exists(r"C:\Users\ALP\Desktop")


class YedekCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gunluk_yedek.start()

    def cog_unload(self):
        self.gunluk_yedek.cancel()

    @tasks.loop(hours=24)
    async def gunluk_yedek(self):
        await self._yedek_al()

    @gunluk_yedek.before_loop
    async def before_yedek(self):
        await self.bot.wait_until_ready()

    async def _yedek_al(self):
        if not database.pool:
            log.error("DB pool hazir degil, yedek atlanidi!")
            return

        tarih     = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        dosya_adi = f"ascelia_{tarih}.zip"

        try:
            zip_buf = io.BytesIO()

            async with database.pool.acquire() as conn:
                tables = await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                )

                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for trow in tables:
                        table = trow["tablename"]
                        try:
                            csv_buf = io.BytesIO()
                            await conn.copy_from_table(
                                table, output=csv_buf, format="csv", header=True
                            )
                            csv_buf.seek(0)
                            zf.writestr(f"{table}.csv", csv_buf.read())
                        except Exception as e:
                            log.warning(f"Tablo atlanidi ({table}): {e}")

            zip_buf.seek(0)
            boyut_kb = zip_buf.getbuffer().nbytes // 1024
            log.info(f"Yedek olusturuldu: {dosya_adi} ({boyut_kb} KB)")

            if IS_LOCAL:
                await self._kaydet_local(zip_buf, dosya_adi)
            else:
                await self._yukle_discord(zip_buf, dosya_adi, boyut_kb)

        except Exception as e:
            log.error(f"Yedek exception: {e}", exc_info=True)

    async def _kaydet_local(self, buf: io.BytesIO, dosya_adi: str):
        os.makedirs(YEDEK_KLASOR, exist_ok=True)
        hedef = os.path.join(YEDEK_KLASOR, dosya_adi)
        with open(hedef, "wb") as f:
            f.write(buf.read())
        log.info(f"Local yedek kaydedildi: {hedef}")
        await self._eski_yedekleri_temizle()

    async def _yukle_discord(self, buf: io.BytesIO, dosya_adi: str, boyut_kb: int):
        kanal_id = int(os.getenv("YEDEK_KANAL_ID", "0"))
        if not kanal_id:
            log.error("YEDEK_KANAL_ID tanimli degil!")
            return

        kanal = self.bot.get_channel(kanal_id)
        if not kanal:
            log.error(f"Yedek kanali bulunamadi: {kanal_id}")
            return

        if boyut_kb > 24_000:
            log.warning(f"Yedek cok buyuk ({boyut_kb} KB), Discord limiti asiliyor.")
            return

        dosya = discord.File(buf, filename=dosya_adi)
        embed = discord.Embed(
            title="DB Yedek",
            description=f"`{dosya_adi}` — **{boyut_kb} KB**",
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Geri yuklemek icin her tablo icin: COPY table FROM 'file.csv' CSV HEADER")
        await kanal.send(embed=embed, file=dosya)
        log.info(f"Railway yedek Discord kanalina yuklendi: {dosya_adi}")

    async def _eski_yedekleri_temizle(self):
        try:
            dosyalar = sorted([
                os.path.join(YEDEK_KLASOR, f)
                for f in os.listdir(YEDEK_KLASOR)
                if f.startswith("ascelia_") and f.endswith(".zip")
            ])
            for d in dosyalar[:-MAX_YEDEK]:
                os.remove(d)
                log.info(f"Eski yedek silindi: {d}")
        except Exception as e:
            log.error(f"Temizleme hatasi: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(YedekCog(bot))
