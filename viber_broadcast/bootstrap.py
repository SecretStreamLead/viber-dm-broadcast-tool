"""Bootstrap: wire config, adapters, services, and the dispatcher together.

This is the only module allowed to know about every layer. Everything below
it receives its dependencies via constructor injection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from viber_broadcast.adapters.base import ViberAdapter
from viber_broadcast.adapters.viber_desktop import ViberDesktopAdapter
from viber_broadcast.config.settings import Settings, load_settings
from viber_broadcast.services.account_pool import AccountPool
from viber_broadcast.services.dispatcher import Dispatcher
from viber_broadcast.services.pacing import PacingService
from viber_broadcast.services.sent_log import SentLog
from viber_broadcast.services.template_engine import TemplateEngine
from viber_broadcast.utils.logging import configure_logging

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Runtime:
    settings: Settings
    adapter: ViberAdapter
    accounts: AccountPool
    pacing: PacingService
    templates: TemplateEngine
    sent_log: SentLog
    dispatcher: Dispatcher


def _build_adapter(settings: Settings) -> ViberAdapter:
    """Pick the platform adapter. Today only the Viber Desktop bridge ships."""
    match settings.adapter:
        case "viber-desktop":
            return ViberDesktopAdapter(
                handle_path=settings.desktop_handle_path,
                request_timeout=settings.request_timeout_s,
            )
        case other:
            raise ValueError(f"unknown adapter: {other!r}")


def build_runtime(settings: Settings | None = None) -> Runtime:
    settings = settings or load_settings()
    configure_logging(settings.log_dir, settings.log_level)

    adapter = _build_adapter(settings)
    accounts = AccountPool.from_file(settings.accounts_file)
    pacing = PacingService(
        min_delay_s=settings.min_delay_s,
        max_delay_s=settings.max_delay_s,
        burst_window_s=settings.burst_window_s,
        burst_cap=settings.burst_cap,
    )
    templates = TemplateEngine.from_dir(settings.templates_dir)
    sent_log = SentLog(settings.sent_db)

    dispatcher = Dispatcher(
        adapter=adapter,
        accounts=accounts,
        pacing=pacing,
        templates=templates,
        sent_log=sent_log,
        max_retries=settings.max_retries,
    )
    log.info("runtime ready: adapter=%s accounts=%d", settings.adapter, len(accounts))
    return Runtime(
        settings=settings,
        adapter=adapter,
        accounts=accounts,
        pacing=pacing,
        templates=templates,
        sent_log=sent_log,
        dispatcher=dispatcher,
    )


def default_config_dir() -> Path:
    return Path.home() / ".viber-broadcast"