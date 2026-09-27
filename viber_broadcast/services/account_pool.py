"""Account pool — checkout/checkin with daily caps and cooldowns."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from viber_broadcast.adapters.base import ViberAdapter
from viber_broadcast.models.account import Account, AccountState

log = logging.getLogger(__name__)


class AccountPool:
    """Thread-safe pool. Checkout returns the least-recently-used ready account."""

    def __init__(self, accounts: list[Account], adapter: ViberAdapter | None = None) -> None:
        self._lock = threading.Lock()
        self._accounts: dict[str, Account] = {a.id: a for a in accounts}
        self.adapter = adapter

    @classmethod
    def from_file(cls, path: Path) -> AccountPool:
        if not path.exists():
            log.warning("accounts file missing: %s — starting with empty pool", path)
            return cls([])
        raw = json.loads(path.read_text(encoding="utf-8"))
        accounts = [Account.model_validate(item) for item in raw]
        return cls(accounts)

    def __len__(self) -> int:
        return len(self._accounts)

    def checkout(self) -> Account | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            candidates = [a for a in self._accounts.values() if a.is_available(now)]
            if not candidates:
                return None
            candidates.sort(key=lambda a: a.last_used_at or datetime.min.replace(tzinfo=timezone.utc))
            chosen = candidates[0]
            chosen.state = AccountState.COOLING  # reserve
            return chosen

    def checkin(self, account: Account) -> None:
        with self._lock:
            if account.state is AccountState.COOLING and account.cooldown_until is None:
                account.state = AccountState.READY

    def snapshot(self) -> list[Account]:
        with self._lock:
            return list(self._accounts.values())