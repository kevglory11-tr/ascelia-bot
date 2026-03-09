"""
utils/cooldown.py — Slash komutlar ve dropdown'lar için cooldown yöneticisi.

app_commands.checks.cooldown sadece komutlarda çalışır.
Select/Button callback'leri için bu sınıfı kullan.
"""

import time
from collections import defaultdict


class CooldownManager:
    """
    Per-key cooldown takipçisi.

    Kullanım:
        kalan = cooldown.kontrol(f"ticket:{user_id}", sure=30)
        if kalan:
            await interaction.followup.send(f"⏳ {kalan:.0f}sn bekle.", ephemeral=True)
            return
    """

    def __init__(self) -> None:
        self._kayitlar: dict[str, float] = defaultdict(float)

    def kontrol(self, anahtar: str, sure: float) -> float | None:
        """
        Cooldown kontrolü yap.
        - Cooldown'daysa: kalan süreyi (float) döndürür.
        - Cooldown dolmuşsa: None döndürür ve zamanı günceller.
        """
        simdi = time.monotonic()
        gecen = simdi - self._kayitlar[anahtar]
        kalan = sure - gecen
        if kalan > 0:
            return kalan
        self._kayitlar[anahtar] = simdi
        return None

    def sifirla(self, anahtar: str) -> None:
        """Belirli bir anahtarın cooldown'ını sıfırla."""
        self._kayitlar.pop(anahtar, None)

    def toplu_temizle(self, sure: float) -> None:
        """Süresi dolmuş tüm kayıtları temizle (bellek optimizasyonu)."""
        simdi = time.monotonic()
        silincekler = [k for k, v in self._kayitlar.items() if simdi - v > sure]
        for k in silincekler:
            del self._kayitlar[k]


# Her sistem için ayrı cooldown instance — karışmasın
ticket_cooldown   = CooldownManager()   # 30 saniye
basvuru_cooldown  = CooldownManager()   # 5 dakika (300 sn)
oneri_cooldown    = CooldownManager()   # 10 dakika (600 sn)
sikayet_cooldown  = CooldownManager()   # 10 dakika (600 sn)
