# Contributing to viber-dm-broadcast-tool

Thanks for wanting to push the broadcast layer forward. This repo is
service-oriented: thin handlers, fat services, dumb models, and swappable
platform adapters. Keep that shape when you send a PR.

## Ground rules

- **One concern per module.** If a service starts doing transport *and*
  persistence, split it.
- **Adapters stay thin.** Anything that talks to Viber Desktop (or a future
  Viber Web adapter) lives under `viber_broadcast/adapters/`. Nothing else
  imports `httpx` directly for Viber calls.
- **No blocking calls in async paths.** Use `httpx.AsyncClient`. If you must
  shell out to a Windows handle, wrap it in `asyncio.to_thread`.
- **Rate-limit is sacred.** Do not bypass `services/pacing.py`. Every outbound
  DM must pass through `PacingService.acquire()`.

## Dev setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,gui]"
pre-commit install
```

## Tests

```powershell
pytest -q
ruff check .
mypy viber_broadcast
```

New service = new test file under `tests/`. Adapters get mocked via `respx`
for HTTP and a fake handle for the desktop bridge.

## Commit style

`scope: short imperative summary` — e.g. `pacing: add jittered backoff for 429`.

## Reporting bugs

Open an issue with: OS build, Python version, Viber Desktop version, the
command you ran, and the last 50 lines of `logs/broadcast.log`. Redact phone
numbers and session tokens.

## Code of conduct

Be a decent person. This is a hobbyist broadcast tool; the maintainers are
volunteers and they will close threads that turn into flame wars.