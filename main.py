"""
╔══════════════════════════════════════════════════════════════╗
║          M2BOARD BOT  —  main.py                            ║
║          Giriş noktası. Sadece buradan başlatılır.          ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import os
import sys

import discord
from discord.ext import commands

from utils.logger import setup_logger
from config.settings import Settings

log = setup_logger("main")

COGS = [
    "cogs.yardim",
    "cogs.sss",
    "cogs.duyuru",
    "cogs.status",
    "cogs.ticket",
    "cogs.basvuru",
    "cogs.dogrulama",
    "cogs.oneri_sikayet",
    "cogs.autoresponder",
]


class M2BoardBot(commands.Bot):

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members         = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.settings = Settings()

    async def setup_hook(self) -> None:
        await self._cogleri_yukle()

    async def _cogleri_yukle(self) -> None:
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"✅ Cog yüklendi: {cog}")
            except Exception as e:
                log.error(f"❌ Cog yüklenemedi: {cog} — {e}", exc_info=True)

    async def on_ready(self) -> None:
        log.info(f"🤖 Bot aktif: {self.user} (ID: {self.user.id})")
        log.info(f"📡 Sunucu sayısı: {len(self.guilds)}")
        try:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(f"🔄 {len(synced)} slash komutu senkronize edildi ({guild.name})")
            # Global komutları temizle (duplicate önlemek için)
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
        except Exception as e:
            log.error(f"Komut sync hatası: {e}", exc_info=True)

    async def on_error(self, event: str, *args, **kwargs) -> None:
        log.error(f"Event hatası [{event}]:", exc_info=True)


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN bulunamadı! .env dosyasını kontrol et.")
        sys.exit(1)

    bot = M2BoardBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
