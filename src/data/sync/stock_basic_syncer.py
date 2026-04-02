"""Syncer for stock_basic table.

Merges stock_basic (3 markets) with stock_company (main_business, business_scope).
Treated as a single batch — batch_key = 'full'.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.data.sync.base import BaseSyncer, Batch

logger = logging.getLogger(__name__)

MARKETS = ["主板", "创业板", "科创板"]
COMPANY_CHUNK = 100  # ts_codes per stock_company call


class StockBasicSyncer(BaseSyncer):
    TABLE = "stock_basic"

    def generate_batches(self, start_date: str, end_date: str) -> list[Batch]:
        return [Batch(key="full", params={})]

    def fetch_batch(self, batch: Batch) -> pd.DataFrame:
        # 1. Fetch stock_basic for each market
        frames = []
        for market in MARKETS:
            self._rate.acquire()
            df = self._pro.stock_basic(market=market, list_status="L")
            if df is not None and not df.empty:
                frames.append(df)

        if not frames:
            return pd.DataFrame()

        basic_df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts_code"])

        # 2. Fetch stock_company in chunks of COMPANY_CHUNK
        ts_codes = basic_df["ts_code"].tolist()
        company_frames = []
        for i in range(0, len(ts_codes), COMPANY_CHUNK):
            chunk = ts_codes[i : i + COMPANY_CHUNK]
            self._rate.acquire()
            cdf = self._pro.stock_company(
                ts_code=",".join(chunk),
                fields="ts_code,main_business,business_scope",
            )
            if cdf is not None and not cdf.empty:
                company_frames.append(cdf)

        # 3. Left-join company info onto basic
        if company_frames:
            company_df = pd.concat(company_frames, ignore_index=True).drop_duplicates(
                subset=["ts_code"]
            )
            merged = basic_df.merge(company_df, on="ts_code", how="left")
        else:
            merged = basic_df.copy()
            merged["main_business"] = None
            merged["business_scope"] = None

        return merged
