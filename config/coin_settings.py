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
PATRON_MIN_SAAT   = 1
PATRON_MAX_SAAT   = 3
PATRON_HP         = 750
PATRON_HP_SCALING = 0
PATRON_SURE_DK    = 60
PATRON_MAX_SALDIRI = 3
PATRON_HASAR_MIN  = 20
PATRON_HASAR_MAX  = 80
PATRON_MAX_INDIRIM_SN = 21600
PATRON_INDIRIM_ESIK   = 5

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

# ── Rozet Mağazası ─────────────────────────────────────────
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
# para_birimi: "coin" → M2B Coin harcama, "gem" → Gem harcama
# fiyat: ilgili para biriminden tutar

PROFIL_ARKA_PLANLAR_STATIK = [
    {"id": "varsayilan",  "isim": "Varsayilan", "renk": "2b2d31", "fiyat": 0, "para_birimi": "gem", "emoji": "⬛"},
    {"id": "gojo_statik", "isim": "Gojo",       "renk": "6c3483", "fiyat": 1, "para_birimi": "gem", "emoji": "\U0001f7e3"},
]

PROFIL_ARKA_PLANLAR_HAREKETLI = [
    {"id": "gojo_hareketli", "isim": "Gojo", "renk": "6c3483", "fiyat": 4, "para_birimi": "gem", "emoji": "✨"},
]

# Geriye dönük uyumluluk — renk adlı eski ID'ler URL map'te tutulur,
# burada sadece aktif arka planların renk/isim araması için kullanılır.
PROFIL_ARKA_PLANLAR = PROFIL_ARKA_PLANLAR_STATIK + PROFIL_ARKA_PLANLAR_HAREKETLI
