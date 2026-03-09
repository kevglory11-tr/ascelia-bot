"""
utils/dm_queue.py — Merkezi DM kuyruğu.

Tüm cog'ların kullandığı singleton DM queue.
Rate limit (40003) ve bot kısıtlaması (Forbidden) durumlarını
exponential backoff ile otomatik yönetir.
"""

import asyncio
import logging
from dataclasses import dataclass, field

import discord

log = logging.getLogger("dm_queue")


@dataclass
class _DMGorev:
    uye: discord.Member
    embed: discord.Embed
    view: discord.ui.View | None = None
    extra_url: str | None = None
    deneme: int = 0


class DMQueue:
    """Singleton DM kuyruğu — tüm cog'lardan kullanılır."""

    _instance: "DMQueue | None" = None

    def __new__(cls) -> "DMQueue":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._queue: asyncio.Queue[_DMGorev] = asyncio.Queue()
            cls._instance._worker_task: asyncio.Task | None = None
        return cls._instance

    # ── Yaşam döngüsü ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Bot hazır olunca çağır."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())
            log.info("DM kuyruğu başlatıldı")

    def stop(self) -> None:
        """Bot kapanınca çağır."""
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None

    # ── Public API ───────────────────────────────────────────────────────────

    async def gonder(
        self,
        uye: discord.Member,
        embed: discord.Embed,
        view: discord.ui.View | None = None,
        extra_url: str | None = None,
    ) -> None:
        """DM'i kuyruğa ekle."""
        await self._queue.put(_DMGorev(uye=uye, embed=embed, view=view, extra_url=extra_url))

    @property
    def kuyruk_boyutu(self) -> int:
        return self._queue.qsize()

    # ── Worker ───────────────────────────────────────────────────────────────

    async def _worker(self) -> None:
        backoff: float = 1.5  # DM'ler arası bekleme (sn)

        while True:
            gorev = await self._queue.get()
            try:
                kwargs: dict = {"embed": gorev.embed}
                if gorev.view:
                    kwargs["view"] = gorev.view
                await gorev.uye.send(**kwargs)
                if gorev.extra_url:
                    await gorev.uye.send(gorev.extra_url)
                backoff = 1.5  # Başarılıysa backoff'u sıfırla
                log.debug(f"DM gönderildi → {gorev.uye} ({gorev.uye.id})")

            except discord.Forbidden as e:
                kod = getattr(e, "code", 0)
                if kod == 50007:
                    log.debug(f"DM kapalı (50007) → {gorev.uye} ({gorev.uye.id})")
                else:
                    # Bot kısıtlı — 30sn bekle, bir kez daha dene
                    bekle = min(30 * (gorev.deneme + 1), 120)
                    log.warning(
                        f"DM Forbidden (kod={kod}) → {gorev.uye} ({gorev.uye.id}), "
                        f"{bekle}sn sonra tekrar (deneme {gorev.deneme + 1})"
                    )
                    if gorev.deneme < 2:
                        await asyncio.sleep(bekle)
                        gorev.deneme += 1
                        await self._queue.put(gorev)
                    else:
                        log.error(f"DM 3 denemede başarısız → {gorev.uye} ({gorev.uye.id})")

            except discord.HTTPException as e:
                if e.code == 40003:
                    # Rate limit — exponential backoff ile kuyruğa geri al
                    backoff = min(backoff * 2, 60)
                    log.warning(
                        f"DM rate limit (40003), {backoff:.0f}sn bekleniyor → "
                        f"{gorev.uye} ({gorev.uye.id})"
                    )
                    await asyncio.sleep(backoff)
                    await self._queue.put(gorev)
                else:
                    log.error(f"DM HTTPException ({e.code}) → {gorev.uye}: {e}")

            except Exception as e:
                log.error(f"DM beklenmeyen hata → {gorev.uye}: {e}", exc_info=True)

            finally:
                self._queue.task_done()
                await asyncio.sleep(backoff)


# Singleton instance — her yerden `from utils.dm_queue import dm_queue` ile kullan
dm_queue = DMQueue()
