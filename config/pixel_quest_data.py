"""config/pixel_quest_data.py — Pixel Quest oyun verileri (v2 — dengeli)."""

# ── Irklar (yeniden dengelendi) ──────────────────────────
IRKLAR = {
    "cuece": {
        "isim": "Cüce",
        "emoji": "🧔",
        "aciklama": "Yüksek savunma ve HP, düşük saldırı ve hız",
        "hp": 180,
        "saldiri": 10,
        "savunma": 22,
        "hiz": 5,
        "avatar_klasor": "avatars/dwarf",
        "skill_klasor": "skills/paladin",
    },
    "peri": {
        "isim": "Peri",
        "emoji": "🧚",
        "aciklama": "Yüksek saldırı ve hız, düşük HP ve savunma",
        "hp": 90,
        "saldiri": 25,
        "savunma": 5,
        "hiz": 20,
        "avatar_klasor": "avatars/fairy",
        "skill_klasor": "skills/undead",
    },
    "ork": {
        "isim": "Ork",
        "emoji": "🐗",
        "aciklama": "Dengeli savaşçı, güçlü saldırı",
        "hp": 130,
        "saldiri": 20,
        "savunma": 12,
        "hiz": 10,
        "avatar_klasor": "avatars/orc",
        "skill_klasor": "skills/swordman",
    },
}

# ── Seviye başı stat artışı ──────────────────────────────
SEVIYE_STAT_BONUS = {
    "hp": 10,
    "saldiri": 1,
    "savunma": 1,
}

# ── Canavarlar (3 tier: low 1-7, chaos 8-14, elit 15-20) ─
CANAVARLAR = {
    "low": [
        {"isim": "Orman Faresi",      "hp": 25,  "saldiri": 4,  "savunma": 2,  "hiz": 12, "xp": 8,   "altin": (3, 8),     "ikon": 1},
        {"isim": "Zehirli Örümcek",   "hp": 35,  "saldiri": 7,  "savunma": 3,  "hiz": 10, "xp": 12,  "altin": (5, 12),    "ikon": 2},
        {"isim": "Vahşi Kurt",        "hp": 50,  "saldiri": 9,  "savunma": 4,  "hiz": 14, "xp": 16,  "altin": (6, 15),    "ikon": 3},
        {"isim": "Goblin Avcısı",     "hp": 45,  "saldiri": 11, "savunma": 5,  "hiz": 9,  "xp": 18,  "altin": (8, 18),    "ikon": 4},
        {"isim": "Dağ Ayısı",         "hp": 80,  "saldiri": 12, "savunma": 10, "hiz": 4,  "xp": 22,  "altin": (10, 22),   "ikon": 5},
        {"isim": "İskelet Savaşçısı", "hp": 55,  "saldiri": 10, "savunma": 7,  "hiz": 7,  "xp": 17,  "altin": (7, 16),    "ikon": 6},
        {"isim": "Yılan Kralı",       "hp": 40,  "saldiri": 14, "savunma": 3,  "hiz": 16, "xp": 20,  "altin": (8, 20),    "ikon": 7},
        {"isim": "Taşkın Golem",      "hp": 100, "saldiri": 7,  "savunma": 16, "hiz": 2,  "xp": 25,  "altin": (12, 25),   "ikon": 8},
        {"isim": "Orman Trenti",      "hp": 70,  "saldiri": 9,  "savunma": 11, "hiz": 3,  "xp": 20,  "altin": (9, 20),    "ikon": 9},
        {"isim": "Kızgın Domuz",      "hp": 60,  "saldiri": 12, "savunma": 6,  "hiz": 8,  "xp": 15,  "altin": (6, 15),    "ikon": 10},
        {"isim": "Mezar Kazıcı",      "hp": 50,  "saldiri": 8,  "savunma": 5,  "hiz": 6,  "xp": 13,  "altin": (5, 13),    "ikon": 11},
        {"isim": "Karanlık Yarasa",   "hp": 30,  "saldiri": 11, "savunma": 2,  "hiz": 18, "xp": 14,  "altin": (5, 12),    "ikon": 12},
        {"isim": "Bataklık Canavarı", "hp": 90,  "saldiri": 10, "savunma": 9,  "hiz": 3,  "xp": 24,  "altin": (10, 24),   "ikon": 13},
        {"isim": "Cüce Şaman",        "hp": 35,  "saldiri": 13, "savunma": 4,  "hiz": 11, "xp": 16,  "altin": (6, 14),    "ikon": 14},
        {"isim": "Mantar Adam",       "hp": 45,  "saldiri": 6,  "savunma": 8,  "hiz": 5,  "xp": 12,  "altin": (5, 12),    "ikon": 15},
    ],
    "chaos": [
        {"isim": "Kaos İblis",         "hp": 160, "saldiri": 24, "savunma": 14, "hiz": 10, "xp": 50,  "altin": (25, 50),   "ikon": 1},
        {"isim": "Şeytan Şövalyesi",   "hp": 220, "saldiri": 28, "savunma": 20, "hiz": 6,  "xp": 70,  "altin": (35, 65),   "ikon": 2},
        {"isim": "Cehennem Kurdu",     "hp": 180, "saldiri": 26, "savunma": 15, "hiz": 13, "xp": 58,  "altin": (28, 55),   "ikon": 3},
        {"isim": "Karanlık Büyücü",    "hp": 140, "saldiri": 32, "savunma": 10, "hiz": 14, "xp": 62,  "altin": (30, 60),   "ikon": 4},
        {"isim": "Ateş Ejderhası",     "hp": 280, "saldiri": 30, "savunma": 22, "hiz": 5,  "xp": 90,  "altin": (45, 85),   "ikon": 5},
        {"isim": "Kemik Ejderi",       "hp": 240, "saldiri": 27, "savunma": 24, "hiz": 4,  "xp": 78,  "altin": (38, 75),   "ikon": 6},
        {"isim": "Ruh Yiyici",         "hp": 170, "saldiri": 30, "savunma": 12, "hiz": 15, "xp": 65,  "altin": (32, 62),   "ikon": 7},
        {"isim": "Kara Elf",           "hp": 150, "saldiri": 28, "savunma": 16, "hiz": 16, "xp": 60,  "altin": (30, 58),   "ikon": 8},
        {"isim": "Gölgeler Lordu",     "hp": 300, "saldiri": 33, "savunma": 26, "hiz": 7,  "xp": 95,  "altin": (48, 90),   "ikon": 9},
        {"isim": "Lanetli Şövalye",    "hp": 200, "saldiri": 26, "savunma": 22, "hiz": 8,  "xp": 72,  "altin": (35, 70),   "ikon": 10},
        {"isim": "Zombi Kral",         "hp": 230, "saldiri": 25, "savunma": 20, "hiz": 5,  "xp": 68,  "altin": (33, 65),   "ikon": 11},
        {"isim": "Demon Avcısı",       "hp": 190, "saldiri": 30, "savunma": 18, "hiz": 12, "xp": 75,  "altin": (36, 72),   "ikon": 12},
    ],
    # Elit mob ikonları chaos klasörünün kullanılmayan yüksek
    # aralığından seçildi (chaos tier 1-12 kullanır) — görsel çakışma yok
    "elit": [
        {"isim": "Cehennem Lordu",     "hp": 350, "saldiri": 40, "savunma": 25, "hiz": 8,  "xp": 130, "altin": (80, 140),  "ikon": 41},
        {"isim": "Karanlık İmparator", "hp": 420, "saldiri": 44, "savunma": 30, "hiz": 6,  "xp": 160, "altin": (95, 160),  "ikon": 42},
        {"isim": "Ölüm Şövalyesi",     "hp": 380, "saldiri": 48, "savunma": 22, "hiz": 12, "xp": 150, "altin": (90, 155),  "ikon": 43},
        {"isim": "Kıyamet Ejderhası",  "hp": 550, "saldiri": 42, "savunma": 38, "hiz": 4,  "xp": 200, "altin": (120, 190), "ikon": 44},
        {"isim": "Ruh Lordu",          "hp": 300, "saldiri": 52, "savunma": 20, "hiz": 16, "xp": 170, "altin": (100, 170), "ikon": 45},
        {"isim": "Kadim Titan",        "hp": 650, "saldiri": 38, "savunma": 42, "hiz": 2,  "xp": 220, "altin": (130, 200), "ikon": 46},
        {"isim": "Şeytan Kralı",       "hp": 480, "saldiri": 50, "savunma": 32, "hiz": 9,  "xp": 200, "altin": (115, 185), "ikon": 47},
        {"isim": "Kaos Tanrısı",       "hp": 600, "saldiri": 55, "savunma": 36, "hiz": 7,  "xp": 250, "altin": (140, 220), "ikon": 48},
    ],
}

# ── Loot Tablosu ──────────────────────────────────────────
LOOT_KATEGORILERI = {
    "goblin":  {"isim": "Goblin Ganimetleri",  "klasor": "loot/goblin",  "sayisi": 48, "tier": 1},
    "general": {"isim": "Genel Ganimeler",     "klasor": "loot/general", "sayisi": 48, "tier": 1},
    "pirate":  {"isim": "Korsan Hazineleri",   "klasor": "loot/pirate",  "sayisi": 48, "tier": 2},
    "undead":  {"isim": "Undead Kalıntıları",  "klasor": "loot/undead",  "sayisi": 48, "tier": 3},
    "mineral": {"isim": "Değerli Madenler",    "klasor": "minerals",     "sayisi": 48, "tier": 3},
}

LOOT_ISIMLERI = {
    "goblin": [
        "Goblin Dişi", "Goblin Tırnak", "Kirli Bez", "Paslı Civata", "Kemik Parçası",
        "Eski Boncuk", "Küçük Çanta", "Goblin Küpesi", "Yırtık Deri", "Taş Bilyesi",
    ],
    "general": [
        "Hayvan Derisi", "Sert Kabuk", "Örümcek Ağı", "Kurt Pençesi", "Ayı Kürkü",
        "Yılan Pulcuğu", "Sivri Diş", "Kemik Kolye", "Eski Para", "Kristal Parçası",
    ],
    "pirate": [
        "Korsan Bıçağı", "Altın Sikke", "Deniz Kabuğu", "Pusula Parçası", "Harita Parçası",
        "Gemi Civisi", "İnci Tanesi", "Korsan Bandanası", "Kanca", "Barut Torbası",
    ],
    "undead": [
        "Kafatası", "Ruh Özü", "Karanlık Kristal", "Lanetli Kemik", "Gölgeli Taş",
        "Ölüm Muskası", "Hayalet Külü", "Karanlık Öz", "Kefen Parçası", "Ruh Taşı",
    ],
    "mineral": [
        "Bakır Cevheri", "Demir Külçesi", "Gümüş Tozu", "Altın Pirinci", "Zümrüt Şardı",
        "Yakut Kırığı", "Safir Parçası", "Elmas Tozu", "Mithril Cevheri", "Adamant Külçesi",
    ],
}

# İsim → ikon (deterministic) — aynı isimli item her yerde aynı görsel
LOOT_IKON = {
    # goblin
    "Goblin Dişi": 1, "Goblin Tırnak": 2, "Kirli Bez": 3, "Paslı Civata": 4, "Kemik Parçası": 5,
    "Eski Boncuk": 6, "Küçük Çanta": 7, "Goblin Küpesi": 8, "Yırtık Deri": 9, "Taş Bilyesi": 10,
    # general
    "Hayvan Derisi": 1, "Sert Kabuk": 2, "Örümcek Ağı": 3, "Kurt Pençesi": 4, "Ayı Kürkü": 5,
    "Yılan Pulcuğu": 6, "Sivri Diş": 7, "Kemik Kolye": 8, "Eski Para": 9, "Kristal Parçası": 10,
    # pirate
    "Korsan Bıçağı": 1, "Altın Sikke": 2, "Deniz Kabuğu": 3, "Pusula Parçası": 4, "Harita Parçası": 5,
    "Gemi Civisi": 6, "İnci Tanesi": 7, "Korsan Bandanası": 8, "Kanca": 9, "Barut Torbası": 10,
    # undead
    "Kafatası": 1, "Ruh Özü": 2, "Karanlık Kristal": 3, "Lanetli Kemik": 4, "Gölgeli Taş": 5,
    "Ölüm Muskası": 6, "Hayalet Külü": 7, "Karanlık Öz": 8, "Kefen Parçası": 9, "Ruh Taşı": 10,
    # mineral
    "Bakır Cevheri": 1, "Demir Külçesi": 2, "Gümüş Tozu": 3, "Altın Pirinci": 4, "Zümrüt Şardı": 5,
    "Yakut Kırığı": 6, "Safir Parçası": 7, "Elmas Tozu": 8, "Mithril Cevheri": 9, "Adamant Külçesi": 10,
}

# ── Ekipman (20 seviyeye yayıldı) ───────────────────────
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

EKIPMANLAR = {
    "silah": [
        {"isim": "Tahta Yay",         "bonus": 2,  "nadirlik": "yaygın",    "ikon": 1,  "seviye": 1},
        {"isim": "Avcı Yayı",         "bonus": 4,  "nadirlik": "yaygın",    "ikon": 5,  "seviye": 3},
        {"isim": "Meşe Yay",          "bonus": 7,  "nadirlik": "yaygın",    "ikon": 10, "seviye": 5},
        {"isim": "Savaş Yayı",        "bonus": 11, "nadirlik": "uncommon",  "ikon": 15, "seviye": 7},
        {"isim": "Çelik Arbalet",     "bonus": 16, "nadirlik": "uncommon",  "ikon": 20, "seviye": 9},
        {"isim": "Ateş Yayı",         "bonus": 22, "nadirlik": "nadir",     "ikon": 25, "seviye": 11},
        {"isim": "Fırtına Arbaleti",  "bonus": 29, "nadirlik": "nadir",     "ikon": 30, "seviye": 13},
        {"isim": "Ejderha Yayı",      "bonus": 37, "nadirlik": "efsanevi",  "ikon": 35, "seviye": 15},
        {"isim": "Kadim Arbalet",     "bonus": 47, "nadirlik": "efsanevi",  "ikon": 40, "seviye": 17},
        {"isim": "Tanrıların Yayı",   "bonus": 60, "nadirlik": "mitik",     "ikon": 45, "seviye": 20},
    ],
    "kalkan": [
        {"isim": "Ahşap Kalkan",      "bonus": 2,  "nadirlik": "yaygın",    "ikon": 1,  "seviye": 1},
        {"isim": "Deri Kalkan",        "bonus": 4,  "nadirlik": "yaygın",    "ikon": 5,  "seviye": 3},
        {"isim": "Demir Kalkan",      "bonus": 7,  "nadirlik": "yaygın",    "ikon": 10, "seviye": 5},
        {"isim": "Çelik Kalkan",      "bonus": 11, "nadirlik": "uncommon",  "ikon": 15, "seviye": 7},
        {"isim": "Muhafız Kalkanı",   "bonus": 16, "nadirlik": "uncommon",  "ikon": 20, "seviye": 9},
        {"isim": "Ateş Kalkanı",      "bonus": 22, "nadirlik": "nadir",     "ikon": 25, "seviye": 11},
        {"isim": "Büyülü Tılsım",    "bonus": 29, "nadirlik": "nadir",     "ikon": 30, "seviye": 13},
        {"isim": "Ejderha Kalkanı",   "bonus": 37, "nadirlik": "efsanevi",  "ikon": 35, "seviye": 15},
        {"isim": "Kadim Tılsım",     "bonus": 47, "nadirlik": "efsanevi",  "ikon": 40, "seviye": 17},
        {"isim": "Tanrıların Kalkanı","bonus": 60, "nadirlik": "mitik",     "ikon": 45, "seviye": 20},
    ],
    "kemer": [
        {"isim": "Kumaş Kemer",       "bonus": 8,   "nadirlik": "yaygın",    "ikon": 1,  "seviye": 1},
        {"isim": "Deri Kemer",         "bonus": 15,  "nadirlik": "yaygın",    "ikon": 5,  "seviye": 3},
        {"isim": "Zincir Kemer",      "bonus": 25,  "nadirlik": "yaygın",    "ikon": 10, "seviye": 5},
        {"isim": "Savaşçı Kemeri",    "bonus": 38,  "nadirlik": "uncommon",  "ikon": 15, "seviye": 7},
        {"isim": "Muhafız Kemeri",    "bonus": 52,  "nadirlik": "uncommon",  "ikon": 20, "seviye": 9},
        {"isim": "Ateş Kemeri",       "bonus": 70,  "nadirlik": "nadir",     "ikon": 25, "seviye": 11},
        {"isim": "Büyülü Kemer",      "bonus": 90,  "nadirlik": "nadir",     "ikon": 30, "seviye": 13},
        {"isim": "Ejderha Kemeri",    "bonus": 115, "nadirlik": "efsanevi",  "ikon": 35, "seviye": 15},
        {"isim": "Kadim Kemer",       "bonus": 150, "nadirlik": "efsanevi",  "ikon": 40, "seviye": 17},
        {"isim": "Tanrıların Kemeri", "bonus": 200, "nadirlik": "mitik",     "ikon": 45, "seviye": 20},
    ],
}

# ── İksirler ──────────────────────────────────────────────
IKSIRLER = [
    {"isim": "Küçük Can İksiri",   "etki": "hp",      "deger": 30,  "ikon": 1,  "nadirlik": "yaygın"},
    {"isim": "Orta Can İksiri",    "etki": "hp",      "deger": 60,  "ikon": 5,  "nadirlik": "uncommon"},
    {"isim": "Büyük Can İksiri",   "etki": "hp",      "deger": 120, "ikon": 10, "nadirlik": "nadir"},
    {"isim": "Saldırı İksiri",     "etki": "saldiri", "deger": 5,   "ikon": 15, "nadirlik": "uncommon"},
    {"isim": "Savunma İksiri",     "etki": "savunma", "deger": 5,   "ikon": 20, "nadirlik": "uncommon"},
    {"isim": "Hız İksiri",         "etki": "hiz",     "deger": 5,   "ikon": 25, "nadirlik": "nadir"},
    {"isim": "Efsane İksir",       "etki": "hp",      "deger": 250, "ikon": 30, "nadirlik": "efsanevi"},
]

# ── Seviye Sistemi (20 seviye, uzun grind) ───────────────
SEVIYE_XP = {
    1: 0,       2: 100,     3: 280,     4: 550,     5: 950,
    6: 1500,    7: 2250,    8: 3200,    9: 4500,    10: 6200,
    11: 8400,   12: 11200,  13: 14800,  14: 19200,  15: 25000,
    16: 31500,  17: 39000,  18: 48000,  19: 58500,  20: 70000,
}

# ── Dükkan (altınla satın alınabilir) ────────────────────
DUKKAN = [
    {"isim": "Küçük Can İksiri", "fiyat": 25,   "etki": "hp",      "deger": 30,  "ikon": 1,  "nadirlik": "yaygın",   "aciklama": "+30 HP"},
    {"isim": "Orta Can İksiri",  "fiyat": 80,   "etki": "hp",      "deger": 60,  "ikon": 5,  "nadirlik": "uncommon", "aciklama": "+60 HP"},
    {"isim": "Büyük Can İksiri", "fiyat": 200,  "etki": "hp",      "deger": 120, "ikon": 10, "nadirlik": "nadir",    "aciklama": "+120 HP"},
    {"isim": "Saldırı İksiri",   "fiyat": 150,  "etki": "saldiri", "deger": 5,   "ikon": 15, "nadirlik": "uncommon", "aciklama": "+5 Saldırı (1 savaş)"},
    {"isim": "Savunma İksiri",   "fiyat": 150,  "etki": "savunma", "deger": 5,   "ikon": 20, "nadirlik": "uncommon", "aciklama": "+5 Savunma (1 savaş)"},
    {"isim": "Hız İksiri",       "fiyat": 320,  "etki": "hiz",     "deger": 5,   "ikon": 25, "nadirlik": "nadir",    "aciklama": "+5 Hız (1 savaş)"},
    {"isim": "Efsane İksir",     "fiyat": 900,  "etki": "hp",      "deger": 250, "ikon": 30, "nadirlik": "efsanevi", "aciklama": "+250 HP"},
]

# ── Malzeme satış fiyatları ──────────────────────────────
MALZEME_FIYAT = {
    "goblin":  5,
    "general": 5,
    "pirate":  12,
    "undead":  20,
    "mineral": 35,
}

# ── Nadirlik renkleri ─────────────────────────────────────
NADIRLIK_RENK = {
    "yaygın":   0x9E9E9E,
    "uncommon": 0x4CAF50,
    "nadir":    0x2196F3,
    "efsanevi": 0x9C27B0,
    "mitik":    0xF44336,
}

NADIRLIK_SIRA = {
    "mitik":    5,
    "efsanevi": 4,
    "nadir":    3,
    "uncommon": 2,
    "yaygın":   1,
}

NADIRLIK_EMOJI = {
    "yaygın":   "⬜",
    "uncommon": "🟢",
    "nadir":    "🔵",
    "efsanevi": "🟣",
    "mitik":    "🔴",
}

# ── Drop oranları ────────────────────────────────────────
MALZEME_DROP_SANS = 0.30   # %30
EKIPMAN_DROP_SANS = 0.04   # %4
IKSIR_DROP_SANS = 0.08     # %8

# ── Mob ikon klasörleri ──────────────────────────────────
MOB_IKON_KLASOR = {
    "low": "mobs/low",
    "chaos": "mobs/chaos",
    "elit": "mobs/chaos",  # elit iconları 41-48 aralığında, chaos ise 1-12
}

# ── Irk → skill klasörü (savaş log görselleri için) ──────
# Her ırkın kendine özel skill ikonları vardır; embed thumbnail olarak
# rastgele seçilerek çeşitlilik sağlanır (avatar yerine)
SKILL_KLASORLERI = {
    "cuece": "skills/paladin",
    "peri":  "skills/undead",
    "ork":   "skills/swordman",
}

# Nadirlik → iksir ikonu (envanter embed'lerinde tematik kullanım)
IKSIR_IKON_NADIRLIK = {
    "yaygın":   1,
    "uncommon": 10,
    "nadir":    20,
    "efsanevi": 30,
    "mitik":    40,
}

# ── Savaş cooldown ──────────────────────────────────────
SAVAS_COOLDOWN = 60  # saniye
