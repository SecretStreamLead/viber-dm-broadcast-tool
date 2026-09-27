"""Dispatcher — runs a BroadcastJob across the pool with bounded concurrency."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from viber_broadcast.adapters.base import ViberAdapter
from viber_broadcast.handlers.send_handler import SendHandler
from viber_broadcast.models.broadcast import (
    BroadcastJob,
    DeliveryResult,
    DeliveryStatus,
)
from viber_broadcast.services.account_pool import AccountPool
from viber_broadcast.services.pacing import PacingService
from viber_broadcast.services.sent_log import SentLog
from viber_broadcast.services.template_engine import TemplateEngine
from viber_broadcast.utils.logging import get_logger

log = logging.getLogger(__name__)


@dataclass(slots=True)
class DispatchSummary:
    queued: int
    sent: int
    failed: int
    skipped: int
    elapsed_s: float


class Dispatcher:
    """Fan out a job. Concurrency is bounded by the account pool size."""

    def __init__(
        self,
        adapter: ViberAdapter,
        accounts: AccountPool,
        pacing: PacingService,
        templates: TemplateEngine,
        sent_log: SentLog,
        max_retries: int = 3,
        concurrency: int | None = None,
    ) -> None:
        self._accounts = accounts
        self._accounts.adapter = adapter
        self._handler = SendHandler(accounts, pacing, templates, sent_log)
        self._max_retries = max_retries
        self._concurrency = concurrency or max(1, len(accounts))

    async def run(self, job: BroadcastJob) -> DispatchSummary:
        started = time.perf_counter()
        sem = asyncio.Semaphore(self._concurrency)
        results: list[DeliveryResult] = []

        async def _one(recipient) -> None:
            async with sem:
                result = await self._with_retries(recipient, job.template, job.dry_run)
                results.append(result)

        await asyncio.gather(*(_one(r) for r in job.recipients))

        sent = sum(1 for r in results if r.status is DeliveryStatus.SENT)
        failed = sum(1 for r in results if r.status is DeliveryStatus.FAILED)
        skipped = sum(1 for r in results if r.status is DeliveryStatus.SKIPPED_DUPE)
        summary = DispatchSummary(
            queued=len(job.recipients),
            sent=sent,
            failed=failed,
            skipped=skipped,
            elapsed_s=time.perf_counter() - started,
        )
        log.info("dispatch done: %s", summary)
        return summary

    async def _with_retries(self, recipient, template: str, dry_run: bool) -> DeliveryResult:
        backoff = 1.5
        last: DeliveryResult | None = None
        for attempt in range(1, self._max_retries + 1):
            result = await self._handler.handle(recipient, template, dry_run=dry_run)
            last = result
            if result.status is not DeliveryStatus.RATE_LIMITED:
                return result
            log.warning(
                "rate limited on %s (attempt %d/%d), backing off %.1fs",
                recipient.phone, attempt, self._max_retries, backoff,
            )
            await asyncio.sleep(backoff)
            backoff *= 2
        assert last is not None
        return last