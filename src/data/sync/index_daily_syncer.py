"""Syncer for index_daily table.

Fetches 3 major indices (上证/深证/创业板) per month.
batch_key format: '{ts_code_short}_{YYYYMM}'
"""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch, months_in_range

logger = logging.getLogger(__name__)

# (ts_code, short_key_prefix)
INDICES = [
    ("000001.SH", "SH"),   # 上证指数
    ("399001.SZ", "SZ"),   # 深证成指
    ("399006.SZ", "CYB"),  # 创业板指
]


class IndexDailySyncer(BaseSyncer):
    TABLE = "index_daily"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        batches = []
        for ms, me in months_in_range(start_date, end_date):
            ym = ms[:6]
            for ts_code, prefix in INDICES:
                batches.append(
                    Batch(
                        key=f"{prefix}_{ym}",
                        params={"ts_code": ts_code, "start_date": ms, "end_date": me},
                    )
                )
        return batches

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        self._rate.acquire()
        df = self._pro.index_daily(
            ts_code=batch.params["ts_code"],
            start_date=batch.params["start_date"],
            end_date=batch.params["end_date"],
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df
