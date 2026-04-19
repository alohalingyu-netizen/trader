"""HTTP client for /api/market/* endpoints."""

from __future__ import annotations

from typing import Optional

import requests


class MarketApiClient:
    """Thin wrapper around the /api/market/* REST endpoints backed by MySQL."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    _NO_PROXY = {"http": None, "https": None}

    def _get(self, path: str, params: dict | None = None) -> list[dict]:
        resp = requests.get(
            f"{self._base}{path}",
            params={k: v for k, v in (params or {}).items() if v is not None},
            timeout=self._timeout,
            proxies=self._NO_PROXY,
        )
        resp.raise_for_status()
        return resp.json()

    def get_stocks(self, market: Optional[str] = None) -> list[dict]:
        return self._get("/api/market/stocks", {"market": market})

    def get_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        return self._get(
            f"/api/market/daily/{ts_code}",
            {"start_date": start_date, "end_date": end_date},
        )

    def get_limit_list(
        self, trade_date: str, limit_type: Optional[str] = None
    ) -> list[dict]:
        return self._get(
            "/api/market/limit-list",
            {"trade_date": trade_date, "limit_type": limit_type},
        )

    def get_limit_step(self, trade_date: str) -> list[dict]:
        return self._get("/api/market/limit-step", {"trade_date": trade_date})

    def get_limit_concept(self, trade_date: str) -> list[dict]:
        return self._get("/api/market/limit-concept", {"trade_date": trade_date})

    def get_dc_index(
        self, trade_date: str, idx_type: Optional[str] = None
    ) -> list[dict]:
        return self._get(
            "/api/market/dc-index",
            {"trade_date": trade_date, "idx_type": idx_type},
        )

    def get_dc_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        return self._get(
            f"/api/market/dc-daily/{ts_code}",
            {"start_date": start_date, "end_date": end_date},
        )

    def get_dc_concept(self, trade_date: str) -> list[dict]:
        return self._get("/api/market/dc-concept", {"trade_date": trade_date})

    def get_index_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        return self._get(
            f"/api/market/index-daily/{ts_code}",
            {"start_date": start_date, "end_date": end_date},
        )

    def get_daily_info(
        self, trade_date: str, ts_code: Optional[str] = None
    ) -> list[dict]:
        return self._get(
            "/api/market/daily-info",
            {"trade_date": trade_date, "ts_code": ts_code},
        )

    def get_breadth_stats(self, trade_date: str) -> dict:
        resp = requests.get(
            f"{self._base}/api/market/breadth-stats",
            params={"trade_date": trade_date},
            timeout=self._timeout,
            proxies=self._NO_PROXY,
        )
        resp.raise_for_status()
        return resp.json() or {}

    def get_dc_index_range(
        self,
        start_date: str,
        end_date: str,
        idx_type: Optional[str] = None,
    ) -> list[dict]:
        return self._get(
            "/api/market/dc-index-range",
            {"start_date": start_date, "end_date": end_date, "idx_type": idx_type},
        )

    def get_trade_cal(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
    ) -> list[dict]:
        return self._get(
            "/api/market/trade-cal",
            {"start_date": start_date, "end_date": end_date, "is_open": is_open},
        )

    def get_technical_indicators(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        return self._get(
            f"/api/market/technical-indicators/{ts_code}",
            {"start_date": start_date, "end_date": end_date},
        )

    def get_daily_with_ma(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        return self._get(
            f"/api/market/daily-with-ma/{ts_code}",
            {"start_date": start_date, "end_date": end_date},
        )
