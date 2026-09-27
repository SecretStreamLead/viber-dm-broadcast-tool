# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.6.x   | yes       |
| 0.5.x   | security fixes only |
| < 0.5   | no        |

## Reporting a vulnerability

Do **not** open a public issue for security problems. Email
`security@viber-dm-broadcast-tool.invalid` with:

- A description of the issue and its impact.
- Steps to reproduce, or a PoC script.
- The affected version and platform (Windows build, Viber Desktop version).

We aim to acknowledge within 72 hours and ship a patch within 14 days for
high-severity issues.

## Scope

In-scope:

- Session token leakage in `logs/` or `sessions/`.
- Account credential exposure via `keyring` fallback paths.
- Remote code execution via adapter plugin loading.
- SQL injection in the sent-log store.

Out of scope:

- Account bans resulting from normal use of the tool. Broadcast pacing is a
  best-effort heuristic; you are responsible for how you use it.
- Third-party forks that strip the pacing layer.

## Hardening notes for operators

- Keep `sessions/` on an encrypted volume. Session blobs are the crown jewels.
- Never commit `config/local.yaml` or `accounts.json`. Both are gitignored.
- Rotate accounts on any 429 burst longer than 5 minutes.
- Run the tool behind a VPN if you're broadcasting at scale; IP reputation
  feeds directly into Viber's anti-spam heuristics.