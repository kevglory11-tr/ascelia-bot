"""cogs/yedek.py — Otomatik gunluk DB yedekleme sistemi.

Local (Windows): Masaustu/Ascelia Yedek klasorune kaydeder.
Railway (production): Discord'daki YEDEK_KANAL_ID kanalina yukler.
"""

import asyncio
import io
import os
import shutil
import tempfile
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils.logger import setup_logger

log = setup_logger("yedek")

_pg_dump_local = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
PG_DUMP      = _pg_dump_local if os.path.exists(_pg_dump_local) else (shutil.which("pg_dump") or "pg_dump")
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
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            log.error("DATABASE_URL bulunamadı, yedek alınamadı!")
            return
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        tarih     = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        dosya_adi = f"ascelia_{tarih}.dump"

        # pg_dump çıktısını geçici dosyaya yaz
        with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
            tmp_yol = tmp.name

        try:
            proc = await asyncio.create_subprocess_exec(
                PG_DUMP, "-Fc", db_url,
                stdout=open(tmp_yol, "wb"),
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                log.error(f"pg_dump hatası: {stderr.decode()}")
                return

            boyut = os.path.getsize(tmp_yol) // 1024
            log.info(f"pg_dump tamamlandı: {dosya_adi} ({boyut} KB)")

            if IS_LOCAL:
                await self._kaydet_local(tmp_yol, dosya_adi)
            else:
                await self._yukle_discord(tmp_yol, dosya_adi, boyut)

        except Exception as e:
            log.error(f"Yedek exception: {e}", exc_info=True)
        finally:
            if os.path.exists(tmp_yol):
                os.remove(tmp_yol)

    async def _kaydet_local(self, tmp_yol: str, dosya_adi: str):
        os.makedirs(YEDEK_KLASOR, exist_ok=True)
        hedef = os.path.join(YEDEK_KLASOR, dosya_adi)
        os.replace(tmp_yol, hedef)
        log.info(f"✅ Local yedek: {hedef}")
        await self._eski_yedekleri_temizle()

    async def _yukle_discord(self, tmp_yol: str, dosya_adi: str, boyut_kb: int):
        kanal_id = int(os.getenv("YEDEK_KANAL_ID", "0"))
        if not kanal_id:
            log.error("YEDEK_KANAL_ID tanımlı değil — Railway yedek atlandı!")
            return

        kanal = self.bot.get_channel(kanal_id)
        if not kanal:
            log.error(f"Yedek kanalı bulunamadı: {kanal_id}")
            return

        # 25 MB Discord limit kontrolü
        if boyut_kb > 24_000:
            log.warning(f"Yedek dosyası çok büyük ({boyut_kb} KB) — Discord limitini aşıyor.")
            return

        with open(tmp_yol, "rb") as f:
            dosya = discord.File(f, filename=dosya_adi)
            embed = discord.Embed(
                title="🗄️ Otomatik DB Yedek",
                description=f"`{dosya_adi}` — **{boyut_kb} KB**",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="Geri yüklemek için: pg_restore -d <DB_URL> <dosya>")
            await kanal.send(embed=embed, file=dosya)

        log.info(f"✅ Railway yedek Discord'a yüklendi: {dosya_adi}")

    async def _eski_yedekleri_temizle(self):
        try:
            dosyalar = sorted([
                os.path.join(YEDEK_KLASOR, f)
                for f in os.listdir(YEDEK_KLASOR)
                if f.startswith("ascelia_") and f.endswith(".dump")
            ])
            for d in dosyalar[:-MAX_YEDEK]:
                os.remove(d)
                log.info(f"Eski yedek silindi: {d}")
        except Exception as e:
            log.error(f"Temizleme hatası: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(YedekCog(bot))
