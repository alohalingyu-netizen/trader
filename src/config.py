"""Configuration management for Evolving Trader.

Loads settings from a YAML file with environment variable overrides.
API keys MUST come from environment variables, never from the YAML file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ConfigValidationError(ValueError):
    """Raised when required configuration fields are missing or invalid."""


class AgentConfig(BaseModel):
    model: str = "deepseek/deepseek-chat"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LLMConfig(BaseModel):
    model: str = "deepseek/deepseek-chat"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class TushareConfig(BaseModel):
    token: str
    cache_db: str = "data/cache.db"
    rate_limit_per_min: int = Field(default=200, gt=0)


class MySQLConfig(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "evolving_trader"


class RiskConfig(BaseModel):
    max_position_pct: float = Field(default=0.30, gt=0.0, le=1.0)
    max_drawdown_pct: float = Field(default=0.15, gt=0.0, le=1.0)
    stop_loss_pct: float = Field(default=0.08, gt=0.0, le=1.0)
    take_profit_pct: float = Field(default=0.20, gt=0.0, le=1.0)
    max_open_positions: int = Field(default=5, gt=0)


class NotificationConfig(BaseModel):
    enabled: bool = False


class StockPoolConfig(BaseModel):
    mode: str = Field(default="index", description="index or custom")
    index_codes: List[str] = Field(
        default_factory=lambda: ["000300.SH", "000905.SH"],
        description="Index codes for index mode",
    )
    custom_list: List[str] = Field(
        default_factory=list,
        description="Custom stock list for custom mode",
    )


class Config(BaseModel):
    llm: LLMConfig
    tushare: TushareConfig
    risk: RiskConfig
    mysql: MySQLConfig = Field(default_factory=MySQLConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    stock_pool: StockPoolConfig = Field(default_factory=StockPoolConfig)
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _apply_env_overrides(cls, values: dict) -> dict:
        """Apply environment variable overrides to raw config dict."""
        # LLM overrides
        llm = values.setdefault("llm", {})
        if v := os.environ.get("EVOLVING_TRADER_LLM_MODEL"):
            llm["model"] = v
        if v := os.environ.get("EVOLVING_TRADER_LLM_TEMPERATURE"):
            llm["temperature"] = float(v)
        if v := os.environ.get("EVOLVING_TRADER_LLM_MAX_TOKENS"):
            llm["max_tokens"] = int(v)
        # API keys: pick up from standard env vars per provider
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
            if v := os.environ.get(key):
                llm.setdefault("api_key", v)
                break

        # Tushare token — MUST come from env var
        tushare = values.setdefault("tushare", {})
        if v := os.environ.get("TUSHARE_TOKEN"):
            tushare["token"] = v

        # MySQL — env vars override yaml
        mysql = values.setdefault("mysql", {})
        if v := os.environ.get("MYSQL_HOST"):
            mysql["host"] = v
        if v := os.environ.get("MYSQL_PORT"):
            mysql["port"] = int(v)
        if v := os.environ.get("MYSQL_USER"):
            mysql["user"] = v
        if v := os.environ.get("MYSQL_PASSWORD"):
            mysql["password"] = v
        if v := os.environ.get("MYSQL_DATABASE"):
            mysql["database"] = v

        return values

    @classmethod
    def load(cls, path: str) -> "Config":
        """Load configuration from a YAML file, applying env var overrides."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path.resolve()}"
            )

        with config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Expand agents with fallback to global llm defaults
        global_llm = raw.get("llm", {})
        agents_raw = raw.get("agents", {})
        for agent_name, agent_cfg in agents_raw.items():
            for key in ("model", "temperature", "max_tokens"):
                if key not in agent_cfg or agent_cfg[key] is None:
                    agent_cfg[key] = global_llm.get(key)
        raw["agents"] = agents_raw

        try:
            return cls.model_validate(raw)
        except Exception as exc:
            # Wrap pydantic errors to provide a clearer message
            missing = []
            if "tushare" in str(exc) and "token" in str(exc):
                missing.append("TUSHARE_TOKEN (set env var)")
            if missing:
                raise ConfigValidationError(
                    f"Missing required configuration fields: {', '.join(missing)}"
                ) from exc
            raise
