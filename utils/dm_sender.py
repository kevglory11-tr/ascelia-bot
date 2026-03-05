"""utils/dm_sender.py — Toplu DM motoru."""

import asyncio
import logging
from dataclasses import dataclass, field

import discord
from config.settings import Settings

log = logging.getLogger("dm_sender")


@dataclass
class DMSonucu:
    basarili: list[str] = field(default_factory=list)
    basarisiz: list[str] = field(default_factory=list)

    @property
    def toplam(self) -> int:
        return len(self.basarili) + len(self.basarisiz)

    def ozet(self) -> str:
        return (
            f"📨 **{len(self.basarili)}** üyeye ulaşıldı\n"
            f"❌ **{len(self.basarisiz)}** üyeye ulaşılamadı *(DM kapalı)*\n"
            f"👥 Toplam hedef: **{self.toplam}** üye"
        )


async def herkese_gonder(
    guild: discord.Guild,
    embed: discord.Embed,
    settings: Settings | None = None,
    video_url: str = None,
    view: discord.ui.View = None,
) -> DMSonucu:
    s = settings or Settings()
    sonuc = DMSonucu()
    uyeler = [m for m in guild.members if not m.bot]
    log.info(f"Toplu DM başladı → {len(uyeler)} üye")

    for uye in uyeler:
        try:
            await uye.send(embed=embed, view=view)
            if video_url:
                await uye.send(video_url)
            sonuc.basarili.append(uye.name)
        except discord.Forbidden as e:
            hata_kodu = getattr(e, 'code', 0)
            sonuc.basarisiz.append(uye.name)
            if hata_kodu == 50007:
                log.debug(f"DM gönderilemedi (DM kapalı) [{uye.name}]")
            else:
                # Bot geçici kısıtlı olabilir — 30sn bekle, bir kez daha dene
                log.warning(f"DM Forbidden (kod={hata_kodu}) [{uye.name}], 30sn sonra tekrar denenecek")
                await asyncio.sleep(30)
                try:
                    await uye.send(embed=embed, view=view)
                    if video_url:
                        await uye.send(video_url)
                    sonuc.basarisiz.remove(uye.name)
                    sonuc.basarili.append(uye.name)
                    log.info(f"DM retry başarılı [{uye.name}]")
                except Exception:
                    log.warning(f"DM retry de başarısız [{uye.name}]")
        except discord.HTTPException as e:
            sonuc.basarisiz.append(uye.name)
            log.debug(f"DM HTTPException [{uye.name}]: kod={e.code} {e}")
        await asyncio.sleep(s.dm_bekleme)

    log.info(f"DM tamamlandı → ✓{len(sonuc.basarili)} ✗{len(sonuc.basarisiz)}")
    return sonuc
