"""Moving Average Calculator — compute and save technical indicators."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.data.mysql_client import MySQLClient

logger = logging.getLogger(__name__)


class MACalculator:
    """计算股票技术指标（移动平均线）并保存到数据库。"""

    def __init__(self, db: MySQLClient) -> None:
        self._db = db

    def _get_earliest_trading_date(
        self,
        start_date: str,
        max_window: int,
    ) -> str:
        """根据 trade_cal，找出 start_date 前的第 (max_window-1) 个交易日。"""
        if max_window <= 1:
            return start_date

        sql = """
            SELECT cal_date FROM trade_cal
            WHERE exchange = 'SSE'
              AND cal_date < :start_date
              AND is_open = 1
            ORDER BY cal_date DESC
            LIMIT :window_minus_one
        """
        rows = self._db.query(
            sql,
            {"start_date": start_date, "window_minus_one": max_window - 1},
        )

        if not rows or len(rows) < max_window - 1:
            return rows[-1]["cal_date"] if rows else start_date

        return rows[-1]["cal_date"]

    def calculate_and_save_moving_averages(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        windows: Optional[list[int]] = None,
    ) -> int:
        """计算股票在指定时间段内的移动平均线，并保存到数据库。

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 目标日期范围的开始，如 '20240101'
            end_date: 目标日期范围的结束，如 '20240331'
            windows: 均线周期列表，默认 [5, 7, 10, 17, 30, 60, 250]

        Returns:
            保存到数据库的行数
        """
        if windows is None:
            windows = [5, 7, 10, 17, 30, 60, 250]

        if not windows:
            return 0

        max_window = max(windows)
        earliest_date = self._get_earliest_trading_date(start_date, max_window)

        sql = """
            SELECT ts_code, trade_date, close
            FROM stock_daily
            WHERE ts_code = :ts_code
              AND trade_date BETWEEN :earliest_date AND :end_date
            ORDER BY trade_date
        """
        rows = self._db.query(
            sql,
            {"ts_code": ts_code, "earliest_date": earliest_date, "end_date": end_date},
        )

        if not rows:
            logger.warning(f"{ts_code}: 在 {earliest_date} 到 {end_date} 无行情数据")
            return 0

        df = pd.DataFrame(rows)
        df["trade_date"] = df["trade_date"].astype(str)
        df = df.sort_values("trade_date").reset_index(drop=True)

        for window in windows:
            df[f"ma{window}"] = df["close"].rolling(
                window=window, min_periods=window
            ).mean()

        df = df[df["trade_date"] >= start_date].copy()

        if df.empty:
            return 0

        cols_to_save = ["ts_code", "trade_date"] + [f"ma{w}" for w in windows]
        df = df[cols_to_save]

        rows_saved = self._db.insert_or_replace("stock_technical_indicators", df)
        logger.info(
            f"{ts_code}: 成功保存 {rows_saved} 条均线记录到 stock_technical_indicators"
        )
        return rows_saved
