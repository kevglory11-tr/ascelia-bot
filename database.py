"""
database.py — PostgreSQL bağlantısı. M2Board Coin + EXP + Profil sistemi.
"""

import asyncpg
import os
import json
from datetime import datetime, timezone, timedelta, date
from utils.logger import setup_logger

log = setup_logger("database")
pool: asyncpg.Pool = None

_TR = timedelta(hours=3)


def _tr_bugun() -> date:
    """Railway UTC sunucusunda Türkiye saatiyle (UTC+3) bugünün tarihini döndürür."""
    return (datetime.now(timezone.utc) + _TR).date()


def _tr_hafta_no() -> str:
    """Türkiye saatiyle (UTC+3) ISO hafta numarasını döndürür. Örn: '2026-14'"""
    now = datetime.now(timezone.utc) + _TR
    iso = now.isocalendar()
    return f"{iso[0]}-{iso[1]:02d}"


async def init_pool() -> None:
    global pool
    url = os.getenv("DATABASE_URL")
    if not url:
        log.critical("DATABASE_URL bulunamadı!")
        return
    pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
    await _create_tables()
    await _migrate()
    log.info("✅ PostgreSQL bağlantısı kuruldu.")


async def _create_tables() -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
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
                son_mesaj_exp       TIMESTAMPTZ DEFAULT NULL
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
                kapali      BOOLEAN DEFAULT FALSE
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
        """)
    log.info("✅ Tablolar hazır.")


async def _migrate() -> None:
    """Mevcut tabloya yeni kolonları ekle (varsa atla)."""
    yeni_kolonlar = [
        ("level",            "INT DEFAULT 1"),
        ("exp",              "BIGINT DEFAULT 0"),
        ("rozet_listesi",    "JSONB DEFAULT '[]'"),
        ("aktif_rozet",      "TEXT DEFAULT NULL"),
        ("profil_renk",      "TEXT DEFAULT '2b2d31'"),
        ("profil_bio",       "TEXT DEFAULT NULL"),
        ("profil_arka_plan", "TEXT DEFAULT 'varsayilan'"),
        ("boost_seviye",     "INT DEFAULT 0"),
        ("boost_baslangic",  "TIMESTAMPTZ DEFAULT NULL"),
        ("son_mesaj_exp",    "TIMESTAMPTZ DEFAULT NULL"),
        ("giris_serisi",     "INT DEFAULT 0"),
        ("toplam_kazanilan", "BIGINT DEFAULT 0"),
    ]
    async with pool.acquire() as conn:
        for kolon, tip in yeni_kolonlar:
            try:
                await conn.execute(
                    f"ALTER TABLE coins ADD COLUMN IF NOT EXISTS {kolon} {tip}"
                )
            except Exception:
                pass

        # mac_bilgi tablosuna gercek_skor ekle
        try:
            await conn.execute(
                "ALTER TABLE mac_bilgi ADD COLUMN IF NOT EXISTS gercek_skor TEXT DEFAULT NULL"
            )
        except Exception:
            pass

        # coins tablosuna luminary_bonus ekle
        try:
            await conn.execute(
                "ALTER TABLE coins ADD COLUMN IF NOT EXISTS luminary_bonus INT DEFAULT 0"
            )
        except Exception:
            pass

        # gunluk_gorev_log tablosuna ek_gorev ekle
        try:
            await conn.execute(
                "ALTER TABLE gunluk_gorev_log ADD COLUMN IF NOT EXISTS ek_gorev BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            pass

        # Patron haftalık ödül log tablosu
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS patron_haftalik_odul_log (
                    id         SERIAL      PRIMARY KEY,
                    hafta_no   TEXT        NOT NULL,
                    discord_id BIGINT      NOT NULL,
                    sira       INT         NOT NULL,
                    gem_odul   INT         NOT NULL,
                    verildi_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE (hafta_no, discord_id)
                )
            """)
        except Exception:
            pass
        # Referans sistemi tablosu
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referans_log (
                    id              SERIAL      PRIMARY KEY,
                    davet_eden_id   BIGINT      NOT NULL,
                    davet_edilen_id BIGINT      NOT NULL,
                    odul_coin       INT         DEFAULT 0,
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE (davet_edilen_id)
                )
            """)
        except Exception:
            pass
    log.info("✅ Migrasyon tamamlandı.")


# ── Kullanıcı CRUD ─────────────────────────────────────────────────────────────

async def get_user(discord_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM coins WHERE discord_id = $1", discord_id)


async def ensure_user(discord_id: int, username: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO coins (discord_id, username)
            VALUES ($1, $2)
            ON CONFLICT (discord_id) DO UPDATE SET username = EXCLUDED.username
        """, discord_id, username)
        return await conn.fetchrow("SELECT * FROM coins WHERE discord_id = $1", discord_id)


async def add_coins(discord_id: int, username: str, miktar: int, aciklama: str = None) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO coins (discord_id, username, bakiye, toplam_kazanilan)
            VALUES ($1, $2, $3, $3)
            ON CONFLICT (discord_id) DO UPDATE
                SET bakiye           = coins.bakiye + EXCLUDED.bakiye,
                    toplam_kazanilan = coins.toplam_kazanilan + EXCLUDED.bakiye,
                    username         = EXCLUDED.username
            RETURNING bakiye
        """, discord_id, username, miktar)
        await conn.execute(
            "INSERT INTO coin_log (discord_id, miktar, tip, aciklama) VALUES ($1, $2, 'kazanc', $3)",
            discord_id, miktar, aciklama
        )
        return row["bakiye"]


async def remove_coins(discord_id: int, miktar: int, aciklama: str = None) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE coins SET bakiye = bakiye - $2 WHERE discord_id = $1 AND bakiye >= $2 RETURNING bakiye",
            discord_id, miktar
        )
        if not row:
            return False
        await conn.execute(
            "INSERT INTO coin_log (discord_id, miktar, tip, aciklama) VALUES ($1, $2, 'harcama', $3)",
            discord_id, miktar, aciklama
        )
        return True


async def set_son_giris(discord_id: int, tarih_str: str) -> int:
    """son_giris güncelle, seriyi artır. Yeni seri değerini döndürür."""
    from datetime import date, timedelta
    bugun  = date.fromisoformat(tarih_str)
    dun    = bugun - timedelta(days=1)
    async with pool.acquire() as conn:
        kayit = await conn.fetchrow(
            "SELECT son_giris, giris_serisi FROM coins WHERE discord_id=$1", discord_id
        )
        son    = kayit["son_giris"] if kayit else None
        seri   = kayit["giris_serisi"] if kayit else 0

        if son == dun:
            yeni_seri = seri + 1   # dün girdiyse seri devam
        else:
            yeni_seri = 1          # atlama veya ilk giriş

        await conn.execute(
            "UPDATE coins SET son_giris=$2, giris_serisi=$3 WHERE discord_id=$1",
            discord_id, bugun, yeni_seri
        )
    return yeni_seri


async def get_leaderboard(limit: int = 10):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT discord_id, username, bakiye, level FROM coins ORDER BY bakiye DESC LIMIT $1",
            limit,
        )


# ── EXP & Level ───────────────────────────────────────────────────────────────

def exp_gereken(level: int) -> int:
    """Sonraki level için gereken toplam EXP."""
    return level * 100


async def add_exp(discord_id: int, username: str, miktar: int) -> dict:
    """
    EXP ekle. Level atlama kontrolü yapar.
    Dönüş: {"level": int, "exp": int, "level_up": bool, "coin_odulu": int}
    """
    kayit = await ensure_user(discord_id, username)
    yeni_exp   = kayit["exp"] + miktar
    level      = kayit["level"]
    coin_odulu = 0
    level_up   = False

    while yeni_exp >= exp_gereken(level):
        yeni_exp -= exp_gereken(level)
        level    += 1
        level_up  = True
        coin_odulu += level * 10   # level * 10 coin ödülü

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE coins SET exp = $2, level = $3 WHERE discord_id = $1",
            discord_id, yeni_exp, level
        )

    if coin_odulu > 0:
        await add_coins(discord_id, username, coin_odulu)

    return {"level": level, "exp": yeni_exp, "level_up": level_up, "coin_odulu": coin_odulu}


# ── Rozet sistemi ─────────────────────────────────────────────────────────────

async def get_rozet_listesi(discord_id: int) -> list:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT rozet_listesi FROM coins WHERE discord_id = $1", discord_id
        )
        if not row:
            return []
        val = row["rozet_listesi"]
        if isinstance(val, str):
            return json.loads(val)
        return list(val) if val else []


async def add_rozet(discord_id: int, rozet_id: str) -> None:
    liste = await get_rozet_listesi(discord_id)
    if rozet_id not in liste:
        liste.append(rozet_id)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE coins SET rozet_listesi = $2::jsonb WHERE discord_id = $1",
            discord_id, json.dumps(liste)
        )


async def set_aktif_rozet(discord_id: int, rozet_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE coins SET aktif_rozet = $2 WHERE discord_id = $1",
            discord_id, rozet_id
        )


# ── Kostüm sistemi ────────────────────────────────────────────────────────────

async def add_costume(discord_id: int, costume_id: str, costume_name: str, rarity: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_costumes (discord_id, costume_id, costume_name, rarity)
            VALUES ($1, $2, $3, $4)
        """, discord_id, costume_id, costume_name, rarity)


async def get_costumes(discord_id: int):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM user_costumes WHERE discord_id = $1 ORDER BY kazanildi_at DESC",
            discord_id
        )


# ── Profil güncelleme ─────────────────────────────────────────────────────────

async def update_profil(discord_id: int, **kwargs) -> None:
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE coins SET {sets} WHERE discord_id = $1",
            discord_id, *kwargs.values()
        )


# ── Boost sistemi ─────────────────────────────────────────────────────────────

# ── Gem sistemi ───────────────────────────────────────────────────────────────

async def get_gem_bakiye(discord_id: int) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT miktar FROM gem_bakiye WHERE discord_id = $1", discord_id)
        return row["miktar"] if row else 0


async def add_gem(discord_id: int, miktar: int, tip: str, aciklama: str = None) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO gem_bakiye (discord_id, miktar)
            VALUES ($1, $2)
            ON CONFLICT (discord_id) DO UPDATE
                SET miktar = gem_bakiye.miktar + EXCLUDED.miktar
            RETURNING miktar
        """, discord_id, miktar)
        await conn.execute(
            "INSERT INTO gem_log (discord_id, miktar, tip, aciklama) VALUES ($1,$2,$3,$4)",
            discord_id, miktar, tip, aciklama
        )
        return row["miktar"]


async def remove_gem(discord_id: int, miktar: int, tip: str, aciklama: str = None) -> bool:
    """Atomik güncelleme — bakiye yetersizse False döner, race condition olmaz."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE gem_bakiye SET miktar = miktar - $2 WHERE discord_id = $1 AND miktar >= $2 RETURNING miktar",
            discord_id, miktar
        )
        if not row:
            return False
        await conn.execute(
            "INSERT INTO gem_log (discord_id, miktar, tip, aciklama) VALUES ($1,$2,$3,$4)",
            discord_id, -miktar, tip, aciklama
        )
        return True


# ── Perk sistemi ──────────────────────────────────────────────────────────────

async def get_aktif_perk(discord_id: int, perk_id: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM aktif_perk WHERE discord_id=$1 AND perk_id=$2 AND bitis_tarihi > NOW()",
            discord_id, perk_id
        )
        return row


async def get_tum_aktif_perkler(discord_id: int) -> list:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM aktif_perk WHERE discord_id=$1 AND bitis_tarihi > NOW()",
            discord_id
        )


async def set_aktif_perk(discord_id: int, perk_id: str, sure_gun: int = 0, sure_saat: int = 0):
    from datetime import datetime, timezone, timedelta
    bitis = datetime.now(timezone.utc) + timedelta(days=sure_gun, hours=sure_saat)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO aktif_perk (discord_id, perk_id, bitis_tarihi)
            VALUES ($1, $2, $3)
            ON CONFLICT (discord_id, perk_id) DO UPDATE
                SET bitis_tarihi = EXCLUDED.bitis_tarihi
        """, discord_id, perk_id, bitis)
    return bitis


async def perk_haftalik_limit_kontrol(discord_id: int, perk_id: str) -> bool:
    hafta_no = _tr_hafta_no()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM perk_satin_alma WHERE discord_id=$1 AND perk_id=$2 AND hafta_no=$3",
            discord_id, perk_id, hafta_no
        )
        return row is not None


async def perk_gunluk_limit_kontrol(discord_id: int, perk_id: str) -> bool:
    bugun = _tr_bugun()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM perk_satin_alma WHERE discord_id=$1 AND perk_id=$2 AND tarih=$3",
            discord_id, perk_id, bugun
        )
        return row is not None


async def perk_satin_alma_kaydet(discord_id: int, perk_id: str) -> None:
    bugun    = _tr_bugun()
    hafta_no = _tr_hafta_no()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO perk_satin_alma (discord_id, perk_id, tarih, hafta_no) VALUES ($1,$2,$3,$4)",
            discord_id, perk_id, bugun, hafta_no
        )


async def temizle_suresi_dolan_perkler(perk_idler: list = None) -> list:
    async with pool.acquire() as conn:
        if perk_idler:
            rows = await conn.fetch(
                "DELETE FROM aktif_perk WHERE bitis_tarihi < NOW() AND perk_id = ANY($1) RETURNING discord_id, perk_id",
                perk_idler
            )
        else:
            rows = await conn.fetch(
                "DELETE FROM aktif_perk WHERE bitis_tarihi < NOW() RETURNING discord_id, perk_id"
            )
        return [(r["discord_id"], r["perk_id"]) for r in rows]


# ── Rol & Lifetime görev ──────────────────────────────────────────────────────

async def get_lifetime_gorev_sayisi(discord_id: int) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM gunluk_gorev_log WHERE discord_id=$1 AND durum IN ('tamamlandi','onaylandi')",
            discord_id
        ) or 0


# ── Patron sistemi ────────────────────────────────────────────────────────────

async def patron_hasar_kaydet(patron_id: str, discord_id: int, hasar: int, saldiri_sayisi: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO patron_savas (patron_id, discord_id, toplam_hasar, saldiri_sayisi)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (patron_id, discord_id) DO UPDATE
                SET toplam_hasar   = patron_savas.toplam_hasar   + EXCLUDED.toplam_hasar,
                    saldiri_sayisi = patron_savas.saldiri_sayisi + EXCLUDED.saldiri_sayisi
        """, patron_id, discord_id, hasar, saldiri_sayisi)


async def patron_saldiri_sayisi_al(patron_id: str, discord_id: int) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT saldiri_sayisi FROM patron_savas WHERE patron_id=$1 AND discord_id=$2",
            patron_id, discord_id
        )
        return row["saldiri_sayisi"] if row else 0


async def patron_hasar_siralaması(patron_id: str, limit: int = 3) -> list:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT discord_id, toplam_hasar FROM patron_savas WHERE patron_id=$1 ORDER BY toplam_hasar DESC LIMIT $2",
            patron_id, limit
        )


async def patron_haftalik_siralama(hafta_no: str, limit: int = 10) -> list:
    """O haftaki toplam hasara göre sıralama döndürür."""
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT discord_id, SUM(toplam_hasar) AS haftalik_hasar
            FROM patron_savas
            WHERE TO_CHAR(zaman + INTERVAL '3 hours', 'IYYY-IW') = $1
            GROUP BY discord_id
            ORDER BY haftalik_hasar DESC
            LIMIT $2
        """, hafta_no, limit)


async def patron_haftalik_odul_verildi(hafta_no: str) -> bool:
    """O hafta için ödül verilip verilmediğini kontrol eder."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM patron_haftalik_odul_log WHERE hafta_no=$1 LIMIT 1",
            hafta_no
        )
        return row is not None


async def patron_haftalik_odul_kaydet(hafta_no: str, discord_id: int, sira: int, gem_odul: int) -> None:
    """Haftalık ödül kaydeder (tekrar verilmesini önler)."""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO patron_haftalik_odul_log (hafta_no, discord_id, sira, gem_odul)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (hafta_no, discord_id) DO NOTHING
        """, hafta_no, discord_id, sira, gem_odul)


async def update_boost(discord_id: int, seviye: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE coins SET boost_seviye = $2, boost_baslangic = CASE
                WHEN $2 > 0 AND boost_baslangic IS NULL THEN NOW()
                WHEN $2 = 0 THEN NULL
                ELSE boost_baslangic
            END
            WHERE discord_id = $1
        """, discord_id, seviye)
