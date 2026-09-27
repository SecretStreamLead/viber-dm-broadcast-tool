"""SQLite-backed sent log for dedupe and telemetry."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_METADATA = sa.MetaData()

sent_table = sa.Table(
    "sent",
    _METADATA,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("phone", sa.String(32), nullable=False),
    sa.Column("template", sa.String(64), nullable=False),
    sa.Column("account_id", sa.String(64), nullable=False),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("phone", "template", name="uq_phone_template"),
)


class SentLog:
    """Async SQLite store. One row per (phone, template) pair."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._ready = False

    async def _ensure(self) -> None:
        if self._ready:
            return
        async with self._engine.begin() as conn:
            await conn.run_sync(_METADATA.create_all)
        self._ready = True

    async def already_sent(self, phone: str, template: str) -> bool:
        await self._ensure()
        stmt = sa.select(sa.func.count()).select_from(sent_table).where(
            sent_table.c.phone == phone, sent_table.c.template == template
        )
        async with self._engine.connect() as conn:
            count = (await conn.execute(stmt)).scalar_one()
        return count > 0

    async def record(self, phone: str, template: str, account_id: str) -> None:
        await self._ensure()
        stmt = sa.insert(sent_table).values(
            phone=phone,
            template=template,
            account_id=account_id,
            sent_at=datetime.now(timezone.utc),
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def count_today(self) -> int:
        await self._ensure()
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = sa.select(sa.func.count()).select_from(sent_table).where(
            sent_table.c.sent_at >= start
        )
        async with self._engine.connect() as conn:
            return int((await conn.execute(stmt)).scalar_one())

    async def close(self) -> None:
        await self._engine.dispose()

    async def _flush(self) -> None:  # pragma: no cover — helper for tests
        await asyncio.sleep(0)