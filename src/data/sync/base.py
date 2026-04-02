"""Base syncer — template method pattern for all table syncers."""

from __future__ import annotations

import calendar
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from src.data.mysql_client import MySQLClient
from src.data.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "20240101"


@dataclass
class Batch:
    key: str           # sync_log batch_key
    params: dict = field(default_factory=dict)  # kwargs forwarded to Tushare API


def months_in_range(start_date: str, end_date: str) -> list[tuple[str, str]]:
    """Return (month_start_YYYYMMDD, month_end_YYYYMMDD) for each calendar month
    that overlaps with [start_date, end_date]."""
    start = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
    end = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))

    result: list[tuple[str, str]] = []
    year, month = start.year, start.month

    while True:
        last_day = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        actual_start = max(month_start, start)
        actual_end = min(month_end, end)

        if actual_start <= actual_end:
            result.append((actual_start.strftime("%Y%m%d"), actual_end.strftime("%Y%m%d")))

        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

        if date(year, month, 1) > end:
            break

    return result


def years_in_range(start_date: str, end_date: str) -> list[tuple[int, str, str]]:
    """Return (year, year_start_YYYYMMDD, year_end_YYYYMMDD) for each year
    that overlaps with [start_date, end_date]."""
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    result = []
    for year in range(start_year, end_year + 1):
        year_start = max(start_date, f"{year}0101")
        year_end = min(end_date, f"{year}1231")
        result.append((year, year_start, year_end))
    return result


class BaseSyncer(ABC):
    TABLE: str = ""

    def __init__(self, pro_api, db: MySQLClient, rate_limiter: RateLimiter) -> None:
        self._pro = pro_api
        self._db = db
        self._rate = rate_limiter

    @abstractmethod
    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        """Return the list of batches to process for the given date range."""

    @abstractmethod
    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        """Fetch data from Tushare for a single batch. Must call self._rate.acquire()
        before each Tushare API call."""

    def sync(self, start_date: str, end_date: str, force: bool = False) -> None:
        """Run sync for all batches in [start_date, end_date].

        Batches already marked 'done' in sync_log are skipped unless force=True.
        """
        table = self.TABLE
        batches = self.generate_batches(start_date, end_date)
        logger.info("[%s] %d batches to process (%s ~ %s)", table, len(batches), start_date, end_date)

        for batch in batches:
            if not force and self._db.is_done(table, batch.key):
                logger.info("[%s] skip %s (already done)", table, batch.key)
                continue

            self._db.upsert_log(table, batch.key, status="pending")
            try:
                df = self.fetch_batch(batch)
                rows = self._db.insert_ignore(table, df)
                self._db.upsert_log(table, batch.key, status="done", rows_written=rows)
                logger.info("[%s] %s → %d rows written", table, batch.key, rows)
            except Exception as exc:
                self._db.upsert_log(table, batch.key, status="error", error_msg=str(exc))
                logger.error("[%s] %s error: %s", table, batch.key, exc)
                raise
