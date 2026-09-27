"""Settings loader — env vars, YAML overlay, defaults."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from viber_broadcast.bootstrap import default_config_dir


class Settings(BaseModel):
    """Runtime configuration. Loaded once at bootstrap and frozen."""

    adapter: str = "viber-desktop"
    desktop_handle_path: Path = Field(
        default_factory=lambda: Path(r"\\.\pipe\viber_desktop_bridge")
    )
    request_timeout_s: float = 20.0

    accounts_file: Path = Field(default_factory=lambda: default_config_dir() / "accounts.json")
    templates_dir: Path = Field(default_factory=lambda: default_config_dir() / "templates")
    sent_db: Path = Field(default_factory=lambda: default_config_dir() / "sent.db")
    log_dir: Path = Field(default_factory=lambda: default_config_dir() / "logs")
    log_level: str = "INFO"

    min_delay_s: float = 4.0
    max_delay_s: float = 11.0
    burst_window_s: float = 60.0
    burst_cap: int = 12
    max_retries: int = 3

    @field_validator("log_level")
    @classmethod
    def _upper_level(cls, v: str) -> str:
        return v.upper()

    @field_validator("max_delay_s")
    @classmethod
    def _delay_order(cls, v: float, info) -> float:
        mn = info.data.get("min_delay_s", 0.0)
        if v < mn:
            raise ValueError("max_delay_s must be >= min_delay_s")
        return v


def _config_path() -> Path:
    override = os.getenv("VIBER_BROADCAST_CONFIG")
    if override:
        return Path(override)
    return default_config_dir() / "config.yaml"


def load_settings() -> Settings:
    """Load settings: .env → YAML → env overrides → defaults."""
    load_dotenv()
    cfg_file = _config_path()
    raw: dict[str, object] = {}
    if cfg_file.exists():
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}

    env_map = {
        "VIBER_ADAPTER": "adapter",
        "VIBER_ACCOUNTS_FILE": "accounts_file",
        "VIBER_TEMPLATES_DIR": "templates_dir",
        "VIBER_SENT_DB": "sent_db",
        "VIBER_LOG_DIR": "log_dir",
        "VIBER_LOG_LEVEL": "log_level",
        "VIBER_MIN_DELAY_S": "min_delay_s",
        "VIBER_MAX_DELAY_S": "max_delay_s",
        "VIBER_MAX_RETRIES": "max_retries",
    }
    for env_key, field in env_map.items():
        if (val := os.getenv(env_key)) is not None:
            raw[field] = val

    return Settings.model_validate(raw)