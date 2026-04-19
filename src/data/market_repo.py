"""Market data repository — all MySQL query methods for /api/market/* routes."""

from __future__ import annotations

from typing import Optional

from src.data.mysql_client import MySQLClient


class MarketRepo:
    def __init__(self, db: MySQLClient) -> None:
        self._db = db

    def get_stocks(self, market: Optional[str] = None) -> list[dict]:
        if market:
            sql = "SELECT * FROM stock_basic WHERE market = :market ORDER BY ts_code"
            return self._db.query(sql, {"market": market})
        return self._db.query("SELECT * FROM stock_basic ORDER BY ts_code")

    def get_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["ts_code = :ts_code"]
        params: dict = {"ts_code": ts_code}
        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date
        sql = (
            f"SELECT * FROM stock_daily WHERE {' AND '.join(conditions)}"
            " ORDER BY trade_date"
        )
        return self._db.query(sql, params)

    def get_limit_list(
        self,
        trade_date: str,
        limit_type: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["trade_date = :trade_date"]
        params: dict = {"trade_date": trade_date}
        if limit_type:
            conditions.append("limit_type = :limit_type")
            params["limit_type"] = limit_type
        sql = (
            f"SELECT * FROM limit_list_ths WHERE {' AND '.join(conditions)}"
            " ORDER BY limit_amount DESC"
        )
        return self._db.query(sql, params)

    def get_limit_step(self, trade_date: str) -> list[dict]:
        sql = "SELECT * FROM limit_step WHERE trade_date = :d ORDER BY CAST(nums AS UNSIGNED) DESC"
        return self._db.query(sql, {"d": trade_date})

    def get_limit_concept(self, trade_date: str) -> list[dict]:
        sql = "SELECT * FROM limit_cpt_list WHERE trade_date = :d ORDER BY `rank`"
        return self._db.query(sql, {"d": trade_date})

    def get_dc_index(
        self,
        trade_date: str,
        idx_type: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["trade_date = :trade_date"]
        params: dict = {"trade_date": trade_date}
        if idx_type:
            conditions.append("idx_type = :idx_type")
            params["idx_type"] = idx_type
        sql = (
            f"SELECT * FROM dc_index WHERE {' AND '.join(conditions)}"
            " ORDER BY pct_change DESC"
        )
        return self._db.query(sql, params)

    def get_dc_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["ts_code = :ts_code"]
        params: dict = {"ts_code": ts_code}
        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date
        sql = (
            f"SELECT * FROM dc_daily WHERE {' AND '.join(conditions)}"
            " ORDER BY trade_date"
        )
        return self._db.query(sql, params)

    def get_dc_concept(self, trade_date: str) -> list[dict]:
        sql = "SELECT * FROM dc_concept WHERE trade_date = :d ORDER BY `rank`"
        return self._db.query(sql, {"d": trade_date})

    def get_index_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["ts_code = :ts_code"]
        params: dict = {"ts_code": ts_code}
        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date
        sql = (
            f"SELECT * FROM index_daily WHERE {' AND '.join(conditions)}"
            " ORDER BY trade_date"
        )
        return self._db.query(sql, params)

    def get_daily_info(
        self,
        trade_date: str,
        ts_code: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["trade_date = :trade_date"]
        params: dict = {"trade_date": trade_date}
        if ts_code:
            conditions.append("ts_code = :ts_code")
            params["ts_code"] = ts_code
        sql = f"SELECT * FROM daily_info WHERE {' AND '.join(conditions)}"
        return self._db.query(sql, params)

    def get_breadth_stats(self, trade_date: str) -> dict:
        sql = """
            SELECT
                COUNT(*)                                             AS total_stocks,
                SUM(CASE WHEN pct_chg > 0  THEN 1 ELSE 0 END)      AS advance,
                SUM(CASE WHEN pct_chg < 0  THEN 1 ELSE 0 END)      AS decline,
                SUM(CASE WHEN pct_chg = 0  THEN 1 ELSE 0 END)      AS unchanged,
                SUM(CASE WHEN pct_chg >= 9.5 THEN 1 ELSE 0 END)    AS up_limit_approx,
                SUM(amount)                                          AS total_amount,
                SUM(vol)                                             AS total_vol
            FROM stock_daily
            WHERE trade_date = :trade_date
        """
        rows = self._db.query(sql, {"trade_date": trade_date})
        return rows[0] if rows else {}

    def get_dc_index_range(
        self,
        start_date: str,
        end_date: str,
        idx_type: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["trade_date BETWEEN :start_date AND :end_date"]
        params: dict = {"start_date": start_date, "end_date": end_date}
        if idx_type:
            conditions.append("idx_type = :idx_type")
            params["idx_type"] = idx_type
        sql = (
            f"SELECT ts_code, trade_date, idx_type, name, pct_change, `leading`, up_num, down_num"
            f" FROM dc_index WHERE {' AND '.join(conditions)}"
            " ORDER BY trade_date, pct_change DESC"
        )
        return self._db.query(sql, params)

    def get_trade_cal(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
    ) -> list[dict]:
        conditions: list[str] = []
        params: dict = {}
        if start_date:
            conditions.append("cal_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("cal_date <= :end_date")
            params["end_date"] = end_date
        if is_open is not None:
            conditions.append("is_open = :is_open")
            params["is_open"] = is_open
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM trade_cal {where} ORDER BY cal_date"
        return self._db.query(sql, params)

    def get_technical_indicators(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["ts_code = :ts_code"]
        params: dict = {"ts_code": ts_code}
        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date
        sql = (
            f"SELECT * FROM stock_technical_indicators WHERE {' AND '.join(conditions)}"
            " ORDER BY trade_date"
        )
        return self._db.query(sql, params)

    def get_daily_with_ma(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        conditions = ["sd.ts_code = :ts_code"]
        params: dict = {"ts_code": ts_code}
        if start_date:
            conditions.append("sd.trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("sd.trade_date <= :end_date")
            params["end_date"] = end_date
        sql = (
            f"SELECT sd.ts_code, sd.trade_date, sd.close, sd.open, sd.high, sd.low, sd.vol, sd.amount,"
            f" sti.ma5, sti.ma7, sti.ma10, sti.ma17, sti.ma30, sti.ma60, sti.ma250"
            f" FROM stock_daily sd"
            f" LEFT JOIN stock_technical_indicators sti ON sd.ts_code = sti.ts_code AND sd.trade_date = sti.trade_date"
            f" WHERE {' AND '.join(conditions)}"
            f" ORDER BY sd.trade_date"
        )
        return self._db.query(sql, params)
