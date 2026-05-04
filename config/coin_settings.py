"""config/coin_settings.py — M2Board Coin sistemi ayarlari."""
import os

# ── Hazine ────────────────────────────────────────────────
HAZINE_KANAL_ID   = int(os.getenv("HAZINE_KANAL_ID", "0"))
HAZINE_MIN_SAAT   = 1
HAZINE_MAX_SAAT   = 2
HAZINE_MIN_COIN   = 1
HAZINE_MAX_COIN   = 200

# ── Gunluk Giris ──────────────────────────────────────────
GUNLUK_COIN       = 50

# ── Market ────────────────────────────────────────────────
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
PATRON_MIN_SAAT        = 1
PATRON_MAX_SAAT        = 3
PATRON_HP              = 750
PATRON_HP_SCALING      = 0
PATRON_SURE_DK         = 60
PATRON_MAX_SALDIRI     = 3
PATRON_HASAR_MIN       = 20
PATRON_HASAR_MAX       = 80
PATRON_MAX_INDIRIM_SN  = 21600
PATRON_INDIRIM_ESIK    = 5

# ── Bildirim Kanali ───────────────────────────────────────
BILDIRIM_KANAL_ID = int(os.getenv("BILDIRIM_KANAL_ID", "0"))

# ── Gorev Rolleri ─────────────────────────────────────────
ROL_VANGUARD_ID   = int(os.getenv("ROL_VANGUARD_ID",  "0"))
ROL_HARBINGER_ID  = int(os.getenv("ROL_HARBINGER_ID", "0"))
ROL_SENTINEL_ID   = int(os.getenv("ROL_SENTINEL_ID",  "0"))
ROL_LUMINARY_ID   = int(os.getenv("ROL_LUMINARY_ID",  "0"))

# ── Profil Rozet Sistemi ───────────────────────────────────
OZEL_ROZETLER = [
    {"id": "seri_7",      "isim": "7 Günlük Kahraman",  "emoji": "\U0001f525"},
    {"id": "seri_30",     "isim": "Aylık Efsane",        "emoji": "\U0001f3c6"},
    {"id": "seri_100",    "isim": "Yüzlük Titan",        "emoji": "\U0001f451"},
    {"id": "vanguard",    "isim": "Vanguard",             "emoji": "⚔️"},
    {"id": "harbinger",   "isim": "Harbinger",            "emoji": "\U0001f3af"},
    {"id": "sentinel",    "isim": "Sentinel",             "emoji": "\U0001f6e1️"},
    {"id": "luminary",    "isim": "Luminary",             "emoji": "✨"},
    {"id": "patron_asil", "isim": "Patron Katili",        "emoji": "\U0001f480"},
    {"id": "ozel_admin",  "isim": "Ekip Üyesi",          "emoji": "⭐"},
    {"id": "referans_10", "isim": "Davetçi",              "emoji": "\U0001f4e8"},
]

# ── Rozet Magazasi ─────────────────────────────────────────
ROZET_MAGAZA = [
    {"id": "rm_alev",    "isim": "Alev",    "emoji": "\U0001f525", "fiyat": 200},
    {"id": "rm_yildiz",  "isim": "Yıldız",  "emoji": "\U00002b50", "fiyat": 300},
    {"id": "rm_robot",   "isim": "Robot",   "emoji": "\U0001f916", "fiyat": 400},
    {"id": "rm_elmas",   "isim": "Elmas",   "emoji": "\U0001f48e", "fiyat": 500},
    {"id": "rm_gizem",   "isim": "Gizem",   "emoji": "\U0001f52e", "fiyat": 600},
    {"id": "rm_kral",    "isim": "Kral",    "emoji": "\U0001f451", "fiyat": 800},
    {"id": "rm_galaksi", "isim": "Galaksi", "emoji": "\U0001f30c", "fiyat": 1000},
    {"id": "rm_ejder",   "isim": "Ejder",   "emoji": "\U0001f409", "fiyat": 1200},
]

# ── Profil Arka Plan Sistemi ───────────────────────────────
# para_birimi: "gem"  → Gem harcama
# fiyat      : ilgili para biriminden tutar (0 = ucretsiz)
#
# Sayfalama: Select menu basina max 25 item (Discord limiti).
# STATIK ilk 25 → Sayfa 1, geri kalan → Sayfa 2. Ayni sekilde HAREKETLI.
#
# HAREKETLI liste ID'leri "_gif" soneki alir; boylece STATIK ile cakismaz.
# URL eslestirmesi cogs/profil.py'de otomatik uretilir:
#   {id}.jpg → statik,  {id[:-4]}.gif → hareketli

_AP_STATIK = [
    # id                   isim                          renk      fiyat  emoji
    ("varsayilan",         "Varsayılan",                 "2b2d31",  0,    "⬛"),
    ("gojo_statik",        "Gojo",                       "6c3483",  1,    "\U0001f7e3"),
    ("gojo_hollow",        "Gojo - Sonsuz Boşluk",       "6c3483",  1,    "\U0001f300"),
    ("mahoraga",           "Mahoraga",                   "2c3e50",  1,    "☸️"),
    ("angel_devil",        "Şeytan Melek",               "2c2c3e",  1,    "\U0001f608"),
    ("makima",             "Makima",                     "c0392b",  1,    "\U0001f534"),
    ("goku",               "Goku - Dragon Ball",         "e67e22",  1,    "\U0001f305"),
    ("trunks",             "Trunks - Dragon Ball",       "7b5ea7",  1,    "⚡"),
    ("trunks_rage",        "Trunks SSJ Rage",            "4169e1",  1,    "\U0001f4ab"),
    ("acheron",            "Acheron",                    "8b1a1a",  1,    "⚔️"),
    ("phainon",            "Phainon",                    "1a1a6e",  1,    "\U0001f30c"),
    ("herta",              "The Herta",                  "7b68ee",  1,    "\U0001f3ad"),
    ("chisa",              "Chisa",                      "d4a0c8",  1,    "\U0001f338"),
    ("galbrena",           "Galbrena",                   "8b3a3a",  1,    "\U0001f525"),
    ("zhixing",            "Zhixing",                    "2c3e50",  1,    "\U0001f30c"),
    ("itachi",             "Itachi",                     "8b0000",  1,    "\U0001f441️"),
    ("2b",                 "2B - NieR Automata",         "4a6fa5",  1,    "\U0001f916"),
    ("elaina",             "Elaina",                     "5b8dd9",  1,    "\U0001f9d9‍♀️"),
    ("nacht",              "Nacht Faust",                "1a1a2e",  1,    "\U0001f311"),
    ("columbina",          "Columbina",                  "4a3060",  1,    "\U0001f47c"),
    ("lucy",               "Lucy - Cyberpunk",           "ff6b9d",  1,    "\U0001f338"),
    ("miku",               "Hatsune Miku",               "00b4d8",  1,    "\U0001f3b5"),
    ("miyabi",             "Miyabi",                     "c0a0d0",  1,    "❄️"),
    ("hoshino",            "Hoshino",                    "4a90d9",  1,    "⭐"),
    ("leafeon",            "Leafeon & Espeon",           "2d8659",  1,    "\U0001f33f"),
    # ─── Sayfa 2 baslangici ───────────────────────────────
    ("saber",              "Saber - Fate",               "4169e1",  1,    "⚔️"),
    ("musashi",            "Musashi",                    "8b6914",  1,    "⚔️"),
    ("vagabond",           "Vagabond",                   "8b6914",  1,    "\U0001f30a"),
    ("zhuang",             "Zhuang Fangyi",              "2d8659",  1,    "\U0001f3d4️"),
    ("azure_blade",        "Azure Kılıç",                "1a6b8a",  1,    "\U0001f30a"),
    ("chromatic",          "Kromatik",                   "7b3fa0",  1,    "\U0001f49c"),
    ("crimson_kitsune",    "Kızıl Tilki",                "8b2020",  1,    "\U0001f98a"),
    ("fiery_eyes",         "Ateş Gözler",                "c0392b",  1,    "\U0001f525"),
    ("gugu_gaga",          "Gugu Gaga",                  "5dade2",  1,    "\U0001f4ab"),
    ("kitsune_ronin",      "Kitsune Ronin",              "6b4423",  1,    "⚔️"),
    ("oni_girl",           "Oni Kız",                    "8b0000",  1,    "\U0001f479"),
    ("oni_mask",           "Oni Maskesi",                "2c0000",  1,    "\U0001f47a"),
    ("sakura_blade",       "Sakura Kılıç",               "c47295",  1,    "\U0001f338"),
    ("scarlet_devil",      "Kızıl Şeytan",               "8b0000",  1,    "\U0001f608"),
]

# Hareketli liste: her ID'nin sonu "_gif" — STATIK ile cakisma olmaz.
# gojo_hareketli tek istisna (zaten benzersiz).
_AP_HAREKETLI = [
    # id                    isim                          renk      fiyat  emoji
    ("gojo_hareketli",      "Gojo",                       "6c3483",  4,    "✨"),
    ("gojo_hollow_gif",     "Gojo - Sonsuz Boşluk",       "6c3483",  4,    "\U0001f300"),
    ("mahoraga_gif",        "Mahoraga",                   "2c3e50",  4,    "☸️"),
    ("angel_devil_gif",     "Şeytan Melek",               "2c2c3e",  4,    "\U0001f608"),
    ("makima_gif",          "Makima",                     "c0392b",  4,    "\U0001f534"),
    ("goku_gif",            "Goku - Dragon Ball",         "e67e22",  4,    "\U0001f305"),
    ("trunks_gif",          "Trunks - Dragon Ball",       "7b5ea7",  4,    "⚡"),
    ("trunks_rage_gif",     "Trunks SSJ Rage",            "4169e1",  4,    "\U0001f4ab"),
    ("acheron_gif",         "Acheron",                    "8b1a1a",  4,    "⚔️"),
    ("phainon_gif",         "Phainon",                    "1a1a6e",  4,    "\U0001f30c"),
    ("herta_gif",           "The Herta",                  "7b68ee",  4,    "\U0001f3ad"),
    ("chisa_gif",           "Chisa",                      "d4a0c8",  4,    "\U0001f338"),
    ("galbrena_gif",        "Galbrena",                   "8b3a3a",  4,    "\U0001f525"),
    ("zhixing_gif",         "Zhixing",                    "2c3e50",  4,    "\U0001f30c"),
    ("itachi_gif",          "Itachi",                     "8b0000",  4,    "\U0001f441️"),
    ("2b_gif",              "2B - NieR Automata",         "4a6fa5",  4,    "\U0001f916"),
    ("elaina_gif",          "Elaina",                     "5b8dd9",  4,    "\U0001f9d9‍♀️"),
    ("nacht_gif",           "Nacht Faust",                "1a1a2e",  4,    "\U0001f311"),
    ("columbina_gif",       "Columbina",                  "4a3060",  4,    "\U0001f47c"),
    ("lucy_gif",            "Lucy - Cyberpunk",           "ff6b9d",  4,    "\U0001f338"),
    ("miku_gif",            "Hatsune Miku",               "00b4d8",  4,    "\U0001f3b5"),
    ("miyabi_gif",          "Miyabi",                     "c0a0d0",  4,    "❄️"),
    ("hoshino_gif",         "Hoshino",                    "4a90d9",  4,    "⭐"),
    ("leafeon_gif",         "Leafeon & Espeon",           "2d8659",  4,    "\U0001f33f"),
    ("saber_gif",           "Saber - Fate",               "4169e1",  4,    "⚔️"),
    # ─── Sayfa 2 baslangici ───────────────────────────────
    ("musashi_gif",         "Musashi",                    "8b6914",  4,    "⚔️"),
    ("vagabond_gif",        "Vagabond",                   "8b6914",  4,    "\U0001f30a"),
    ("zhuang_gif",          "Zhuang Fangyi",              "2d8659",  4,    "\U0001f3d4️"),
    ("azure_blade_gif",     "Azure Kılıç",                "1a6b8a",  4,    "\U0001f30a"),
    ("chromatic_gif",       "Kromatik",                   "7b3fa0",  4,    "\U0001f49c"),
    ("crimson_kitsune_gif", "Kızıl Tilki",                "8b2020",  4,    "\U0001f98a"),
    ("fiery_eyes_gif",      "Ateş Gözler",                "c0392b",  4,    "\U0001f525"),
    ("gugu_gaga_gif",       "Gugu Gaga",                  "5dade2",  4,    "\U0001f4ab"),
    ("kitsune_ronin_gif",   "Kitsune Ronin",              "6b4423",  4,    "⚔️"),
    ("oni_girl_gif",        "Oni Kız",                    "8b0000",  4,    "\U0001f479"),
    ("oni_mask_gif",        "Oni Maskesi",                "2c0000",  4,    "\U0001f47a"),
    ("sakura_blade_gif",    "Sakura Kılıç",               "c47295",  4,    "\U0001f338"),
    ("scarlet_devil_gif",   "Kızıl Şeytan",               "8b0000",  4,    "\U0001f608"),
]


def _ap_dict(rows: list, para_birimi: str) -> list[dict]:
    return [
        {
            "id":          ap_id,
            "isim":        isim,
            "renk":        renk,
            "fiyat":       fiyat,
            "para_birimi": para_birimi,
            "emoji":       emoji,
        }
        for ap_id, isim, renk, fiyat, emoji in rows
    ]


PROFIL_ARKA_PLANLAR_STATIK    = _ap_dict(_AP_STATIK,    "gem")
PROFIL_ARKA_PLANLAR_HAREKETLI = _ap_dict(_AP_HAREKETLI, "gem")
PROFIL_ARKA_PLANLAR           = PROFIL_ARKA_PLANLAR_STATIK + PROFIL_ARKA_PLANLAR_HAREKETLI
