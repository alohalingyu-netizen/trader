"""Syncer for trade_cal table.

Fetches trading calendar for both SSE and SZSE in a single batch.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch

logger = logging.getLogger(__name__)

EXCHANGES = ["SSE", "SZSE"]
CAL_START = "20240101"
CAL_END = "20270101"


class TradeCalSyncer(BaseSyncer):
    TABLE = "trade_cal"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        return [Batch(key="full", params={"start_date": CAL_START, "end_date": CAL_END})]

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        frames = []
        for exchange in EXCHANGES:
            self._rate.acquire()
            df = self._pro.trade_cal(
                exchange=exchange,
                start_date=batch.params["start_date"],
                end_date=batch.params["end_date"],
            )
            if df is not None and not df.empty:
                frames.append(df)

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)
