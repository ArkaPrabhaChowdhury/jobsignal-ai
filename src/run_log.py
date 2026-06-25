from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.config import get_settings
from src.models import RunLog


class RunLogStore:
    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path or settings.run_log_db)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_logs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    fetched INTEGER NOT NULL,
                    stored INTEGER NOT NULL,
                    skipped_dedup INTEGER NOT NULL,
                    skipped_low_confidence INTEGER NOT NULL,
                    errors TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def write(self, run_log: RunLog) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO run_logs
                (run_id, started_at, source, fetched, stored, skipped_dedup,
                 skipped_low_confidence, errors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_log.run_id,
                    run_log.started_at.isoformat(),
                    run_log.source,
                    run_log.fetched,
                    run_log.stored,
                    run_log.skipped_dedup,
                    run_log.skipped_low_confidence,
                    json.dumps(run_log.errors),
                ),
            )
            conn.commit()

    def last_runs(self, limit: int = 5) -> list[RunLog]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, started_at, source, fetched, stored,
                       skipped_dedup, skipped_low_confidence, errors
                FROM run_logs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            RunLog(
                run_id=row[0],
                started_at=row[1],
                source=row[2],
                fetched=row[3],
                stored=row[4],
                skipped_dedup=row[5],
                skipped_low_confidence=row[6],
                errors=json.loads(row[7]),
            )
            for row in rows
        ]
