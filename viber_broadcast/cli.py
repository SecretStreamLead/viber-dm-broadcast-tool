"""Typer CLI: the operator-facing surface of the broadcast tool."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from viber_broadcast.bootstrap import build_runtime
from viber_broadcast.models.broadcast import BroadcastJob, Recipient
from viber_broadcast.services.dispatcher import DispatchSummary
from viber_broadcast.utils.recipients import load_recipients

app = typer.Typer(
    name="viber-broadcast",
    help="Viber DM broadcast tool — bulk DM dispatch with pacing and telemetry.",
    no_args_is_help=True,
)
console = Console()


def _print_summary(summary: DispatchSummary) -> None:
    table = Table(title="Broadcast summary")
    table.add_column("metric")
    table.add_column("value", justify="right")
    table.add_row("queued", str(summary.queued))
    table.add_row("sent", str(summary.sent))
    table.add_row("failed", str(summary.failed))
    table.add_row("skipped (dupe)", str(summary.skipped))
    table.add_row("elapsed", f"{summary.elapsed_s:.1f}s")
    console.print(table)


@app.command("send")
def send(
    template: str = typer.Option(..., "--template", "-t", help="Template name in templates/."),
    recipients: Path = typer.Option(..., "--recipients", "-r", exists=True, dir_okay=False),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render and log, never send."),
    limit: int | None = typer.Option(None, "--limit", help="Cap the recipient count."),
) -> None:
    """Fire a broadcast from a template against a recipient list."""
    runtime = build_runtime()
    recips = load_recipients(recipients)
    if limit is not None:
        recips = recips[:limit]

    job = BroadcastJob(
        name=template,
        template=template,
        recipients=[Recipient(phone=r.phone, vars=r.vars) for r in recips],
        dry_run=dry_run,
    )
    summary = asyncio.run(runtime.dispatcher.run(job))
    _print_summary(summary)


@app.command("accounts")
def accounts() -> None:
    """List configured accounts and their current state."""
    runtime = build_runtime()
    table = Table(title="Account pool")
    table.add_column("id")
    table.add_column("label")
    table.add_column("state")
    table.add_column("sent today", justify="right")
    for acct in runtime.accounts.snapshot():
        table.add_row(acct.id, acct.label, acct.state, str(acct.sent_today))
    console.print(table)


@app.command("templates")
def templates() -> None:
    """List available message templates."""
    runtime = build_runtime()
    for name in runtime.templates.names():
        console.print(f"- {name}")


if __name__ == "__main__":
    app()