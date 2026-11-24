"""SQLite persistence layer for players, mission runs, and leaderboards."""

import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "bobbery_rob.db"

_CODENAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class GameDatabase:
    """Lightweight SQLite store for Bobbery Rob codenames and ranked runs."""

    def __init__(self, db_path: Union[str, Path, None] = None) -> None:
        self._db_path = str(DEFAULT_DB_PATH if db_path is None else db_path)
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self._db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _close(self, conn: sqlite3.Connection) -> None:
        if conn is not self._memory_conn:
            conn.close()

    def close(self) -> None:
        """Close the persistent in-memory connection if open."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    player_id TEXT PRIMARY KEY,
                    codename TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id TEXT NOT NULL,
                    codename TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    ending_id TEXT NOT NULL,
                    category TEXT,
                    raw_seconds REAL NOT NULL,
                    adjusted_seconds REAL,
                    final_suspicion INTEGER NOT NULL,
                    objectives_done INTEGER NOT NULL,
                    objectives_total INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_runs_category_time
                    ON runs(category, adjusted_seconds);
                CREATE INDEX IF NOT EXISTS idx_runs_player_time
                    ON runs(player_id, adjusted_seconds);
                """
            )
            conn.commit()
        finally:
            self._close(conn)

    def register_or_get_player(self, codename: str) -> dict[str, Any]:
        """Validate codename and return or create the player record."""
        name = (codename or "").strip()
        if not name:
            return {"ok": False, "player_id": None, "error": "Enter a codename to continue."}
        if not 3 <= len(name) <= 16:
            return {"ok": False, "player_id": None, "error": "Codename must be 3–16 characters."}
        if not _CODENAME_RE.fullmatch(name):
            return {
                "ok": False,
                "player_id": None,
                "error": "Use letters, numbers, hyphens and underscores only.",
            }

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT player_id FROM players WHERE codename = ? COLLATE NOCASE",
                (name,),
            ).fetchone()
            if row is not None:
                return {"ok": True, "player_id": row["player_id"], "error": None}

            player_id = f"plr-{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO players (player_id, codename, created_at) VALUES (?, ?, ?)",
                (player_id, name, now),
            )
            conn.commit()
            return {"ok": True, "player_id": player_id, "error": None}
        finally:
            self._close(conn)

    def get_personal_best(self, player_id: str) -> Optional[float]:
        """Return the player's fastest ranked adjusted time, or None."""
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT MIN(adjusted_seconds) AS best_time
                FROM runs
                WHERE player_id = ? AND adjusted_seconds IS NOT NULL
                """,
                (player_id,),
            ).fetchone()
            if row is None or row["best_time"] is None:
                return None
            return round(float(row["best_time"]), 2)
        finally:
            self._close(conn)

    def record_run(
        self,
        *,
        player_id: str,
        codename: str,
        scenario_id: str,
        ending_id: str,
        category: Optional[str],
        raw_seconds: float,
        adjusted_seconds: Optional[float],
        final_suspicion: int,
        objectives_done: int,
        objectives_total: int,
    ) -> dict[str, Any]:
        """Persist a finished run and compute personal best / new record flags."""
        prev_best = self.get_personal_best(player_id)
        is_new_record = adjusted_seconds is not None and (
            prev_best is None or float(adjusted_seconds) < prev_best
        )

        conn = self._connect()
        try:
            now = datetime.now(timezone.utc).isoformat()
            cursor = conn.execute(
                """
                INSERT INTO runs (
                    player_id, codename, scenario_id, ending_id, category,
                    raw_seconds, adjusted_seconds, final_suspicion,
                    objectives_done, objectives_total, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player_id,
                    codename,
                    scenario_id,
                    ending_id,
                    category,
                    round(float(raw_seconds), 2),
                    round(float(adjusted_seconds), 2) if adjusted_seconds is not None else None,
                    int(final_suspicion),
                    int(objectives_done),
                    int(objectives_total),
                    now,
                ),
            )
            conn.commit()
            run_id = cursor.lastrowid
        finally:
            self._close(conn)

        personal_best = (
            round(float(adjusted_seconds), 2)
            if is_new_record and adjusted_seconds is not None
            else prev_best
        )
        return {
            "run_id": run_id,
            "personal_best_seconds": personal_best,
            "is_new_record": is_new_record,
        }

    def get_leaderboard(self, category: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return top ranked players by fastest adjusted time in `category`."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT codename, MIN(adjusted_seconds) AS best_seconds
                FROM runs
                WHERE category = ? AND adjusted_seconds IS NOT NULL
                GROUP BY player_id
                ORDER BY best_seconds ASC
                LIMIT ?
                """,
                (category, int(limit)),
            ).fetchall()
            return [
                {
                    "rank": idx,
                    "player": row["codename"],
                    "time_seconds": int(round(float(row["best_seconds"]))),
                }
                for idx, row in enumerate(rows, start=1)
            ]
        finally:
            self._close(conn)
