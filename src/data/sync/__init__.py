"""Sync package — exports SYNCER_MAP for CLI dispatch."""

from src.data.sync.dc_concept_syncer import DcConceptSyncer
from src.data.sync.dc_daily_syncer import DcDailySyncer
from src.data.sync.dc_index_syncer import DcIndexSyncer
from src.data.sync.daily_info_syncer import DailyInfoSyncer
from src.data.sync.index_daily_syncer import IndexDailySyncer
from src.data.sync.limit_cpt_syncer import LimitCptSyncer
from src.data.sync.limit_list_syncer import LimitListSyncer
from src.data.sync.limit_step_syncer import LimitStepSyncer
from src.data.sync.stock_basic_syncer import StockBasicSyncer
from src.data.sync.stock_daily_syncer import StockDailySyncer
from src.data.sync.trade_cal_syncer import TradeCalSyncer

# Table name → syncer class, ordered for full sync (dependencies first)
SYNCER_MAP: dict = {
    "stock_basic":    StockBasicSyncer,
    "trade_cal":      TradeCalSyncer,
    "stock_daily":    StockDailySyncer,
    "limit_list_ths": LimitListSyncer,
    "limit_step":     LimitStepSyncer,
    "limit_cpt_list": LimitCptSyncer,
    "dc_index":       DcIndexSyncer,
    "dc_daily":       DcDailySyncer,
    "dc_concept":     DcConceptSyncer,
    "index_daily":    IndexDailySyncer,
    "daily_info":     DailyInfoSyncer,
}

__all__ = [
    "SYNCER_MAP",
    "StockBasicSyncer",
    "TradeCalSyncer",
    "StockDailySyncer",
    "LimitListSyncer",
    "LimitStepSyncer",
    "LimitCptSyncer",
    "DcIndexSyncer",
    "DcDailySyncer",
    "DcConceptSyncer",
    "IndexDailySyncer",
    "DailyInfoSyncer",
]
