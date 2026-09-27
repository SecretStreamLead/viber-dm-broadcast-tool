"""Account model — a single Viber identity usable for outbound DMs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class AccountState(StrEnum):
    READY = "ready"
    COOLING = "cooling"
    BANNED = "banned"
    DISABLED = "disabled"


class Account(BaseModel):
    """One Viber account in the pool.

    `session_ref` is a keyring key, never the raw blob. The blob lives in the
    OS credential store via `keyring`.
    """

    id: str
    label: str
    phone: str
    session_ref: str
    state: AccountState = AccountState.READY
    sent_today: int = 0
    last_used_at: datetime | None = None
    cooldown_until: datetime | None = None
    daily_cap: int = 180

    def is_available(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.state is not AccountState.READY:
            return False
        if self.cooldown_until and self.cooldown_until > now:
            return False
        return self.sent_today < self.daily_cap

    def mark_sent(self, now: datetime | None = None) -> None:
        self.sent_today += 1
        self.last_used_at = now or datetime.now(timezone.utc)

    def cool_down(self, seconds: float, now: datetime | None = None) -> None:
        from datetime import timedelta

        base = now or datetime.now(timezone.utc)
        self.cooldown_until = base + timedelta(seconds=seconds)
        self.state = AccountState.COOLING