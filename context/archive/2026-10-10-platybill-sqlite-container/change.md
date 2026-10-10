---
change_id: platybill-sqlite-container
title: Platybill — SQLite, single container, commit builds, platypus rebrand
status: archived
created: 2026-10-08
updated: 2026-10-10
archived_at: 2026-10-10T00:00:00Z
---

## Notes

Replaced the split Postgres + backend + frontend stack with one all-in-one image:
Next standalone and uvicorn run under supervisord, the browser hits `/api/*`
same-origin and Next rewrites it to `127.0.0.1:8010`, and all state lives in a
single SQLite file at `/data/platybill.db` (WAL, foreign keys on). A PUID/PGID
entrypoint persists the JWT secret, takes a pre-migration SQLite snapshot into
`/data/backups`, runs `alembic upgrade head`, and starts both processes; builds
publish per green `main` commit (`sha-<7>`, `main`, `latest`) instead of
versioned releases.

The product was rebranded to **Platybill** with a hand-traced platypus mark
(light/dark theme variants), blue UI accents, dark by default, and an
English-only UI for launch. An ETL script
(`backend/scripts/migrate_postgres_to_sqlite.py`) migrates 3.1.x Postgres
databases with original IDs and count/sum reconciliation.

Verification: black/mypy/574 pytest, eslint/build/e2e tsc, 24/24 Playwright
e2e against the container, ETL round-trip against postgres:17 at the old head,
root+PUID and non-root container paths, pre-migration backup on restart. The
Unraid CA template and profile are prepared; submission follows the first
published image and a test install.

Security audit during closure found that `TRUST_PROXY=true` on a directly
exposed port let clients spoof `X-Forwarded-For` and bypass rate limits; the
default is now `false` with docs and a SECURITY.md hardening section.
