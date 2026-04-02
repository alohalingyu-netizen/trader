"""Syncer for limit_list_ths table (同花顺涨跌停榜单).

5 limit_type values × monthly batches.
batch_key format: '{TYPE_PREFIX}_{YYYYMM}'
  ZT=涨停池, LB=连扳池, CS=冲刺涨停, ZB=炸板池, DT=跌停池
"""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch, months_in_range

logger = logging.getLogger(__name__)

LIMIT_TYPES = [
    ("ZT", "涨停池"),
    ("LB", "连扳池"),
    ("CS", "冲刺涨停"),
    ("ZB", "炸板池"),
    ("DT", "跌停池"),
]


class LimitListSyncer(BaseSyncer):
    TABLE = "limit_list_ths"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        batches = []
        for ms, me in months_in_range(start_date, end_date):
            ym = ms[:6]
            for prefix, limit_type in LIMIT_TYPES:
                batches.append(
                    Batch(
                        key=f"{prefix}_{ym}",
                        params={"start_date": ms, "end_date": me, "limit_type": limit_type},
                    )
                )
        return batches

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        self._rate.acquire()
        df = self._pro.limit_list_ths(
            start_date=batch.params["start_date"],
            end_date=batch.params["end_date"],
            limit_type=batch.params["limit_type"],
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df
