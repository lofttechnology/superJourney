import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserProgressRepository:
    """SQLite persistence for current runs and lifetime player statistics."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    state INTEGER NOT NULL DEFAULT 1,
                    level INTEGER NOT NULL DEFAULT 1,
                    started_at TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    level_started_at TEXT,
                    username TEXT,
                    display_name TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    timeouts INTEGER NOT NULL DEFAULT 0
                )"""
            )
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(user_progress)")}
            migrations = {
                "level_started_at": "TEXT",
                "username": "TEXT",
                "display_name": "TEXT",
                "attempts": "INTEGER NOT NULL DEFAULT 0",
                "timeouts": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in migrations.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE user_progress ADD COLUMN {name} {definition}")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    display_name TEXT,
                    games_started INTEGER NOT NULL DEFAULT 0,
                    games_completed INTEGER NOT NULL DEFAULT 0,
                    total_attempts INTEGER NOT NULL DEFAULT 0,
                    timeouts INTEGER NOT NULL DEFAULT 0,
                    best_time_seconds INTEGER,
                    updated_at TEXT NOT NULL
                )"""
            )

    def start_game(self, user_id: int, username: str | None, display_name: str) -> None:
        now = utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO user_progress
                   (user_id, state, level, started_at, completed, updated_at, level_started_at,
                    username, display_name, attempts, timeouts)
                   VALUES (?, 1, 1, ?, 0, ?, ?, ?, ?, 0, 0)
                   ON CONFLICT(user_id) DO UPDATE SET
                     state=1, level=1, started_at=excluded.started_at, completed=0,
                     updated_at=excluded.updated_at, level_started_at=excluded.level_started_at,
                     username=excluded.username, display_name=excluded.display_name,
                     attempts=0, timeouts=0""",
                (user_id, now, now, now, username, display_name),
            )
            conn.execute(
                """INSERT INTO player_stats (user_id, username, display_name, games_started, updated_at)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     username=excluded.username, display_name=excluded.display_name,
                     games_started=player_stats.games_started + 1, updated_at=excluded.updated_at""",
                (user_id, username, display_name, now),
            )

    def ensure_player(self, user_id: int, username: str | None, display_name: str) -> dict:
        now = utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO user_progress
                   (user_id, state, level, started_at, completed, updated_at, level_started_at,
                    username, display_name)
                   VALUES (?, 1, 1, ?, 0, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,
                     display_name=excluded.display_name""",
                (user_id, now, now, now, username, display_name),
            )
            conn.execute(
                """INSERT INTO player_stats (user_id, username, display_name, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,
                     display_name=excluded.display_name, updated_at=excluded.updated_at""",
                (user_id, username, display_name, now),
            )
            row = conn.execute("SELECT * FROM user_progress WHERE user_id=?", (user_id,)).fetchone()
            return dict(row)

    def get_progress(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM user_progress WHERE user_id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_remaining_seconds(self, user_id: int, time_limit_seconds: int) -> int:
        progress = self.get_progress(user_id)
        if not progress:
            return time_limit_seconds
        started = progress.get("level_started_at") or progress.get("started_at")
        try:
            start_time = datetime.fromisoformat(started)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            elapsed = (utc_now() - start_time).total_seconds()
            return max(0, time_limit_seconds - int(elapsed))
        except (TypeError, ValueError):
            return time_limit_seconds

    def record_attempt(self, user_id: int, correct: bool) -> None:
        now = utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_progress SET attempts=attempts+1, updated_at=? WHERE user_id=?",
                (now, user_id),
            )
            conn.execute(
                "UPDATE player_stats SET total_attempts=total_attempts+1, updated_at=? WHERE user_id=?",
                (now, user_id),
            )

    def move_to_level(self, user_id: int, level: int) -> None:
        now = utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """UPDATE user_progress SET state=?, level=?, level_started_at=?, updated_at=?
                   WHERE user_id=?""",
                (level, level, now, now, user_id),
            )

    def record_timeout(self, user_id: int) -> None:
        now = utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_progress SET timeouts=timeouts+1, level_started_at=?, updated_at=? WHERE user_id=?",
                (now, now, user_id),
            )
            conn.execute(
                "UPDATE player_stats SET timeouts=timeouts+1, updated_at=? WHERE user_id=?",
                (now, user_id),
            )

    def mark_completed(self, user_id: int) -> int:
        now = utc_now()
        with self._connect() as conn:
            row = conn.execute("SELECT started_at FROM user_progress WHERE user_id=?", (user_id,)).fetchone()
            elapsed = 0
            if row:
                try:
                    started = datetime.fromisoformat(row["started_at"])
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                    elapsed = max(0, int((now - started).total_seconds()))
                except (TypeError, ValueError):
                    pass
            conn.execute(
                "UPDATE user_progress SET completed=1, updated_at=? WHERE user_id=?",
                (now.isoformat(), user_id),
            )
            conn.execute(
                """UPDATE player_stats SET games_completed=games_completed+1,
                   best_time_seconds=CASE WHEN best_time_seconds IS NULL OR best_time_seconds > ?
                     THEN ? ELSE best_time_seconds END, updated_at=? WHERE user_id=?""",
                (elapsed, elapsed, now.isoformat(), user_id),
            )
            return elapsed

    def get_player_stats(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM player_stats WHERE user_id=?", (user_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT display_name, username, games_completed, best_time_seconds
                   FROM player_stats WHERE games_completed > 0
                   ORDER BY best_time_seconds ASC, games_completed DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_remaining_seconds_for_progress(self, progress: dict, time_limit_seconds: int) -> int:
        started = progress.get("level_started_at") or progress.get("started_at")
        try:
            start_time = datetime.fromisoformat(started)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            return max(0, time_limit_seconds - int((utc_now() - start_time).total_seconds()))
        except (TypeError, ValueError):
            return time_limit_seconds
