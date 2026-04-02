"""Syncer for dc_index table (东财板块指数).

Fetches 3 idx_type values per month batch.
batch_key format: '{I|C|G}_{YYYYMM}'
  I = 行业板块, C = 概念板块, G = 地域板块
"""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch, months_in_range

logger = logging.getLogger(__name__)

IDX_TYPES = [
    ("I", "行业板块"),
    ("C", "概念板块"),
    ("G", "地域板块"),
]


class DcIndexSyncer(BaseSyncer):
    TABLE = "dc_index"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        batches = []
        for ms, me in months_in_range(start_date, end_date):
            ym = ms[:6]
            for prefix, idx_type in IDX_TYPES:
                batches.append(
                    Batch(
                        key=f"{prefix}_{ym}",
                        params={"start_date": ms, "end_date": me, "idx_type": idx_type},
                    )
                )
        return batches

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        self._rate.acquire()
        df = self._pro.dc_index(
            start_date=batch.params["start_date"],
            end_date=batch.params["end_date"],
            idx_type=batch.params["idx_type"],
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df
