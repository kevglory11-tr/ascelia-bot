"""
restore_db.py — Ascelia DB Restore Script
Kullanim: DATABASE_URL=... python restore_db.py
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

RESTORE_DIR = Path(r"C:\Users\ALP\Downloads\ascelia_restore")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS coins (
    discord_id          BIGINT PRIMARY KEY,
    username            TEXT NOT NULL,
    bakiye              BIGINT DEFAULT 0,
    son_giris           DATE DEFAULT NULL,
    toplam_kazanilan    BIGINT DEFAULT 0,
    level               INT DEFAULT 1,
    exp                 BIGINT DEFAULT 0,
    rozet_listesi       JSONB DEFAULT '[]',
    aktif_rozet         TEXT DEFAULT NULL,
    profil_renk         TEXT DEFAULT '2b2d31',
    profil_bio          TEXT DEFAULT NULL,
    profil_arka_plan    TEXT DEFAULT 'varsayilan',
    boost_seviye        INT DEFAULT 0,
    boost_baslangic     TIMESTAMPTZ DEFAULT NULL,
    son_mesaj_exp       TIMESTAMPTZ DEFAULT NULL,
    giris_serisi        INT DEFAULT 0,
    luminary_bonus      INT DEFAULT 0,
    giris_serisi_max    INT DEFAULT 0,
    gorev_hatirlatici   BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS hazine_log (
    id              SERIAL PRIMARY KEY,
    kazanan_id      BIGINT NOT NULL,
    miktar          INT NOT NULL,
    kazanildi_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_satin_alma (
    id              SERIAL PRIMARY KEY,
    discord_id      BIGINT NOT NULL,
    urun_id         TEXT NOT NULL,
    fiyat           INT NOT NULL,
    satin_alindi_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_costumes (
    id              SERIAL PRIMARY KEY,
    discord_id      BIGINT NOT NULL,
    costume_id      TEXT NOT NULL,
    costume_name    TEXT NOT NULL,
    rarity          TEXT NOT NULL,
    kazanildi_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS boost_log (
    id              SERIAL PRIMARY KEY,
    discord_id      BIGINT NOT NULL,
    event_type      TEXT NOT NULL,
    miktar          INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gorev_log (
    discord_id  BIGINT NOT NULL,
    gorev_id    TEXT   NOT NULL,
    tarih       TEXT   NOT NULL,
    PRIMARY KEY (discord_id, gorev_id, tarih)
);

CREATE TABLE IF NOT EXISTS mac_tahmin (
    mac_id      TEXT    NOT NULL,
    discord_id  BIGINT  NOT NULL,
    skor        TEXT    NOT NULL,
    isim        TEXT    NOT NULL,
    zaman       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (mac_id, discord_id)
);

CREATE TABLE IF NOT EXISTS coin_log (
    id          BIGSERIAL PRIMARY KEY,
    discord_id  BIGINT NOT NULL,
    miktar      BIGINT NOT NULL,
    tip         TEXT NOT NULL,
    aciklama    TEXT,
    zaman       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_gunluk (
    discord_id  BIGINT NOT NULL,
    tarih       TEXT   NOT NULL,
    PRIMARY KEY (discord_id, tarih)
);

CREATE TABLE IF NOT EXISTS mac_bilgi (
    mac_id      TEXT PRIMARY KEY,
    ev          TEXT NOT NULL,
    ev_logo     TEXT,
    dep         TEXT NOT NULL,
    dep_logo    TEXT,
    mac_zamani  TEXT NOT NULL,
    kanal_id    BIGINT NOT NULL,
    mesaj_id    BIGINT,
    kapali      BOOLEAN DEFAULT FALSE,
    gercek_skor TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS gem_bakiye (
    discord_id  BIGINT PRIMARY KEY,
    miktar      INT    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gem_log (
    id          BIGSERIAL    PRIMARY KEY,
    discord_id  BIGINT       NOT NULL,
    miktar      INT          NOT NULL,
    tip         TEXT         NOT NULL,
    aciklama    TEXT,
    zaman       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aktif_perk (
    id           SERIAL      PRIMARY KEY,
    discord_id   BIGINT      NOT NULL,
    perk_id      TEXT        NOT NULL,
    bitis_tarihi TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (discord_id, perk_id)
);

CREATE TABLE IF NOT EXISTS perk_satin_alma (
    id              BIGSERIAL   PRIMARY KEY,
    discord_id      BIGINT      NOT NULL,
    perk_id         TEXT        NOT NULL,
    tarih           DATE        NOT NULL,
    hafta_no        TEXT        NOT NULL,
    satin_alindi_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patron_savas (
    id              BIGSERIAL   PRIMARY KEY,
    patron_id       TEXT        NOT NULL,
    discord_id      BIGINT      NOT NULL,
    toplam_hasar    INT         DEFAULT 0,
    saldiri_sayisi  INT         DEFAULT 0,
    zaman           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (patron_id, discord_id)
);

CREATE TABLE IF NOT EXISTS patron_haftalik_odul_log (
    id         SERIAL      PRIMARY KEY,
    hafta_no   TEXT        NOT NULL,
    discord_id BIGINT      NOT NULL,
    sira       INT         NOT NULL,
    gem_odul   INT         NOT NULL,
    verildi_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hafta_no, discord_id)
);

CREATE TABLE IF NOT EXISTS referans_log (
    id              SERIAL      PRIMARY KEY,
    davet_eden_id   BIGINT      NOT NULL,
    davet_edilen_id BIGINT      NOT NULL,
    odul_coin       INT         DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (davet_edilen_id)
);

CREATE TABLE IF NOT EXISTS gunluk_gorev_log (
    id           BIGSERIAL   PRIMARY KEY,
    discord_id   BIGINT      NOT NULL,
    isim         TEXT,
    gorev_id     TEXT        NOT NULL,
    gorev_baslik TEXT,
    durum        TEXT        NOT NULL,
    tarih        TEXT        NOT NULL,
    kanit        TEXT,
    odul         INT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    ek_gorev     BOOLEAN     DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS pq_karakter (
    discord_id    BIGINT PRIMARY KEY,
    irk           TEXT,
    avatar_ikon   TEXT,
    hp            INT DEFAULT 0,
    max_hp        INT DEFAULT 0,
    xp            INT DEFAULT 0,
    altin         INT DEFAULT 0,
    silah_id      TEXT,
    kalkan_id     TEXT,
    kemer_id      TEXT,
    toplam_kill   INT DEFAULT 0,
    toplam_olum   INT DEFAULT 0,
    en_derin_kat  INT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pq_envanter (
    id        BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    tur        TEXT,
    isim       TEXT,
    kategori   TEXT,
    ikon       INT,
    bonus      INT DEFAULT 0,
    nadirlik   TEXT,
    adet       INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pq_savas_log (
    id         BIGSERIAL   PRIMARY KEY,
    discord_id BIGINT      NOT NULL,
    canavar    TEXT,
    sonuc      TEXT,
    hasar      INT DEFAULT 0,
    xp         INT DEFAULT 0,
    altin      INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

# SERIAL kolonlara sahip tablolar — restore sonrası sequence sıfırlanacak
SERIAL_TABLES = [
    "hazine_log", "market_satin_alma", "user_costumes", "boost_log",
    "coin_log", "gem_log", "aktif_perk", "perk_satin_alma",
    "patron_savas", "patron_haftalik_odul_log", "referans_log",
    "gunluk_gorev_log", "pq_envanter", "pq_savas_log",
]

# Restore sırası (bağımlılıklara göre)
TABLE_ORDER = [
    "coins", "gem_bakiye", "coin_log", "gem_log",
    "hazine_log", "market_satin_alma", "user_costumes",
    "boost_log", "gorev_log", "gunluk_gorev_log",
    "mac_tahmin", "mac_bilgi", "market_gunluk",
    "aktif_perk", "perk_satin_alma", "patron_savas",
    "patron_haftalik_odul_log", "referans_log",
    "pq_karakter", "pq_envanter", "pq_savas_log",
]


async def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("HATA: DATABASE_URL environment variable set edilmemis!")
        print("Kullanim: $env:DATABASE_URL='postgresql://...' ; python restore_db.py")
        sys.exit(1)

    print(f"Baglaniyor...")
    conn = await asyncpg.connect(url)
    print("OK - Baglanti kuruldu.")

    print("\n[1/3] Tablolar olusturuluyor...")
    await conn.execute(CREATE_SQL)
    print("OK - Tum tablolar hazir.")

    print("\n[2/3] Veriler yukleniyor...")
    basarili = []
    basarisiz = []

    for table in TABLE_ORDER:
        csv_path = RESTORE_DIR / f"{table}.csv"
        if not csv_path.exists():
            continue
        try:
            with open(csv_path, "rb") as f:
                await conn.copy_to_table(
                    table,
                    source=f,
                    format="csv",
                    header=True,
                )
            size = csv_path.stat().st_size
            print(f"  OK  {table:<35} ({size:,} byte)")
            basarili.append(table)
        except Exception as e:
            print(f"  HATA {table:<33} -> {e}")
            basarisiz.append(table)

    print("\n[3/3] Sequence'ler sifirlaniyor...")
    for table in SERIAL_TABLES:
        if table not in basarili:
            continue
        try:
            await conn.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 0) + 1,
                    false
                )
            """)
            print(f"  OK  {table}")
        except Exception as e:
            print(f"  ATLA {table} -> {e}")

    await conn.close()

    print(f"\n{'='*50}")
    print(f"Restore tamamlandi!")
    print(f"  Basarili : {len(basarili)} tablo")
    if basarisiz:
        print(f"  Basarisiz: {len(basarisiz)} tablo -> {basarisiz}")
    print(f"{'='*50}")
    print("\nArtik botu deploy edebilirsin.")


if __name__ == "__main__":
    asyncio.run(main())
