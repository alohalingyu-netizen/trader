"""Syncer for stock_daily table.

Per-day batches (batch_key = YYYYMMDD), multi-threaded fetch with max 10 workers.
Each day calls daily(trade_date) + daily_basic(trade_date) for the full market.
Non-trading days return empty DataFrames and are recorded as done with 0 rows.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch

logger = logging.getLogger(__name__)

MAX_WORKERS = 10
_BASIC_DROP = {"ts_code", "trade_date", "close"}


def _all_days(start_date: str, end_date: str) -> list[str]:
    """Return every calendar day in [start_date, end_date] as YYYYMMDD strings."""
    start = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
    end = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
    days = []
    cur = start
    while cur <= end:
        days.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return days


class StockDailySyncer(BaseSyncer):
    TABLE = "stock_daily"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        return [
            Batch(key=d, params={"trade_date": d})
            for d in _all_days(start_date, end_date)
        ]

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        trade_date = batch.params["trade_date"]

        self._rate.acquire()
        daily_df = self._pro.daily(trade_date=trade_date)

        self._rate.acquire()
        basic_df = self._pro.daily_basic(trade_date=trade_date)

        if daily_df is None or daily_df.empty:
            return pd.DataFrame()

        if basic_df is not None and not basic_df.empty:
            keep_cols = ["ts_code", "trade_date"] + [
                c for c in basic_df.columns if c not in _BASIC_DROP
            ]
            basic_df = basic_df[keep_cols]
            merged = daily_df.merge(basic_df, on=["ts_code", "trade_date"], how="left")
        else:
            merged = daily_df.copy()

        return merged

    def sync(self, start_date: str, end_date: str, force: bool = False) -> None:
        table = self.TABLE
        batches = self.generate_batches(start_date, end_date)

        pending = [
            b for b in batches
            if force or not self._db.is_done(table, b.key)
        ]
        skipped = len(batches) - len(pending)
        logger.info(
            "[%s] %d days total, %d pending, %d skipped",
            table, len(batches), len(pending), skipped,
        )

        def _process(batch: Batch) -> tuple[str, int]:
            self._db.upsert_log(table, batch.key, status="pending")
            try:
                df = self.fetch_batch(batch)
                rows = self._db.insert_ignore(table, df)
                self._db.upsert_log(table, batch.key, status="done", rows_written=rows)
                if rows > 0:
                    logger.info("[%s] %s → %d rows", table, batch.key, rows)
                return batch.key, rows
            except Exception as exc:
                self._db.upsert_log(table, batch.key, status="error", error_msg=str(exc))
                logger.error("[%s] %s error: %s", table, batch.key, exc)
                raise

        errors: list[Exception] = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process, b): b for b in pending}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    errors.append(exc)

        if errors:
            raise errors[0]
