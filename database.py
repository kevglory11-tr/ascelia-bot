"""
database.py — PostgreSQL bağlantısı. M2Board Coin + EXP + Profil sistemi.
"""

import asyncpg
import os
import json
from utils.logger import setup_logger

log = setup_logger("database")
pool: asyncpg.Pool = None


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


async def add_coins(discord_id: int, username: str, miktar: int) -> int:
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
        return row["bakiye"]


async def remove_coins(discord_id: int, miktar: int) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT bakiye FROM coins WHERE discord_id = $1", discord_id)
        if not row or row["bakiye"] < miktar:
            return False
        await conn.execute(
            "UPDATE coins SET bakiye = bakiye - $2 WHERE discord_id = $1",
            discord_id, miktar
        )
        return True


async def set_son_giris(discord_id: int, tarih_str: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE coins SET son_giris = $2 WHERE discord_id = $1", discord_id, tarih_str
        )


async def get_leaderboard(limit: int = 10):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT username, bakiye, level FROM coins ORDER BY bakiye DESC LIMIT $1", limit
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
