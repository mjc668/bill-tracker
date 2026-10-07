# Bill Tracker

A self-hosted household bill tracking PWA. Define your recurring bills once, then each period's payment instances are generated automatically. Track what's paid from any device — phone, tablet, or desktop.

No third-party data sharing. No subscription. Runs locally with Docker Compose or in the cloud. Each user's data is fully isolated.


## Preview

| Payments (light) | Payments (dark) |
|---|---|
| <img src="demo/public/payments_light.png" width="350"> | <img src="demo/public/payments_dark.png" width="350"> |

| Bills | Settings |
|---|---|
| <img src="demo/public/bills.png" width="350"> | <img src="demo/public/settings.png" width="350"> |


## What it does

- **Multiple household users** — register separate accounts for each family member; every account's bills, payments, categories and settings are fully isolated.
- **Recurring bills** — define a bill once: name, category, amount, currency, recurrence (weekly / every-N weeks, monthly / every-N months, yearly / every-N years, or one-off) with an optional occurrence limit. Bill Tracker generates payment instances automatically each period.
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

Pull the published images from GitHub Container Registry and run the app with just two files — no repo clone required.

```bash
mkdir bill-tracker && cd bill-tracker
curl -O https://raw.githubusercontent.com/mjc668/bill-tracker/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/mjc668/bill-tracker/main/.env.example
cp .env.example .env
```

Edit `.env` and set a strong `POSTGRES_PASSWORD` and `JWT_SECRET` — the stack refuses to start while either is empty (generate each with `openssl rand -hex 24`). `BILL_TRACKER_VERSION` is pre-set to the current release; change it if you want a different one, then:

```bash
docker compose -f docker-compose.prod.yml up -d
```

- Frontend: http://localhost:3010
- API docs: http://localhost:8010/docs

To try it with pre-seeded demo data instead of starting empty:

```bash
docker compose -f docker-compose.prod.yml --profile demo up -d
```

`BILL_TRACKER_VERSION` is required — there is no implicit `:latest`. Set it in `.env` or per-command (e.g. `BILL_TRACKER_VERSION=3.1.0 docker compose -f docker-compose.prod.yml up -d`).


## Getting started

The steps below build the images from source — use this if you're developing Bill Tracker or want to run unreleased changes. If you just want to run the app, see [Quick start without cloning](#quick-start-without-cloning) above.

### 1. Set up environment

```bash
cp .env.example .env
```

Edit `.env` and set a strong `POSTGRES_PASSWORD` and `JWT_SECRET` (generate each with `openssl rand -hex 24`). Everything else works with the defaults for local use.

### 2. Start the app

```bash
docker compose up --build
```

- Frontend: http://localhost:3010
- API docs: http://localhost:8010/docs

### 3. Create your account

Open http://localhost:3010 and register. Each account is isolated — register separately for each family member.

### 4. Add your first bill

Go to **Bills → New Bill**. Fill in the name, category, amount, recurrence, and due date. Save it — Bill Tracker will generate this period's payment instance automatically.

### 5. Track payments

Go to **Payments**. Use the month selector to browse any period. Click **Mark as Paid** when a bill is settled — you can record a partial amount, the actual date, and a note. Upcoming instances are created automatically for recurring bills.

### 6. Set up notifications (optional)

The recommended channel is an [Apprise](https://github.com/caronc/apprise) API gateway: run the `caronc/apprise` or `lscr.io/linuxserver/apprise-api` image and point `APPRISE_BASE_URL` in `.env` at it (see the `# Notifications` section in `.env.example`), then use **Settings → Email Notifications** to send a test and configure when reminders go out (2 days before, 1 day before, on the day, 1 day after).

SMTP is an optional legacy fallback and is still required for password reset. Add the `SMTP_*` values to `.env` and restart to enable it.

The settings page also shows the current server time (UTC) so you can set send times relative to your timezone.


## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | yes | PostgreSQL password — generate with `openssl rand -hex 24`; an empty value aborts the stack |
| `JWT_SECRET` | yes | JWT signing secret — use a long random string |
| `BILL_TRACKER_VERSION` | yes (prod compose) | Released image tag to run, e.g. `3.1.0` — there is no implicit `:latest` |
| `DATABASE_URL` | yes | PostgreSQL connection string |
| `NEXT_PUBLIC_API_URL` | yes | Backend URL as seen by the browser |
| `APPRISE_BASE_URL` | no | Apprise API gateway base URL (recommended notification channel) |
| `APPRISE_KEY` | no | Stateful config key inside the Apprise gateway |
| `APPRISE_URLS` | no | Stateless Apprise targets passed per request, e.g. `ntfy://topic discord://webhook_id/webhook_token` |
| `APPRISE_TIMEOUT_SECONDS` | no | Timeout for Apprise gateway requests (default: 10) |
| `SMTP_HOST` | no | SMTP server for email reminders and password reset |
| `SMTP_PORT` | no | SMTP port (default: 587) |
| `SMTP_USER` | no | SMTP login |
| `SMTP_PASSWORD` | no | SMTP password |
| `REMINDER_FROM` | no | From address for reminder emails |
| `APP_BASE_URL` | no | Public URL of the frontend — used in password reset links (default: `http://localhost:3010`) |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | no | How long a reset token is valid in minutes (default: 60; set to 0 for no expiry) |
| `RESTORE_SNAPSHOT_RETENTION_DAYS` | no | Days a pre-restore snapshot stays recoverable before the cleanup job deletes it (default: 7) |

Copy `.env.example` to `.env`. Never commit `.env`.


## Stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, next-intl
- **Backend:** FastAPI, Python 3.13, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Database:** PostgreSQL 17 as a separate `postgres` service with a named volume
- **Runtime:** Docker Compose


## Development commands

```bash
# Start everything
docker compose up --build

# Wipe DB and start clean
docker compose down -v && docker compose up --build

# Frontend only (against a running backend)
cd frontend && npm run dev

# Backend only
cd backend && uv run uvicorn app.main:app --reload

# Lint
cd frontend && npm run lint

# Backend format check, types, tests
cd backend && uv run black --check --target-version py313 .
cd backend && uv run mypy app
cd backend && uv run pytest tests/ -v

# New DB migration after changing a model
docker compose exec backend uv run alembic revision --autogenerate -m "describe the change"
```

> **Migration note:** Always read the generated migration file before applying — autogenerate can miss new columns. For renames, write `add_column` + `UPDATE` + `drop_column` manually instead of relying on `alter_column(new_column_name=...)`.


## Deployment

The production compose file binds the frontend and backend to localhost only; put a TLS-terminating reverse proxy (Caddy, nginx + Certbot, or Cloudflare) in front. PostgreSQL runs as its own `postgres` service with a named volume — the database is not co-located in the backend container.

Full guides for Caddy, nginx + Certbot, and Cloudflare — including HTTPS/PWA requirements — are in [`context/foundation/infrastructure.md`](context/foundation/infrastructure.md#https--pwa-deployment).


## Updating

Set `BILL_TRACKER_VERSION` in `.env` to the release you want, then pull and recreate:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Database migrations run automatically when the backend starts. The running version is shown at the bottom-right of the app.

**Bill Tracker renamed its images in 3.0.0.** Images moved from `ghcr.io/mjc668/pay-tracker-*` to `ghcr.io/mjc668/bill-tracker-*`, and `PAY_TRACKER_VERSION` became `BILL_TRACKER_VERSION`. The old image names are frozen at 2.6.0, so any tooling that tracks the image a container was created with — the Unraid Docker tab, Compose Manager, update notifiers like Diun — will stop reporting updates until the reference is changed:

- **Docker Compose on the host:** re-download `docker-compose.prod.yml` (or copy the new `image:` lines), rename the env var to `BILL_TRACKER_VERSION=3.1.0`, then `pull` + `up -d`.
- **Unraid Docker tab:** edit each container → change **Repository** to `ghcr.io/mjc668/bill-tracker-backend` / `ghcr.io/mjc668/bill-tracker-frontend` (tag `3.1.0` or `latest`), Apply, then pull. Unraid's "update available" check only looks at that repository field.
- **Unraid Compose Manager (or any compose stack):** update the stack's compose/env files the same way, then `docker compose pull && docker compose up -d`.

Upgrading from 2.x also logs everyone out once (the JWT issuer/audience changed in 3.0.0) — that is expected; sign in again afterwards.


## Installing as a PWA

- **Chrome / Brave (desktop):** install icon (⊕) in the address bar, or browser menu → Install Bill Tracker
- **Android:** browser menu (⋮) → Add to Home screen
- **iOS Safari:** Share (⎋) → Add to Home Screen

Requires HTTPS in production. Localhost works as an exception in most browsers.


## Export & backup

- **XLSX** — Payments page → Export Excel. One sheet per month, all columns.
- **JSON backup** — Settings → Download Backup. Full data export scoped to your account.
- **Restore** — Settings → Restore from Backup. Shows a comparison of your current data vs. the backup (bill/payment counts, export date) before you confirm, then atomically replaces your data. Accepts `schema_version` 2–6.
- **Undo a restore** — every restore automatically snapshots your prior data server-side first (skipped if you had no existing bills). If a restore turns out to be a mistake, Settings → Restore shows a "Restore This Snapshot" option with the snapshot's timestamp, letting you revert. Snapshots are kept for `RESTORE_SNAPSHOT_RETENTION_DAYS` (default 7) and only the single most recent one is retained per account.


## Upgrading from Pay Tracker 2.x

Bill Tracker is the renamed and extended continuation of Pay Tracker. When upgrading from Pay Tracker 2.x:

- Image and package names changed: `pay-tracker-*` → `bill-tracker-*`. Use the new `ghcr.io/mjc668/bill-tracker-*` images.
- `PAY_TRACKER_VERSION` is now `BILL_TRACKER_VERSION` in `.env`.
- The JWT issuer/audience changed, so all existing sessions are invalidated — every user has to log in again. The session-expiry flow handles this gracefully.
- `POST /auth/login` and `POST /auth/register` no longer return the token in the response body; the JWT is delivered as an HttpOnly cookie only.
- The database schema and the `postgres` data volume are unchanged — existing data carries over.


## Credits

Bill Tracker is a rework and extension of **Pay Tracker** by Mariusz Winiarz — https://github.com/marwin87/pay-tracker — released under the MIT License. Thanks for the original concept and implementation.

This project adds the payment ledger, editable categories, generalized recurrence, dashboard/statistics, Apprise notifications, and other changes. The upstream MIT notice and the modifications notice are preserved in [LICENSE](LICENSE). If you use this software in a public-facing application, a clear link or attribution back to the original project is appreciated.
