import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class UserProgressRepository:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    state INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def set_progress(self, user_id: int, state: int, level: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_progress (user_id, state, level, started_at, completed, updated_at)
                VALUES (?, ?, ?, ?, 0, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET state = excluded.state,
                              level = excluded.level,
                              updated_at = excluded.updated_at,
                              started_at = COALESCE(user_progress.started_at, excluded.started_at)
                """,
                (user_id, state, level, now, now),
            )

    def reset_progress(self, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_progress (user_id, state, level, started_at, completed, updated_at)
                VALUES (?, 1, 1, ?, 0, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET state = excluded.state,
                              level = excluded.level,
                              started_at = excluded.started_at,
                              completed = excluded.completed,
                              updated_at = excluded.updated_at
                """,
                (user_id, now, now),
            )

    def get_progress(self, user_id: int):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, state, level, started_at, completed, updated_at FROM user_progress WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def mark_completed(self, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_progress SET completed = 1, updated_at = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_remaining_seconds(self, user_id: int, total_seconds: int = 30) -> int:
        row = self.get_progress(user_id)
        if not row:
            return total_seconds
        started_at = row.get("started_at")
        if not started_at:
            return total_seconds
        try:
            created = datetime.fromisoformat(started_at)
            now = datetime.now(timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            delta = (now - created).total_seconds()
            return max(0, total_seconds - int(delta))
        except ValueError:
            return total_seconds
