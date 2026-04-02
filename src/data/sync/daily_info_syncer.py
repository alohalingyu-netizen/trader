"""Syncer for daily_info table (沪深市场每日交易统计).

Batches by (market_type × year).
batch_key format: '{market}_{YYYY}'
"""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch, years_in_range

logger = logging.getLogger(__name__)

MARKETS = ["SH_MARKET", "SZ_MARKET", "SZ_GEM", "SZ_SME", "SH_STAR"]


class DailyInfoSyncer(BaseSyncer):
    TABLE = "daily_info"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        batches = []
        for market in MARKETS:
            for year, year_start, year_end in years_in_range(start_date, end_date):
                batches.append(
                    Batch(
                        key=f"{market}_{year}",
                        params={"ts_code": market, "start_date": year_start, "end_date": year_end},
                    )
                )
        return batches

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        self._rate.acquire()
        df = self._pro.daily_info(
            ts_code=batch.params["ts_code"],
            start_date=batch.params["start_date"],
            end_date=batch.params["end_date"],
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df
