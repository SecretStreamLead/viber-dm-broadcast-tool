"""Broadcast job, recipient, and per-message result models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Recipient(BaseModel):
    """One DM target. `vars` feeds the template engine."""

    phone: str
    vars: dict[str, str] = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit() or ch == "+")
        if not digits.startswith("+"):
            digits = "+" + digits
        if len(digits) < 8:
            raise ValueError(f"phone too short: {v!r}")
        return digits


class BroadcastJob(BaseModel):
    name: str
    template: str
    recipients: list[Recipient]
    dry_run: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeliveryStatus(StrEnum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED_DUPE = "skipped_dupe"
    RATE_LIMITED = "rate_limited"


class DeliveryResult(BaseModel):
    recipient: str
    account_id: str | None
    status: DeliveryStatus
    error: str | None = None
    latency_ms: int | None = None
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))