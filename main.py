"""
╔══════════════════════════════════════════════════════════════╗
║          ASCELIA BOT  —  main.py                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys

import discord
from discord.ext import commands

from utils.logger import setup_logger
from utils.dm_queue import dm_queue
from config.settings import Settings
import database

log = setup_logger("main")

COGS = [
    # ── Mevcut sistemler ─────────────────────────────────────
    "cogs.yardim",
    "cogs.sss",
    "cogs.status",
    "cogs.ticket",
    "cogs.basvuru",
    "cogs.dogrulama",
    "cogs.oneri_sikayet",
    "cogs.autoresponder",
    # ── Coin sistemi ─────────────────────────────────────────
    "cogs.hazine",
    "cogs.gunluk_giris",
    "cogs.kasa",
    "cogs.coin_market",

    "cogs.admin_coin",
    "cogs.gunluk_gorev",
    "cogs.gem_magaza",
    "cogs.patron",
    "cogs.skor_tahmin",
    "cogs.atam",
    "cogs.referans",
    # ── Ticket komutları ─────────────────────────────────────
    "cogs.ticket_komutlar",
    # ── Sistem ───────────────────────────────────────────────
    "cogs.yedek",
    "cogs.hatirlatici",
]


class AsceliaBot(commands.Bot):

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members         = True
        intents.message_content = True
        intents.reactions       = True   # Hazine reaksiyonları için

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.settings = Settings()

    async def setup_hook(self) -> None:
        await database.init_pool()
        await self._cogleri_yukle()

    async def _cogleri_yukle(self) -> None:
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"✅ Cog yüklendi: {cog}")
            except Exception as e:
                log.error(f"❌ Cog yüklenemedi: {cog} — {e}", exc_info=True)

    async def on_ready(self) -> None:
        dm_queue.start()
        log.info(f"🤖 Bot aktif: {self.user} (ID: {self.user.id})")
        try:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(f"🔄 {len(synced)} komut sync edildi ({guild.name})")
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
        except Exception as e:
            log.error(f"Sync hatası: {e}", exc_info=True)

    async def close(self) -> None:
        dm_queue.stop()
        await super().close()

    async def on_error(self, event: str, *args, **kwargs) -> None:
        log.error(f"Event hatası [{event}]:", exc_info=True)


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN bulunamadı!")
        sys.exit(1)

    bot = AsceliaBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
