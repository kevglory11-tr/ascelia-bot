"""config/coin_settings.py — M2Board Coin sistemi ayarları."""
import os

# ── Hazine ────────────────────────────────────────────────
HAZINE_KANAL_ID   = int(os.getenv("HAZINE_KANAL_ID", "0"))
HAZINE_MIN_SAAT   = 0.01
HAZINE_MAX_SAAT   = 0.02
HAZINE_MIN_COIN   = 1
HAZINE_MAX_COIN   = 200

# ── Günlük Giriş ──────────────────────────────────────────
GUNLUK_MIN_COIN   = 1
GUNLUK_MAX_COIN   = 50

# ── Market (herkes için aynı) ─────────────────────────────
MARKET_URUNLER = [
    {"id": "mp_10",  "isim": "🎟️ 10 MP Kuponu",  "fiyat": 50},
    {"id": "mp_20",  "isim": "🎟️ 20 MP Kuponu",  "fiyat": 100},
    {"id": "mp_30",  "isim": "🎟️ 30 MP Kuponu",  "fiyat": 200},
    {"id": "mp_40",  "isim": "🎟️ 40 MP Kuponu",  "fiyat": 250},
    {"id": "mp_50",  "isim": "🎟️ 50 MP Kuponu",  "fiyat": 300},
    {"id": "mp_100", "isim": "🎟️ 100 MP Kuponu", "fiyat": 400},
    {"id": "mp_150", "isim": "🎟️ 150 MP Kuponu", "fiyat": 500},
    {"id": "mp_200", "isim": "🎟️ 200 MP Kuponu", "fiyat": 1000},
]
