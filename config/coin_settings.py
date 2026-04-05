"""config/coin_settings.py — M2Board Coin sistemi ayarları."""
import os

# ── Hazine ────────────────────────────────────────────────
HAZINE_KANAL_ID   = int(os.getenv("HAZINE_KANAL_ID", "0"))
HAZINE_MIN_SAAT   = 1
HAZINE_MAX_SAAT   = 5
HAZINE_MIN_COIN   = 1
HAZINE_MAX_COIN   = 200

# ── Günlük Giriş ──────────────────────────────────────────
GUNLUK_MIN_COIN   = 1
GUNLUK_MAX_COIN   = 50

# ── Market (herkes için aynı) ─────────────────────────────
# gem: satın alımda verilecek bonus Gem miktarı (0 = yok)
MARKET_URUNLER = [
    {"id": "mp_100", "isim": "🎟️ 100 MP Kuponu", "fiyat": 500,  "gem": 0},
    {"id": "mp_200", "isim": "🎟️ 200 MP Kuponu", "fiyat": 1000, "gem": 0},
    {"id": "mp_300", "isim": "🎟️ 300 MP Kuponu", "fiyat": 1500, "gem": 1},
    {"id": "mp_400", "isim": "🎟️ 400 MP Kuponu", "fiyat": 2000, "gem": 2},
    {"id": "mp_500", "isim": "🎟️ 500 MP Kuponu", "fiyat": 2500, "gem": 3},
]

# ── Gem Sistemi ───────────────────────────────────────────
GEM_COIN_KURU     = 1000  # 1 Gem = 1000 Coin

# ── Patron ────────────────────────────────────────────────
PATRON_KANAL_ID   = int(os.getenv("PATRON_KANAL_ID", "0"))
PATRON_MIN_SAAT   = 20          # Günde 1 baskın — min 20 saat
PATRON_MAX_SAAT   = 24          # Günde 1 baskın — max 24 saat
PATRON_HP         = 1000        # Base HP (her yeni saldıran +300 ekler)
PATRON_HP_SCALING = 300         # Yeni katılımcı başına HP artışı
PATRON_SURE_DK    = 60          # Savaş süresi (dakika)
PATRON_MAX_SALDIRI = 3
PATRON_HASAR_MIN  = 20
PATRON_HASAR_MAX  = 80
PATRON_MAX_INDIRIM_SN = 21600   # Yazarak max 6 saat erken çağırılabilir
PATRON_INDIRIM_ESIK   = 5       # Her 5 unique yazan → 30 dk indirim

# ── Bildirim Kanalı ───────────────────────────────────────
BILDIRIM_KANAL_ID = int(os.getenv("BILDIRIM_KANAL_ID", "0"))

# ── Görev Rolleri ─────────────────────────────────────────
ROL_VANGUARD_ID   = int(os.getenv("ROL_VANGUARD_ID",  "0"))
ROL_HARBINGER_ID  = int(os.getenv("ROL_HARBINGER_ID", "0"))
ROL_SENTINEL_ID   = int(os.getenv("ROL_SENTINEL_ID",  "0"))
ROL_LUMINARY_ID   = int(os.getenv("ROL_LUMINARY_ID",  "0"))
