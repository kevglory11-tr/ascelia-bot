"""config/coin_settings.py — M2Board Coin sistemi ayarları."""
import os

# ── Hazine ────────────────────────────────────────────────
HAZINE_KANAL_ID   = int(os.getenv("HAZINE_KANAL_ID", "0"))
HAZINE_MIN_SAAT   = 2
HAZINE_MAX_SAAT   = 6
HAZINE_MIN_COIN   = 1
HAZINE_MAX_COIN   = 100

# ── Günlük Giriş ──────────────────────────────────────────
GUNLUK_MIN_COIN   = 1
GUNLUK_MAX_COIN   = 50

# ── Market (herkes için aynı) ─────────────────────────────
MARKET_URUNLER = [
    {"id": "mp_100", "isim": "🎟️ 100 MP Kuponu", "fiyat": 500},
    {"id": "mp_150", "isim": "🎟️ 150 MP Kuponu", "fiyat": 750},
    {"id": "mp_200", "isim": "🎟️ 200 MP Kuponu", "fiyat": 1000},
    {"id": "mp_250", "isim": "🎟️ 250 MP Kuponu", "fiyat": 1500},
    {"id": "mp_300", "isim": "🎟️ 300 MP Kuponu", "fiyat": 2000},
    {"id": "mp_350", "isim": "🎟️ 350 MP Kuponu", "fiyat": 2500},
    {"id": "mp_400", "isim": "🎟️ 400 MP Kuponu", "fiyat": 3000},
    {"id": "mp_450", "isim": "🎟️ 450 MP Kuponu", "fiyat": 4000},
    {"id": "mp_500", "isim": "🎟️ 500 MP Kuponu", "fiyat": 5000},
]
