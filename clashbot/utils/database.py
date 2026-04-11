"""
SQLite veritabanı modülü – aiosqlite tabanlı.
JSON dosyaları yerine kalıcı, sorgulanabilir depolama sağlar.

Tablolar:
  - players          : Oyuncu anlık verileri (son güncelleme)
  - donation_history : Haftalık bağış geçmişi
  - war_history      : Haftalık savaş katkı geçmişi
  - activity_log     : Aktivite skoru geçmişi
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

log = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "clashbot.db")

# ── SQL Injection Koruması – İzin verilen sütun adları ────────────
ALLOWED_PLAYER_COLUMNS = frozenset({
    "tag", "name", "role", "trophies", "best_trophies", "exp_level",
    "donations", "donations_received", "war_fame", "decks_used",
    "last_seen", "updated_at",
})


class Database:
    """Async SQLite veritabanı yöneticisi."""

    def __init__(self) -> None:
        self._db: Optional[aiosqlite.Connection] = None

    # ── Bağlantı Yönetimi ────────────────────────────────────────────

    async def connect(self) -> None:
        """Veritabanına bağlan ve tabloları oluştur."""
        os.makedirs(DB_DIR, exist_ok=True)
        self._db = await aiosqlite.connect(DB_PATH)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()
        log.info("SQLite veritabanı bağlantısı kuruldu: %s", DB_PATH)

    async def close(self) -> None:
        """Veritabanı bağlantısını kapat."""
        if self._db:
            await self._db.close()
            self._db = None
            log.info("SQLite veritabanı bağlantısı kapatıldı.")

    async def _create_tables(self) -> None:
        """Gerekli tabloları oluştur (yoksa)."""
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                tag             TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                role            TEXT DEFAULT 'member',
                trophies        INTEGER DEFAULT 0,
                best_trophies   INTEGER DEFAULT 0,
                exp_level       INTEGER DEFAULT 1,
                donations       INTEGER DEFAULT 0,
                donations_received INTEGER DEFAULT 0,
                war_fame        INTEGER DEFAULT 0,
                decks_used      INTEGER DEFAULT 0,
                last_seen       TEXT,
                updated_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS donation_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_tag  TEXT NOT NULL,
                player_name TEXT NOT NULL,
                donations   INTEGER DEFAULT 0,
                donations_received INTEGER DEFAULT 0,
                week_start  TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                UNIQUE(player_tag, week_start)
            );

            CREATE TABLE IF NOT EXISTS war_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_tag  TEXT NOT NULL,
                player_name TEXT NOT NULL,
                fame        INTEGER DEFAULT 0,
                decks_used  INTEGER DEFAULT 0,
                boat_attacks INTEGER DEFAULT 0,
                week_start  TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                UNIQUE(player_tag, week_start)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_tag  TEXT NOT NULL,
                player_name TEXT NOT NULL,
                score       REAL DEFAULT 0.0,
                donation_score REAL DEFAULT 0.0,
                war_score   REAL DEFAULT 0.0,
                trophy_score REAL DEFAULT 0.0,
                recorded_at TEXT NOT NULL,
                UNIQUE(player_tag, recorded_at)
            );

            CREATE TABLE IF NOT EXISTS trophy_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_tag  TEXT NOT NULL,
                trophies    INTEGER DEFAULT 0,
                recorded_at TEXT NOT NULL,
                UNIQUE(player_tag, recorded_at)
            );

            CREATE TABLE IF NOT EXISTS server_settings (
                guild_id    TEXT PRIMARY KEY,
                language    TEXT DEFAULT 'en'
            );
        """)
        await self._db.commit()

    # ── Oyuncu CRUD ──────────────────────────────────────────────────

    async def upsert_player(self, tag: str, **kwargs) -> None:
        """Oyuncu ekle veya güncelle."""
        now = datetime.now(timezone.utc).isoformat()
        kwargs["updated_at"] = now
        kwargs["tag"] = tag

        # SQL Injection koruması: yalnızca beyaz listedeki sütun adlarına izin ver
        invalid_keys = set(kwargs.keys()) - ALLOWED_PLAYER_COLUMNS
        if invalid_keys:
            raise ValueError(
                f"Geçersiz sütun adı tespit edildi: {invalid_keys}"
            )

        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        updates = ", ".join(
            f"{k}=excluded.{k}" for k in kwargs if k != "tag"
        )

        sql = f"""
            INSERT INTO players ({columns})
            VALUES ({placeholders})
            ON CONFLICT(tag) DO UPDATE SET {updates}
        """
        await self._db.execute(sql, list(kwargs.values()))
        await self._db.commit()

    async def upsert_many_players(self, players: list[dict]) -> None:
        """Birden fazla oyuncuyu toplu ekle/güncelle."""
        now = datetime.now(timezone.utc).isoformat()
        for p in players:
            await self._db.execute("""
                INSERT INTO players (tag, name, role, trophies, best_trophies,
                                     exp_level, donations, donations_received, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tag) DO UPDATE SET
                    name=excluded.name,
                    role=excluded.role,
                    trophies=excluded.trophies,
                    best_trophies=excluded.best_trophies,
                    exp_level=excluded.exp_level,
                    donations=excluded.donations,
                    donations_received=excluded.donations_received,
                    updated_at=excluded.updated_at
            """, (
                p.get("tag"),
                p.get("name", "Bilinmiyor"),
                p.get("role", "member"),
                p.get("trophies", 0),
                p.get("bestTrophies", 0),
                p.get("expLevel", 1),
                p.get("donations", 0),
                p.get("donationsReceived", 0),
                now,
            ))
        await self._db.commit()

    async def get_player(self, tag: str) -> Optional[dict]:
        """Tek oyuncu verisi döndürür."""
        cursor = await self._db.execute(
            "SELECT * FROM players WHERE tag = ?", (tag,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def get_all_players(self) -> list[dict]:
        """Tüm oyuncuları döndürür."""
        cursor = await self._db.execute("SELECT * FROM players ORDER BY trophies DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Bağış Geçmişi ───────────────────────────────────────────────

    async def save_donation_snapshot(
        self, player_tag: str, player_name: str,
        donations: int, donations_received: int, week_start: str
    ) -> None:
        """Haftalık bağış anlık görüntüsü kaydet."""
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute("""
            INSERT INTO donation_history
                (player_tag, player_name, donations, donations_received, week_start, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_tag, week_start) DO UPDATE SET
                donations=excluded.donations,
                donations_received=excluded.donations_received,
                recorded_at=excluded.recorded_at
        """, (player_tag, player_name, donations, donations_received, week_start, now))
        await self._db.commit()

    async def get_donation_history(self, player_tag: str, limit: int = 10) -> list[dict]:
        """Oyuncunun son N haftalık bağış geçmişi."""
        cursor = await self._db.execute("""
            SELECT * FROM donation_history
            WHERE player_tag = ?
            ORDER BY week_start DESC
            LIMIT ?
        """, (player_tag, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Savaş Geçmişi ───────────────────────────────────────────────

    async def save_war_snapshot(
        self, player_tag: str, player_name: str,
        fame: int, decks_used: int, boat_attacks: int, week_start: str
    ) -> None:
        """Haftalık savaş anlık görüntüsü kaydet."""
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute("""
            INSERT INTO war_history
                (player_tag, player_name, fame, decks_used, boat_attacks, week_start, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_tag, week_start) DO UPDATE SET
                fame=excluded.fame,
                decks_used=excluded.decks_used,
                boat_attacks=excluded.boat_attacks,
                recorded_at=excluded.recorded_at
        """, (player_tag, player_name, fame, decks_used, boat_attacks, week_start, now))
        await self._db.commit()

    async def get_war_history(self, player_tag: str, limit: int = 10) -> list[dict]:
        """Oyuncunun son N haftalık savaş geçmişi."""
        cursor = await self._db.execute("""
            SELECT * FROM war_history
            WHERE player_tag = ?
            ORDER BY week_start DESC
            LIMIT ?
        """, (player_tag, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Aktivite Skoru ───────────────────────────────────────────────

    async def save_activity_score(
        self, player_tag: str, player_name: str,
        score: float, donation_score: float,
        war_score: float, trophy_score: float
    ) -> None:
        """Aktivite skorunu kaydet."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await self._db.execute("""
            INSERT INTO activity_log
                (player_tag, player_name, score, donation_score, war_score, trophy_score, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_tag, recorded_at) DO UPDATE SET
                score=excluded.score,
                donation_score=excluded.donation_score,
                war_score=excluded.war_score,
                trophy_score=excluded.trophy_score
        """, (player_tag, player_name, score, donation_score, war_score, trophy_score, today))
        await self._db.commit()

    async def get_activity_scores(self, date: str = None) -> list[dict]:
        """Belirli bir günün aktivite skorlarını döndürür."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = await self._db.execute("""
            SELECT * FROM activity_log
            WHERE recorded_at = ?
            ORDER BY score DESC
        """, (date,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_player_activity_history(
        self, player_tag: str, limit: int = 30
    ) -> list[dict]:
        """Oyuncunun son N günlük aktivite skoru geçmişi."""
        cursor = await self._db.execute("""
            SELECT * FROM activity_log
            WHERE player_tag = ?
            ORDER BY recorded_at DESC
            LIMIT ?
        """, (player_tag, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Kupa Anlık Görüntüsü ────────────────────────────────────────

    async def save_trophy_snapshot(self, player_tag: str, trophies: int) -> None:
        """Günlük kupa anlık görüntüsü kaydet."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await self._db.execute("""
            INSERT INTO trophy_snapshots (player_tag, trophies, recorded_at)
            VALUES (?, ?, ?)
            ON CONFLICT(player_tag, recorded_at) DO UPDATE SET
                trophies=excluded.trophies
        """, (player_tag, trophies, today))
        await self._db.commit()

    async def get_trophy_change(self, player_tag: str, days: int = 7) -> int:
        """Son N gündeki kupa değişimini hesaplar."""
        cursor = await self._db.execute("""
            SELECT trophies FROM trophy_snapshots
            WHERE player_tag = ?
            ORDER BY recorded_at ASC
            LIMIT 1
        """, (player_tag,))
        oldest = await cursor.fetchone()

        cursor2 = await self._db.execute("""
            SELECT trophies FROM trophy_snapshots
            WHERE player_tag = ?
            ORDER BY recorded_at DESC
            LIMIT 1
        """, (player_tag,))
        newest = await cursor2.fetchone()

        if oldest and newest:
            return newest["trophies"] - oldest["trophies"]
        return 0

    # ── İstatistik Sorguları ─────────────────────────────────────────

    async def get_top_donors(self, limit: int = 10) -> list[dict]:
        """En çok bağış yapan oyuncular (mevcut hafta)."""
        cursor = await self._db.execute("""
            SELECT tag, name, donations, donations_received
            FROM players
            ORDER BY donations DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_clan_donation_average(self) -> float:
        """Klan bağış ortalaması."""
        cursor = await self._db.execute(
            "SELECT AVG(donations) as avg_don FROM players"
        )
        row = await cursor.fetchone()
        return row["avg_don"] if row and row["avg_don"] else 0.0

    async def get_player_count(self) -> int:
        """Veritabanındaki oyuncu sayısı."""
        cursor = await self._db.execute("SELECT COUNT(*) as cnt FROM players")
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    # ── Sunucu Ayarları ──────────────────────────────────────────────

    async def get_guild_language(self, guild_id: int) -> str:
        """Sunucunun dil tercihini döndürür."""
        cursor = await self._db.execute(
            "SELECT language FROM server_settings WHERE guild_id = ?", (str(guild_id),)
        )
        row = await cursor.fetchone()
        return row["language"] if row else "en"

    async def set_guild_language(self, guild_id: int, lang: str) -> None:
        """Sunucunun dil tercihini günceller."""
        await self._db.execute("""
            INSERT INTO server_settings (guild_id, language)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET language=excluded.language
        """, (str(guild_id), lang))
        await self._db.commit()

    async def get_all_guild_settings(self) -> list[dict]:
        """Tüm sunucu ayarlarını döndürür (başlangıçta cache yüklemek için)."""
        cursor = await self._db.execute("SELECT * FROM server_settings")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]