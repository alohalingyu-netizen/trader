"""Market data API routes — /api/market/*

All endpoints read from MySQL via MarketRepo.
MySQL connection is lazily initialized from app config on first request.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/market", tags=["market"])

_repo = None  # lazy singleton
_calc = None  # lazy singleton for MACalculator


def _get_repo():
    global _repo
    if _repo is None:
        try:
            from src.config import Config
            from src.data.mysql_client import MySQLClient
            from src.data.market_repo import MarketRepo

            config = Config.load("config/settings.yaml")
            _repo = MarketRepo(MySQLClient(config.mysql))
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"MySQL unavailable: {exc}")
    return _repo


def _get_calc():
    global _calc
    if _calc is None:
        try:
            from src.config import Config
            from src.data.mysql_client import MySQLClient
            from src.data.ma_calculator import MACalculator

            config = Config.load("config/settings.yaml")
            _calc = MACalculator(MySQLClient(config.mysql))
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"MySQL unavailable: {exc}")
    return _calc


@router.get("/stocks")
def get_stocks(market: Optional[str] = None) -> list[dict[str, Any]]:
    """List stocks. Optional ?market= filter (主板/创业板/科创板)."""
    return _get_repo().get_stocks(market=market)


@router.get("/daily/{ts_code}")
def get_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Daily OHLCV + fundamentals for a stock."""
    return _get_repo().get_daily(ts_code, start_date=start_date, end_date=end_date)


@router.get("/limit-list")
def get_limit_list(
    trade_date: str,
    limit_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """涨跌停榜单 for a trading date."""
    return _get_repo().get_limit_list(trade_date, limit_type=limit_type)


@router.get("/limit-step")
def get_limit_step(trade_date: str) -> list[dict[str, Any]]:
    """连板天梯 for a trading date."""
    return _get_repo().get_limit_step(trade_date)


@router.get("/limit-concept")
def get_limit_concept(trade_date: str) -> list[dict[str, Any]]:
    """涨停最强板块 for a trading date."""
    return _get_repo().get_limit_concept(trade_date)


@router.get("/dc-index")
def get_dc_index(
    trade_date: str,
    idx_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """东财板块指数. ?idx_type=行业板块|概念板块|地域板块"""
    return _get_repo().get_dc_index(trade_date, idx_type=idx_type)


@router.get("/dc-daily/{ts_code}")
def get_dc_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    """东财指数日线行情."""
    return _get_repo().get_dc_daily(ts_code, start_date=start_date, end_date=end_date)


@router.get("/dc-concept")
def get_dc_concept(trade_date: str) -> list[dict[str, Any]]:
    """东财概念题材快照."""
    return _get_repo().get_dc_concept(trade_date)


@router.get("/index-daily/{ts_code}")
def get_index_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Major index daily data (上证/深证/创业板)."""
    return _get_repo().get_index_daily(ts_code, start_date=start_date, end_date=end_date)


@router.get("/daily-info")
def get_daily_info(
    trade_date: str,
    ts_code: Optional[str] = None,
) -> list[dict[str, Any]]:
    """沪深市场每日交易统计."""
    return _get_repo().get_daily_info(trade_date, ts_code=ts_code)


@router.get("/breadth-stats")
def get_breadth_stats(trade_date: str) -> dict[str, Any]:
    """全市场涨跌家数 + 成交量聚合."""
    return _get_repo().get_breadth_stats(trade_date)


@router.get("/dc-index-range")
def get_dc_index_range(
    start_date: str,
    end_date: str,
    idx_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """板块近N日涨跌幅."""
    return _get_repo().get_dc_index_range(start_date, end_date, idx_type=idx_type)


@router.get("/trade-cal")
def get_trade_cal(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_open: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Trading calendar. Optional ?is_open=0|1 filter."""
    return _get_repo().get_trade_cal(start_date=start_date, end_date=end_date, is_open=is_open)


@router.post("/calculate-ma")
def calculate_ma(
    ts_code: str,
    start_date: str,
    end_date: str,
    windows: Optional[list[int]] = None,
) -> dict[str, Any]:
    """Calculate and save moving averages for a stock.

    Args:
        ts_code: 股票代码，如 '000001.SZ'
        start_date: 目标日期范围开始，如 '20240301'
        end_date: 目标日期范围结束，如 '20240331'
        windows: 均线周期列表，默认 [5, 7, 10, 17, 30, 60, 250]
    """
    if windows is None:
        windows = [5, 7, 10, 17, 30, 60, 250]

    rows_saved = _get_calc().calculate_and_save_moving_averages(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        windows=windows,
    )
    return {"rows_saved": rows_saved}


@router.get("/technical-indicators/{ts_code}")
def get_technical_indicators(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Query technical indicators (MA5/7/10/17/30/60/250) for a stock."""
    return _get_repo().get_technical_indicators(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/daily-with-ma/{ts_code}")
def get_daily_with_ma(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Query daily OHLCV data with moving averages (MA5/7/10/17/30/60/250)."""
    return _get_repo().get_daily_with_ma(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )
