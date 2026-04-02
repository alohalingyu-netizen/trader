"""MySQL client — connection pool, bulk INSERT IGNORE, sync_log helpers."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import MySQLConfig

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class MySQLClient:
    def __init__(self, config: MySQLConfig) -> None:
        url = (
            f"mysql+pymysql://{config.user}:{config.password}"
            f"@{config.host}:{config.port}/{config.database}"
            "?charset=utf8mb4"
        )
        self._engine: Engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Execute schema.sql to create all tables (IF NOT EXISTS, idempotent)."""
        raw = _SCHEMA_PATH.read_text(encoding="utf-8")
        # Strip SQL line comments before splitting on semicolons
        stripped = re.sub(r"--[^\n]*", "", raw)
        statements = [s.strip() for s in stripped.split(";") if s.strip()]
        with self._engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
        logger.info("MySQL schema initialized.")

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def insert_ignore(self, table: str, df: pd.DataFrame, batch_size: int = 2000) -> int:
        """Bulk INSERT IGNORE into *table* from DataFrame. Returns rows written."""
        if df.empty:
            return 0

        cols = ", ".join(f"`{c}`" for c in df.columns)
        placeholders = ", ".join(f":{c}" for c in df.columns)
        sql = f"INSERT IGNORE INTO `{table}` ({cols}) VALUES ({placeholders})"

        # NaN / NaT → None so PyMySQL sends NULL
        import math
        import numpy as np

        records = df.replace({np.nan: None}).to_dict("records")
        for rec in records:
            for k, v in rec.items():
                if isinstance(v, float) and math.isnan(v):
                    rec[k] = None
        total = 0
        with self._engine.begin() as conn:
            for i in range(0, len(records), batch_size):
                chunk = records[i : i + batch_size]
                result = conn.execute(text(sql), chunk)
                total += result.rowcount
        return total

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def query(self, sql: str, params: Optional[dict] = None) -> list[dict]:
        """Execute a SELECT query and return rows as a list of dicts."""
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            keys = list(result.keys())
            return [dict(zip(keys, row)) for row in result.fetchall()]

    # ------------------------------------------------------------------
    # sync_log helpers
    # ------------------------------------------------------------------

    def is_done(self, table_name: str, batch_key: str) -> bool:
        """Return True if the batch is recorded as 'done' in sync_log."""
        sql = "SELECT status FROM sync_log WHERE table_name = :t AND batch_key = :k"
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"t": table_name, "k": batch_key}).fetchone()
        return row is not None and row[0] == "done"

    def upsert_log(
        self,
        table_name: str,
        batch_key: str,
        status: str,
        rows_written: Optional[int] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        """Insert or update a sync_log row for the given (table, batch_key)."""
        now = datetime.now()

        if status == "pending":
            sql = """
                INSERT INTO sync_log (table_name, batch_key, status, started_at)
                VALUES (:t, :k, 'pending', :now)
                ON DUPLICATE KEY UPDATE
                    status = 'pending',
                    started_at = :now,
                    finished_at = NULL,
                    error_msg = NULL
            """
            params: dict = {"t": table_name, "k": batch_key, "now": now}

        elif status == "done":
            sql = """
                INSERT INTO sync_log (table_name, batch_key, status, rows_written, finished_at)
                VALUES (:t, :k, 'done', :r, :now)
                ON DUPLICATE KEY UPDATE
                    status = 'done',
                    rows_written = :r,
                    finished_at = :now,
                    error_msg = NULL
            """
            params = {"t": table_name, "k": batch_key, "r": rows_written, "now": now}

        else:  # error
            sql = """
                INSERT INTO sync_log (table_name, batch_key, status, error_msg, finished_at)
                VALUES (:t, :k, 'error', :e, :now)
                ON DUPLICATE KEY UPDATE
                    status = 'error',
                    error_msg = :e,
                    finished_at = :now
            """
            params = {"t": table_name, "k": batch_key, "e": error_msg, "now": now}

        with self._engine.begin() as conn:
            conn.execute(text(sql), params)
