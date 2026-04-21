"""cogs/yedek.py — Otomatik günlük DB yedekleme sistemi."""

import asyncio
import os
import subprocess
from datetime import datetime, timezone
from discord.ext import commands, tasks

from utils.logger import setup_logger

log = setup_logger("yedek")

# ── Ayarlar ──────────────────────────────────────────────────
PG_DUMP    = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
YEDEK_KLASOR = r"C:\Users\ALP\Desktop\Ascelia Yedek"
MAX_YEDEK  = 14  # Kaç günlük yedek saklansın


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

        # postgresql:// → postgres:// uyumluluğu
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        os.makedirs(YEDEK_KLASOR, exist_ok=True)

        tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        dosya = os.path.join(YEDEK_KLASOR, f"ascelia_{tarih}.dump")

        try:
            proc = await asyncio.create_subprocess_exec(
                PG_DUMP, "-Fc", db_url,
                stdout=open(dosya, "wb"),
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                boyut = os.path.getsize(dosya) // 1024
                log.info(f"✅ Yedek alındı: {dosya} ({boyut}KB)")
                await self._eski_yedekleri_temizle()
            else:
                log.error(f"❌ Yedek hatası: {stderr.decode()}")
                if os.path.exists(dosya):
                    os.remove(dosya)
        except Exception as e:
            log.error(f"❌ Yedek exception: {e}")

    async def _eski_yedekleri_temizle(self):
        """MAX_YEDEK'ten fazla dosya varsa en eskileri sil."""
        try:
            dosyalar = sorted([
                os.path.join(YEDEK_KLASOR, f)
                for f in os.listdir(YEDEK_KLASOR)
                if f.startswith("ascelia_") and f.endswith(".dump")
            ])
            silinecek = dosyalar[:-MAX_YEDEK] if len(dosyalar) > MAX_YEDEK else []
            for d in silinecek:
                os.remove(d)
                log.info(f"🗑️ Eski yedek silindi: {d}")
        except Exception as e:
            log.error(f"Temizleme hatası: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(YedekCog(bot))
