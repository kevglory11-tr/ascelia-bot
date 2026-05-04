"""config/coin_settings.py — M2Board Coin sistemi ayarları."""
import os

# ── Hazine ────────────────────────────────────────────────
HAZINE_KANAL_ID   = int(os.getenv("HAZINE_KANAL_ID", "0"))
HAZINE_MIN_SAAT   = 1
HAZINE_MAX_SAAT   = 2
HAZINE_MIN_COIN   = 1
HAZINE_MAX_COIN   = 200

# ── Günlük Giriş ──────────────────────────────────────────
GUNLUK_COIN       = 50

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
GEM_COIN_KURU     = 200   # 1 Gem = 200 Coin

# ── Patron ────────────────────────────────────────────────
PATRON_KANAL_ID        = int(os.getenv("PATRON_KANAL_ID", "0"))
PATRON_SONUC_KANAL_ID  = int(os.getenv("PATRON_SONUC_KANAL_ID", "0"))
PATRON_MIN_SAAT   = 1            # Min 1 saat aralık
PATRON_MAX_SAAT   = 3            # Max 3 saat aralık
PATRON_HP         = 750         # Sabit HP (scaling kaldırıldı)
PATRON_HP_SCALING = 0           # Scaling devre dışı
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

# ── Profil Rozet Sistemi ───────────────────────────────────
OZEL_ROZETLER = [
    {"id": "seri_7",      "isim": "7 Gunluk Kahraman",  "emoji": "\U0001f525"},
    {"id": "seri_30",     "isim": "Aylik Efsane",       "emoji": "\U0001f3c6"},
    {"id": "seri_100",    "isim": "Yuzluk Titan",       "emoji": "\U0001f451"},
    {"id": "vanguard",    "isim": "Vanguard",            "emoji": "⚔️"},
    {"id": "harbinger",   "isim": "Harbinger",           "emoji": "\U0001f3af"},
    {"id": "sentinel",    "isim": "Sentinel",            "emoji": "\U0001f6e1️"},
    {"id": "luminary",    "isim": "Luminary",            "emoji": "✨"},
    {"id": "patron_asil", "isim": "Patron Katili",       "emoji": "\U0001f480"},
    {"id": "ozel_admin",  "isim": "Ekip Uyesi",         "emoji": "⭐"},
    {"id": "referans_10", "isim": "Davetci",             "emoji": "\U0001f4e8"},
]

# ── Rozet Mağazası (coin ile satın alınabilen) ─────────────
ROZET_MAGAZA = [
    {"id": "rm_alev",    "isim": "Alev",    "emoji": "\U0001f525", "fiyat": 200},
    {"id": "rm_yildiz",  "isim": "Yildiz",  "emoji": "\U00002b50", "fiyat": 300},
    {"id": "rm_robot",   "isim": "Robot",   "emoji": "\U0001f916", "fiyat": 400},
    {"id": "rm_elmas",   "isim": "Elmas",   "emoji": "\U0001f48e", "fiyat": 500},
    {"id": "rm_gizem",   "isim": "Gizem",   "emoji": "\U0001f52e", "fiyat": 600},
    {"id": "rm_kral",    "isim": "Kral",    "emoji": "\U0001f451", "fiyat": 800},
    {"id": "rm_galaksi", "isim": "Galaksi", "emoji": "\U0001f30c", "fiyat": 1000},
    {"id": "rm_ejder",   "isim": "Ejder",   "emoji": "\U0001f409", "fiyat": 1200},
]

# ── Profil Arka Plan Sistemi ───────────────────────────────
PROFIL_ARKA_PLANLAR = [
    {"id": "varsayilan", "isim": "Varsayilan",  "renk": "2b2d31", "fiyat": 0,    "emoji": "⬛"},
    {"id": "kirmizi",    "isim": "Kirmizi",     "renk": "922b21", "fiyat": 300,  "emoji": "\U0001f7e5"},
    {"id": "mavi",       "isim": "Mavi",        "renk": "1a5276", "fiyat": 300,  "emoji": "\U0001f7e6"},
    {"id": "mor",        "isim": "Mor",         "renk": "6c3483", "fiyat": 300,  "emoji": "\U0001f7ea"},
    {"id": "altin",      "isim": "Altin",       "renk": "9a7d0a", "fiyat": 500,  "emoji": "\U0001f7e8"},
    {"id": "zumrut",     "isim": "Zumrut",      "renk": "1e8449", "fiyat": 500,  "emoji": "\U0001f7e9"},
    {"id": "gunes",      "isim": "Gunes",       "renk": "ca6f1e", "fiyat": 500,  "emoji": "\U0001f7e7"},
    {"id": "galaksi",    "isim": "Galaksi",     "renk": "4a235a", "fiyat": 800,  "emoji": "\U0001f52e"},
    {"id": "ejder",      "isim": "Ejder",       "renk": "641e16", "fiyat": 800,  "emoji": "\U0001f409"},
    {"id": "efsane",     "isim": "Efsane",      "renk": "784212", "fiyat": 1000, "emoji": "⚡"},
]
