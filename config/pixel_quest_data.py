"""config/pixel_quest_data.py — Pixel Quest oyun verileri."""

# ── Irklar ────────────────────────────────────────────────
IRKLAR = {
    "cuece": {
        "isim": "Cuce",
        "emoji": "🧔",
        "aciklama": "Yuksek savunma, dusuk hiz",
        "hp": 150,
        "saldiri": 12,
        "savunma": 18,
        "hiz": 8,
        "avatar_klasor": "avatars/dwarf",
        "skill_klasor": "skills/paladin",
    },
    "peri": {
        "isim": "Peri",
        "emoji": "🧚",
        "aciklama": "Yuksek buyu, dusuk HP",
        "hp": 90,
        "saldiri": 20,
        "savunma": 8,
        "hiz": 15,
        "avatar_klasor": "avatars/fairy",
        "skill_klasor": "skills/undead",
    },
    "ork": {
        "isim": "Ork",
        "emoji": "🐗",
        "aciklama": "Yuksek saldiri, dusuk savunma",
        "hp": 120,
        "saldiri": 22,
        "savunma": 10,
        "hiz": 12,
        "avatar_klasor": "avatars/orc",
        "skill_klasor": "skills/swordman",
    },
}

# ── Canavarlar ────────────────────────────────────────────
CANAVARLAR = {
    # Low level (seviye 1-5)
    "low": [
        {"isim": "Orman Faresi",      "hp": 30,  "saldiri": 5,  "savunma": 2,  "xp": 10, "altin": (5, 15),    "ikon": 1},
        {"isim": "Zehirli Orumcek",   "hp": 40,  "saldiri": 8,  "savunma": 3,  "xp": 15, "altin": (8, 20),    "ikon": 2},
        {"isim": "Vahsi Kurt",        "hp": 55,  "saldiri": 10, "savunma": 5,  "xp": 20, "altin": (10, 25),   "ikon": 3},
        {"isim": "Goblin Avcisi",     "hp": 50,  "saldiri": 12, "savunma": 4,  "xp": 25, "altin": (12, 30),   "ikon": 4},
        {"isim": "Dag Ayisi",         "hp": 80,  "saldiri": 14, "savunma": 8,  "xp": 30, "altin": (15, 35),   "ikon": 5},
        {"isim": "Iskelet Savascisi", "hp": 60,  "saldiri": 11, "savunma": 6,  "xp": 22, "altin": (10, 28),   "ikon": 6},
        {"isim": "Yilan Krali",       "hp": 45,  "saldiri": 15, "savunma": 3,  "xp": 28, "altin": (12, 32),   "ikon": 7},
        {"isim": "Taskin Golem",      "hp": 100, "saldiri": 8,  "savunma": 15, "xp": 35, "altin": (18, 40),   "ikon": 8},
        {"isim": "Orman Trenti",      "hp": 70,  "saldiri": 10, "savunma": 10, "xp": 25, "altin": (14, 30),   "ikon": 9},
        {"isim": "Kizgin Domuz",      "hp": 65,  "saldiri": 13, "savunma": 7,  "xp": 20, "altin": (10, 25),   "ikon": 10},
        {"isim": "Mezar Kazici",      "hp": 55,  "saldiri": 9,  "savunma": 5,  "xp": 18, "altin": (8, 22),    "ikon": 11},
        {"isim": "Karanhk Yarasa",    "hp": 35,  "saldiri": 12, "savunma": 2,  "xp": 15, "altin": (7, 18),    "ikon": 12},
        {"isim": "Bataklik Canavari", "hp": 90,  "saldiri": 11, "savunma": 9,  "xp": 32, "altin": (15, 38),   "ikon": 13},
        {"isim": "Cuce Saman",        "hp": 40,  "saldiri": 7,  "savunma": 4,  "xp": 12, "altin": (6, 16),    "ikon": 14},
        {"isim": "Mantar Adam",       "hp": 50,  "saldiri": 6,  "savunma": 8,  "xp": 16, "altin": (8, 20),    "ikon": 15},
    ],
    # Chaos (seviye 6-10)
    "chaos": [
        {"isim": "Kaos Iblis",        "hp": 150, "saldiri": 25, "savunma": 12, "xp": 60,  "altin": (30, 60),  "ikon": 1},
        {"isim": "Seytan Sovalyesi",  "hp": 200, "saldiri": 30, "savunma": 18, "xp": 80,  "altin": (40, 80),  "ikon": 2},
        {"isim": "Cehennem Kurdu",    "hp": 170, "saldiri": 28, "savunma": 14, "xp": 70,  "altin": (35, 70),  "ikon": 3},
        {"isim": "Karanlik Bueyuecue","hp": 130, "saldiri": 35, "savunma": 10, "xp": 75,  "altin": (38, 75),  "ikon": 4},
        {"isim": "Ates Ejderhasi",    "hp": 250, "saldiri": 32, "savunma": 20, "xp": 100, "altin": (50, 100), "ikon": 5},
        {"isim": "Kemik Ejderi",      "hp": 220, "saldiri": 28, "savunma": 22, "xp": 90,  "altin": (45, 90),  "ikon": 6},
        {"isim": "Ruh Yiyici",        "hp": 160, "saldiri": 33, "savunma": 11, "xp": 78,  "altin": (38, 78),  "ikon": 7},
        {"isim": "Kara Elf",          "hp": 140, "saldiri": 30, "savunma": 15, "xp": 72,  "altin": (35, 72),  "ikon": 8},
        {"isim": "Golgeler Lordu",    "hp": 280, "saldiri": 35, "savunma": 25, "xp": 120, "altin": (60, 120), "ikon": 9},
        {"isim": "Lanetli Sovalye",   "hp": 190, "saldiri": 27, "savunma": 20, "xp": 85,  "altin": (42, 85),  "ikon": 10},
        {"isim": "Zombi Kral",        "hp": 210, "saldiri": 26, "savunma": 18, "xp": 82,  "altin": (40, 82),  "ikon": 11},
        {"isim": "Demon Avcisi",      "hp": 180, "saldiri": 31, "savunma": 16, "xp": 88,  "altin": (44, 88),  "ikon": 12},
    ],
}

# ── Loot Tablosu ──────────────────────────────────────────
LOOT_KATEGORILERI = {
    "goblin":  {"isim": "Goblin Ganimetleri",  "klasor": "loot/goblin",  "sayisi": 48, "tier": 1},
    "general": {"isim": "Genel Ganimeler",     "klasor": "loot/general", "sayisi": 48, "tier": 1},
    "pirate":  {"isim": "Korsan Hazineleri",   "klasor": "loot/pirate",  "sayisi": 48, "tier": 2},
    "undead":  {"isim": "Undead Kalintilari",  "klasor": "loot/undead",  "sayisi": 48, "tier": 3},
}

# Loot isimleri (her kategoriden örnekler)
LOOT_ISIMLERI = {
    "goblin": [
        "Goblin Disi", "Goblin Tirnak", "Kirli Bez", "Pasli Civata", "Kemik Parcasi",
        "Eski Boncuk", "Kucuk Canta", "Goblin Kupesi", "Yirtik Deri", "Tas Bilyesi",
    ],
    "general": [
        "Hayvan Derisi", "Sert Kabuk", "Orumcek Agi", "Kurt Pençesi", "Ayi Kurkue",
        "Yilan Pulcugu", "Sivri Dis", "Kemik Kolye", "Eski Para", "Kristal Parcasi",
    ],
    "pirate": [
        "Korsan Bicagi", "Altin Sikke", "Deniz Kabuğu", "Pusula Parcasi", "Harita Parcasi",
        "Gemi Civisi", "Inci Tanesi", "Korsan Bandanasi", "Kanca", "Barut Torbasi",
    ],
    "undead": [
        "Kafatasi", "Ruh Ozu", "Karanlik Kristal", "Lanetli Kemik", "Golgeli Tas",
        "Olum Muskasi", "Hayalet Kuelue", "Karanhk Oez", "Kefen Parcasi", "Ruh Tasi",
    ],
}

# ── Ekipman ───────────────────────────────────────────────
EKIPMAN_TURLERI = {
    "silah": {
        "isim": "Silah",
        "stat": "saldiri",
        "klasor": "equipment/bow",
        "sayisi": 78,
    },
    "kalkan": {
        "isim": "Kalkan",
        "stat": "savunma",
        "klasor": "equipment/shield",
        "sayisi": 48,
    },
    "kemer": {
        "isim": "Kemer",
        "stat": "hp",
        "klasor": "equipment/belt",
        "sayisi": 48,
    },
}

# Ekipman listesi (nadirlik sırasıyla)
EKIPMANLAR = {
    "silah": [
        {"isim": "Tahta Yay",         "bonus": 3,  "nadirlik": "yaygın",    "ikon": 1,  "seviye": 1},
        {"isim": "Avcı Yayı",         "bonus": 5,  "nadirlik": "yaygın",    "ikon": 5,  "seviye": 2},
        {"isim": "Meşe Yay",          "bonus": 8,  "nadirlik": "yaygın",    "ikon": 10, "seviye": 3},
        {"isim": "Savaş Yayı",        "bonus": 12, "nadirlik": "uncommon",  "ikon": 15, "seviye": 4},
        {"isim": "Çelik Arbalet",     "bonus": 16, "nadirlik": "uncommon",  "ikon": 20, "seviye": 5},
        {"isim": "Ateş Yayı",         "bonus": 22, "nadirlik": "nadir",     "ikon": 25, "seviye": 6},
        {"isim": "Fırtına Arbaleti",  "bonus": 28, "nadirlik": "nadir",     "ikon": 30, "seviye": 7},
        {"isim": "Ejderha Yayı",      "bonus": 35, "nadirlik": "efsanevi",  "ikon": 35, "seviye": 8},
        {"isim": "Kadim Arbalet",     "bonus": 45, "nadirlik": "efsanevi",  "ikon": 40, "seviye": 9},
        {"isim": "Tanrıların Yayı",   "bonus": 60, "nadirlik": "mitik",     "ikon": 45, "seviye": 10},
    ],
    "kalkan": [
        {"isim": "Ahşap Kalkan",      "bonus": 3,  "nadirlik": "yaygın",    "ikon": 1,  "seviye": 1},
        {"isim": "Deri Kalkan",        "bonus": 5,  "nadirlik": "yaygın",    "ikon": 5,  "seviye": 2},
        {"isim": "Demir Kalkan",      "bonus": 8,  "nadirlik": "yaygın",    "ikon": 10, "seviye": 3},
        {"isim": "Çelik Kalkan",      "bonus": 12, "nadirlik": "uncommon",  "ikon": 15, "seviye": 4},
        {"isim": "Muhafız Kalkanı",   "bonus": 16, "nadirlik": "uncommon",  "ikon": 20, "seviye": 5},
        {"isim": "Ateş Kalkanı",      "bonus": 22, "nadirlik": "nadir",     "ikon": 25, "seviye": 6},
        {"isim": "Büyülü Tılsım",    "bonus": 28, "nadirlik": "nadir",     "ikon": 30, "seviye": 7},
        {"isim": "Ejderha Kalkanı",   "bonus": 35, "nadirlik": "efsanevi",  "ikon": 35, "seviye": 8},
        {"isim": "Kadim Tılsım",     "bonus": 45, "nadirlik": "efsanevi",  "ikon": 40, "seviye": 9},
        {"isim": "Tanrıların Kalkanı","bonus": 60, "nadirlik": "mitik",     "ikon": 45, "seviye": 10},
    ],
    "kemer": [
        {"isim": "Kumaş Kemer",       "bonus": 10, "nadirlik": "yaygın",    "ikon": 1,  "seviye": 1},
        {"isim": "Deri Kemer",         "bonus": 20, "nadirlik": "yaygın",    "ikon": 5,  "seviye": 2},
        {"isim": "Zincir Kemer",      "bonus": 30, "nadirlik": "yaygın",    "ikon": 10, "seviye": 3},
        {"isim": "Savaşçı Kemeri",    "bonus": 45, "nadirlik": "uncommon",  "ikon": 15, "seviye": 4},
        {"isim": "Muhafız Kemeri",    "bonus": 60, "nadirlik": "uncommon",  "ikon": 20, "seviye": 5},
        {"isim": "Ateş Kemeri",       "bonus": 80, "nadirlik": "nadir",     "ikon": 25, "seviye": 6},
        {"isim": "Büyülü Kemer",      "bonus": 100,"nadirlik": "nadir",     "ikon": 30, "seviye": 7},
        {"isim": "Ejderha Kemeri",    "bonus": 130,"nadirlik": "efsanevi",  "ikon": 35, "seviye": 8},
        {"isim": "Kadim Kemer",       "bonus": 170,"nadirlik": "efsanevi",  "ikon": 40, "seviye": 9},
        {"isim": "Tanrıların Kemeri", "bonus": 220,"nadirlik": "mitik",     "ikon": 45, "seviye": 10},
    ],
}

# ── İksirler ──────────────────────────────────────────────
IKSIRLER = [
    {"isim": "Küçük Can İksiri",   "etki": "hp",      "deger": 30,  "ikon": 1,  "nadirlik": "yaygın"},
    {"isim": "Orta Can İksiri",    "etki": "hp",      "deger": 60,  "ikon": 5,  "nadirlik": "uncommon"},
    {"isim": "Büyük Can İksiri",   "etki": "hp",      "deger": 100, "ikon": 10, "nadirlik": "nadir"},
    {"isim": "Saldırı İksiri",     "etki": "saldiri", "deger": 10,  "ikon": 15, "nadirlik": "uncommon"},
    {"isim": "Savunma İksiri",     "etki": "savunma", "deger": 10,  "ikon": 20, "nadirlik": "uncommon"},
    {"isim": "Hız İksiri",         "etki": "hiz",     "deger": 8,   "ikon": 25, "nadirlik": "nadir"},
    {"isim": "Efsane İksir",       "etki": "hp",      "deger": 200, "ikon": 30, "nadirlik": "efsanevi"},
]

# ── Seviye Sistemi ────────────────────────────────────────
SEVIYE_XP = {
    1: 0,
    2: 50,
    3: 120,
    4: 220,
    5: 360,
    6: 550,
    7: 800,
    8: 1150,
    9: 1600,
    10: 2200,
}

# ── Nadirlik renkleri ─────────────────────────────────────
NADIRLIK_RENK = {
    "yaygın":   0x9E9E9E,
    "uncommon": 0x4CAF50,
    "nadir":    0x2196F3,
    "efsanevi": 0x9C27B0,
    "mitik":    0xF44336,
}

NADIRLIK_EMOJI = {
    "yaygın":   "⬜",
    "uncommon": "🟢",
    "nadir":    "🔵",
    "efsanevi": "🟣",
    "mitik":    "🔴",
}

# ── Savasma cooldown ──────────────────────────────────────
SAVAS_COOLDOWN = 30  # saniye
