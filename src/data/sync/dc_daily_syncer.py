"""Syncer for dc_daily table (东财指数日线行情). Monthly batches."""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch, months_in_range

logger = logging.getLogger(__name__)


class DcDailySyncer(BaseSyncer):
    TABLE = "dc_daily"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        return [
            Batch(key=ms[:6], params={"start_date": ms, "end_date": me})
            for ms, me in months_in_range(start_date, end_date)
        ]

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        self._rate.acquire()
        df = self._pro.dc_daily(
            start_date=batch.params["start_date"],
            end_date=batch.params["end_date"],
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df
