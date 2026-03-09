"""
utils/dm_sender.py — Toplu DM motoru.

Tüm üyelere DM gönderir. Rate limit (40003) ve Forbidden hatalarını
hata koduna göre ayırt eder, exponential backoff uygular.
"""

import asyncio
import logging
from dataclasses import dataclass, field

import discord
from config.settings import Settings

log = logging.getLogger("dm_sender")

_MAX_BACKOFF = 60.0
_FORBIDDEN_BEKLE = 30.0


@dataclass
class DMSonucu:
    basarili:  list[str] = field(default_factory=list)
    basarisiz: list[str] = field(default_factory=list)

    @property
    def toplam(self) -> int:
        return len(self.basarili) + len(self.basarisiz)

    def ozet(self) -> str:
        return (
            f"📨 **{len(self.basarili)}** üyeye ulaşıldı\n"
            f"❌ **{len(self.basarisiz)}** üyeye ulaşılamadı *(DM kapalı / kısıtlı)*\n"
            f"👥 Toplam hedef: **{self.toplam}** üye"
        )


async def _dm_gonder_guvenli(
    uye: discord.Member,
    embed: discord.Embed,
    view,
    video_url,
    bekleme: float,
) -> bool:
    for deneme in range(3):
        try:
            await uye.send(embed=embed, view=view)
            if video_url:
                await uye.send(video_url)
            return True
        except discord.Forbidden as e:
            kod = getattr(e, "code", 0)
            if kod == 50007:
                log.debug(f"DM kapalı (50007) → {uye.name}")
                return False
            else:
                bekle = _FORBIDDEN_BEKLE * (deneme + 1)
                log.warning(f"DM Forbidden (kod={kod}) → {uye.name}, {bekle:.0f}sn (deneme {deneme+1}/3)")
                if deneme < 2:
                    await asyncio.sleep(bekle)
                    continue
                return False
        except discord.HTTPException as e:
            if e.code == 40003:
                bekle = min(bekleme * (2 ** deneme), _MAX_BACKOFF)
                log.warning(f"DM rate limit (40003) → {uye.name}, {bekle:.0f}sn (deneme {deneme+1}/3)")
                await asyncio.sleep(bekle)
                continue
            else:
                log.error(f"DM HTTPException ({e.code}) → {uye.name}: {e}")
                return False
        except Exception as e:
            log.error(f"DM beklenmeyen hata → {uye.name}: {e}", exc_info=True)
            return False
    return False


async def herkese_gonder(
    guild: discord.Guild,
    embed: discord.Embed,
    settings=None,
    video_url=None,
    view=None,
) -> DMSonucu:
    s = settings or Settings()
    sonuc = DMSonucu()
    uyeler = [m for m in guild.members if not m.bot]
    log.info(f"Toplu DM başladı → {len(uyeler)} üye")
    bekleme = s.dm_bekleme

    for i, uye in enumerate(uyeler):
        basarili = await _dm_gonder_guvenli(uye, embed, view, video_url, bekleme)
        if basarili:
            sonuc.basarili.append(uye.name)
        else:
            sonuc.basarisiz.append(uye.name)
        if (i + 1) % 50 == 0:
            log.info(f"Toplu DM → {i+1}/{len(uyeler)} ✓{len(sonuc.basarili)} ✗{len(sonuc.basarisiz)}")
        await asyncio.sleep(bekleme)

    log.info(f"Toplu DM tamamlandı → ✓{len(sonuc.basarili)} ✗{len(sonuc.basarisiz)} / {sonuc.toplam}")
    return sonuc
