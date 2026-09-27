"""Handle a single send request: render, pace, dispatch, log."""

from __future__ import annotations

import logging
import time

from viber_broadcast.adapters.base import AdapterError, RateLimited
from viber_broadcast.models.account import Account
from viber_broadcast.models.broadcast import (
    DeliveryResult,
    DeliveryStatus,
    Recipient,
)
from viber_broadcast.services.account_pool import AccountPool
from viber_broadcast.services.pacing import PacingService
from viber_broadcast.services.sent_log import SentLog
from viber_broadcast.services.template_engine import TemplateEngine

log = logging.getLogger(__name__)


class SendHandler:
    """Orchestrates one outbound DM. Stateless; safe to share across tasks."""

    def __init__(
        self,
        accounts: AccountPool,
        pacing: PacingService,
        templates: TemplateEngine,
        sent_log: SentLog,
    ) -> None:
        self._accounts = accounts
        self._pacing = pacing
        self._templates = templates
        self._sent_log = sent_log

    async def handle(
        self,
        recipient: Recipient,
        template_name: str,
        *,
        dry_run: bool = False,
    ) -> DeliveryResult:
        if await self._sent_log.already_sent(recipient.phone, template_name):
            return DeliveryResult(
                recipient=recipient.phone,
                account_id=None,
                status=DeliveryStatus.SKIPPED_DUPE,
            )

        body = self._templates.render(template_name, recipient.vars)
        account: Account | None = self._accounts.checkout()
        if account is None:
            return DeliveryResult(
                recipient=recipient.phone,
                account_id=None,
                status=DeliveryStatus.RATE_LIMITED,
                error="no account available in pool",
            )

        await self._pacing.acquire(account.id)

        if dry_run:
            log.info("[dry-run] would send to %s via %s", recipient.phone, account.id)
            return DeliveryResult(
                recipient=recipient.phone,
                account_id=account.id,
                status=DeliveryStatus.SENT,
                error="dry-run",
            )

        started = time.perf_counter()
        try:
            await self._accounts.adapter.send_dm(account, recipient.phone, body)
        except RateLimited as exc:
            account.cool_down(exc.retry_after_s)
            self._accounts.checkin(account)
            return DeliveryResult(
                recipient=recipient.phone,
                account_id=account.id,
                status=DeliveryStatus.RATE_LIMITED,
                error=str(exc),
            )
        except AdapterError as exc:
            self._accounts.checkin(account)
            return DeliveryResult(
                recipient=recipient.phone,
                account_id=account.id,
                status=DeliveryStatus.FAILED,
                error=str(exc),
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        account.mark_sent()
        self._accounts.checkin(account)
        await self._sent_log.record(recipient.phone, template_name, account.id)
        return DeliveryResult(
            recipient=recipient.phone,
            account_id=account.id,
            status=DeliveryStatus.SENT,
            latency_ms=latency_ms,
        )