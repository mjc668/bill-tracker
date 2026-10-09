# Platybill

A self-hosted household bill tracking PWA. Define your recurring bills once, then each period's payment instances are generated automatically. Track what's paid from any device — phone, tablet, or desktop. Platybill's mascot is a wombat.

No third-party data sharing. No subscription. Runs as a single Docker container with all data in one SQLite file — no external database. Each user's data is fully isolated.


## Preview

| Payments (light) | Payments (dark) |
|---|---|
| <img src="demo/public/payments_light.png" width="350"> | <img src="demo/public/payments_dark.png" width="350"> |

| Bills | Settings |
|---|---|
| <img src="demo/public/bills.png" width="350"> | <img src="demo/public/settings.png" width="350"> |


## What it does

- **Multiple household users** — register separate accounts for each family member; every account's bills, payments, categories and settings are fully isolated.
- **Recurring bills** — define a bill once: name, category, amount, currency, recurrence (weekly / every-N weeks, monthly / every-N months, yearly / every-N years, or one-off) with an optional occurrence limit. Platybill generates payment instances automatically each period.
- **Payment ledger** — mark a payment as paid with partial amounts, an actual payment date, and a note; over/underpayments are visible against the expected amount, and reverting a payment removes it.
- **Archive, unarchive, never delete** — archiving a template hides it from active views while preserving its payment history; unarchiving resumes it like an active bill (the current period's payments are generated, past-due included) without backfilling earlier periods.
- **Dashboard** — rolling windows with overdue aging, bills-vs-payments chart, upcoming forecast, and category breakdown.
- **Payments calendar and filters** — browse any month as a calendar or list, and filter payments by status, category, or bill.
- **Editable, translatable categories** — add, rename, reorder and archive categories in Settings; defaults cover common household bills.
- **XLSX export** — download payment history as `.xlsx` (one sheet per month).
- **JSON backup & restore** — full per-user backup and restore, with pre-restore snapshots so a mistaken restore can be undone.
- **Email reminders + monthly summary** — optional scheduled reminders around each due date and a monthly paid/unpaid summary, delivered through an Apprise API gateway with SMTP as an optional fallback.
- **Password reset** — optional. When SMTP is configured, a "Forgot password?" link appears on the login page. Users receive a secure one-time reset link by email (expires after 60 minutes by default).
- **Multilingual** — English, Polish, German. Language is saved per account.
- **Installable PWA** — installs on mobile and desktop. The service worker is network-only (no offline cache), so the app always loads current data and requires connectivity.


## Quick start without cloning

Pull the published image from GitHub Container Registry and run the app with just two files — no repo clone required.

```bash
mkdir platybill && cd platybill
curl -O https://raw.githubusercontent.com/mjc668/platybill/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/mjc668/platybill/main/.env.example
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d
```

- App (UI + API): http://localhost:3010
- API docs: http://localhost:3010/api/docs (development only)

`JWT_SECRET` may be left empty: a strong secret is generated on first start and persisted at `/data/jwt_secret`, so sessions survive restarts. Set it explicitly only to keep an existing secret (e.g. after migrating). For a public deployment, set `ENVIRONMENT=production` and put TLS in front (see [Deployment](context/foundation/infrastructure.md#https--pwa-deployment)).

The compose file defaults to `PLATYBILL_TAG=latest` (rolling builds from green `main` commits). To pin a specific build, set `PLATYBILL_TAG=sha-<7>` in `.env` — the current commit is shown in the app footer.

To try it with pre-seeded demo data instead of starting empty:

```bash
docker compose -f docker-compose.prod.yml --profile demo up -d
```

Demo login: `demo@demo.com` / `demo1234`.


## Getting started

The steps below build the image from source — use this if you're developing Platybill or want to run unreleased changes. If you just want to run the app, see [Quick start without cloning](#quick-start-without-cloning) above.

### 1. Set up environment

```bash
cp .env.example .env
```

Everything works with the defaults for local use. For a public deployment set a `JWT_SECRET`, `ENVIRONMENT=production`, `COOKIE_SECURE=true`, and `APP_BASE_URL` to your public URL.

### 2. Start the app

```bash
docker compose up --build
```

- App: http://localhost:3010
- API docs: http://localhost:3010/api/docs (development only)

### 3. Create your account

Open http://localhost:3010 and register. Each account is isolated — register separately for each family member.

### 4. Add your first bill

Go to **Bills → New Bill**. Fill in the name, category, amount, recurrence, and due date. Save it — Platybill will generate this period's payment instance automatically.

### 5. Track payments

Go to **Payments**. Use the month selector to browse any period. Click **Mark as Paid** when a bill is settled — you can record a partial amount, the actual date, and a note. Upcoming instances are created automatically for recurring bills.

### 6. Set up notifications (optional)

The recommended channel is an [Apprise](https://github.com/caronc/apprise) API gateway: run the `caronc/apprise` or `lscr.io/linuxserver/apprise-api` image and point `APPRISE_BASE_URL` in `.env` at it (see the `# Notifications` section in `.env.example`), then use **Settings → Email Notifications** to send a test and configure when reminders go out (2 days before, 1 day before, on the day, 1 day after).

SMTP is an optional legacy fallback and is still required for password reset. Add the `SMTP_*` values to `.env` and restart to enable it.

The settings page also shows the current server time so you can set send times relative to your timezone; the scheduler honors the container's `TZ`.


## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `PLATYBILL_TAG` | no (prod compose) | Image tag to run: `latest` (default, rolling) or a pinned `sha-<7>` build |
| `JWT_SECRET` | no | JWT signing secret. Leave empty to auto-generate and persist at `/data/jwt_secret`; set it to keep an existing secret |
| `ENVIRONMENT` | no | `development` (default) or `production` — production disables API docs and rejects a weak/default JWT secret |
| `COOKIE_SECURE` | no | Set `true` when serving over HTTPS; over plain HTTP browsers reject Secure cookies and login bounces |
| `TRUST_PROXY` | no | Set `true` behind a reverse proxy so rate limiting uses the real client IP from `X-Forwarded-For` (default `true`) |
| `APP_BASE_URL` | no | Public URL of the app, used in password-reset links (default `http://localhost:3010`) |
| `DATABASE_URL` | no | Optional override; defaults to `sqlite:////data/platybill.db` |
| `TZ` | no | Time zone for the scheduler and logs, e.g. `Europe/Warsaw` (`Etc/UTC` default) |
| `PUID` / `PGID` | no | Unraid/root starts only: file owner for `/data` (CA template uses 99/100; compose runs as 10001) |
| `NEXT_PUBLIC_APP_VERSION` | no | Build-time version label shown in the footer (CI bakes `sha-<7>`; local default `dev`) |
| `NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS` | no | Seconds between proactive session-expiry checks on an idle tab (default 180) |
| `APPRISE_BASE_URL` | no | Apprise API gateway base URL (recommended notification channel) |
| `APPRISE_KEY` | no | Stateful config key inside the Apprise gateway |
| `APPRISE_URLS` | no | Stateless Apprise targets passed per request, e.g. `ntfy://topic discord://webhook_id/webhook_token` |
| `APPRISE_TIMEOUT_SECONDS` | no | Timeout for Apprise gateway requests (default: 10) |
| `SMTP_HOST` | no | SMTP server for email reminders and password reset |
| `SMTP_PORT` | no | SMTP port (default: 587) |
| `SMTP_USER` | no | SMTP login |
| `SMTP_PASSWORD` | no | SMTP password |
| `SMTP_USE_TLS` | no | Use STARTTLS for SMTP (default: true) |
| `REMINDER_FROM` | no | From address for reminder emails |
| `EMAIL_BLOCKED_DOMAINS` | no | JSON array of domains silently skipped by the notification scheduler |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | no | How long a reset token is valid in minutes (default: 60; 0 disables expiry) |
| `RESTORE_SNAPSHOT_RETENTION_DAYS` | no | Days a pre-restore snapshot stays recoverable before cleanup (default: 7) |
| `BACKUP_KEEP` | no | Pre-migration database snapshots kept in `/data/backups` (default: 10) |

Copy `.env.example` to `.env`. Never commit `.env`.


## Stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, next-intl
- **Backend:** FastAPI, Python 3.13, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Database:** SQLite (WAL) at `/data/platybill.db` — no database server
- **Runtime:** one all-in-one Docker image (Next standalone + uvicorn under supervisord), one port `3010`, one volume `/data`


## Development commands

```bash
# Start the whole stack (one container, UI + API on 3010)
docker compose up --build

# Start with demo data (demo@demo.com / demo1234)
docker compose --profile demo up --build

# Wipe the SQLite volume and start clean
docker compose down -v && docker compose up --build

# Frontend only (Next dev server on 3000; /api rewrites to 127.0.0.1:8010).
# API_PREFIX=/api makes the browser-side client call /api/* so the rewrite applies.
cd frontend && API_PREFIX=/api npm run dev

# Backend only (uvicorn on 8010)
cd backend && uv run uvicorn app.main:app --reload

# Lint / build
cd frontend && npm run lint && npm run build

# Backend format check, types, tests
cd backend && uv run black --check --target-version py313 .
cd backend && uv run mypy app
cd backend && uv run pytest

# New DB migration after changing a model
cd backend && uv run alembic revision --autogenerate -m "describe the change"
# ...then hand-review the file and apply:
cd backend && uv run alembic upgrade head
```

> **Migration note:** Always read the generated migration file before applying — autogenerate can miss new columns. For renames, write `add_column` + `UPDATE` + `drop_column` manually instead of relying on `alter_column(new_column_name=...)`. SQLite migrations run with `render_as_batch=True`; the container applies `alembic upgrade head` automatically on start, after snapshotting the database into `/data/backups`.


## Updating

Images are published from every green `main` commit. `latest` and `main` roll forward; `sha-<7>` tags are immutable. Set `PLATYBILL_TAG` in `.env` to pin a build (recommended for stability), then pull and recreate:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

The deployed commit is shown in the footer (bottom-right). Database migrations run automatically on start; the entrypoint first writes a pre-migration snapshot to `/data/backups/pre-upgrade-<timestamp>.db` (keeps `BACKUP_KEEP`, default 10).

**Rollback:** set `PLATYBILL_TAG` to a previous `sha-<7>` tag and recreate. If the newer build had already run a migration, restore the matching pre-upgrade `.db` from `/data/backups` before starting the old image.

Unraid users can use the Docker tab's force-update instead (the template tracks `ghcr.io/mjc668/platybill`).


## Migrating from the Postgres deployment (3.1.x)

Platybill replaces the old PostgreSQL-backed deployment with a single SQLite file. A one-off ETL copies all data (original IDs preserved) and verifies row counts and money totals. The source Postgres must be at alembic revision `b9c0d1e2f3a4` (the 3.1.x head) — run the old stack once so migrations finish, if needed.

```bash
cd backend
uv run python scripts/migrate_postgres_to_sqlite.py \
  --source postgresql://user:pass@host:5432/paytracker \
  --target ./platybill.db
```

The script refuses a non-empty target, so delete `platybill.db` and re-run if a previous attempt failed. Copy the finished file into the container's `/data` volume before first start (e.g. `/mnt/user/appdata/platybill/platybill.db` on Unraid), then start Platybill. Keep the source database until you have verified the new deployment.

**Sign in once after migrating:** the JWT issuer/audience were renamed to `platybill*`, so existing sessions are invalidated. All other data carries over. You may set `JWT_SECRET` to the old value to keep a stable secret for the future.


## Backups

- **Host-side snapshot** — `infra/backup.sh` takes a WAL-safe SQLite snapshot via the SQLite backup API inside the running container, streams it to the host as `backups/platybill-<timestamp>.db.gz`, and prunes files older than `BACKUP_KEEP_DAYS` (default 30). Never copy `/data/platybill.db` while the app is running.
- **Pre-migration snapshots** — taken automatically on every container start before `alembic upgrade head`, stored in `/data/backups`, newest `BACKUP_KEEP` kept.
- **XLSX** — Payments page → Export Excel. One sheet per month, all columns.
- **JSON backup** — Settings → Download Backup. Full data export scoped to your account.
- **Restore** — Settings → Restore from Backup. Shows a comparison of your current data vs. the backup before you confirm, then atomically replaces your data. Every restore snapshots your prior data server-side first, so a mistaken restore can be reverted (kept for `RESTORE_SNAPSHOT_RETENTION_DAYS`, default 7).


## Unraid / Community Applications

An Unraid Community Applications template is prepared in this repo (`templates/platybill.xml`, with the CA profile at `ca_profile.xml`) but is **not yet submitted to the CA catalogue** — the maintainer wants the container tested first. It will be submitted once that is done; this README will be updated when it is listed.

The prepared template configures:

- Repository `ghcr.io/mjc668/platybill:latest` (or pin a `sha-<7>` tag)
- Port `3010`
- `/data` → `/mnt/user/appdata/platybill`
- PUID `99` / PGID `100`, plus `TZ`
- `ENVIRONMENT=production`, `COOKIE_SECURE`, `APP_BASE_URL`, `TRUST_PROXY=true`

HTTPS via [SWAG](https://docs.linuxserver.io/general/swag/) (or another reverse proxy) is recommended: PWA installation and secure cookies need it.

Once listed, installation is: **Apps → search "Platybill"** → fill in port, paths, PUID/PGID and TZ → Install. Docker Hub alternatives or manual `docker run` are not the supported path — use the GHCR image above.


## Installing as a PWA

- **Chrome / Brave (desktop):** install icon (⊕) in the address bar, or browser menu → Install Platybill
- **Android:** browser menu (⋮) → Add to Home screen
- **iOS Safari:** Share (⎋) → Add to Home Screen

Requires HTTPS in production. Localhost works as an exception in most browsers.


## Credits

Platybill is a fork, rework and extension of **Pay Tracker** by Mariusz Winiarz — https://github.com/marwin87/pay-tracker — released under the MIT License. Thanks for the original concept and implementation. The Platybill rebrand and single-container/SQLite rearchitecture are by Michael Carlile.

This project adds the payment ledger, editable categories, generalized recurrence, dashboard/statistics, Apprise notifications, and other changes. The upstream MIT notice and the modifications notice are preserved in [LICENSE](LICENSE). If you use this software in a public-facing application, a clear link or attribution back to the original project is appreciated.
