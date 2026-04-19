"""Configuration management for Evolving Trader.

Loads settings from a YAML file with environment variable overrides.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class ConfigValidationError(ValueError):
    """Raised when required configuration fields are missing or invalid."""


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


class Config(BaseModel):
    tushare: TushareConfig
    mysql: MySQLConfig = Field(default_factory=MySQLConfig)

    @model_validator(mode="before")
    @classmethod
    def _apply_env_overrides(cls, values: dict) -> dict:
        """Apply environment variable overrides to raw config dict."""
        # Tushare token
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

        try:
            return cls.model_validate(raw)
        except Exception as exc:
            missing = []
            if "tushare" in str(exc) and "token" in str(exc):
                missing.append("TUSHARE_TOKEN (set env var)")
            if missing:
                raise ConfigValidationError(
                    f"Missing required configuration fields: {', '.join(missing)}"
                ) from exc
            raise
