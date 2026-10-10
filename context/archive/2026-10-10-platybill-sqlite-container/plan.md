# Platybill — SQLite + single container + commit builds + Unraid CA

## Frozen decisions

- Product/repo renamed to **Platybill** (mascot: platypus). GitHub repo `mjc668/platybill`, local folder `~/projects/platybill`.
- **SQLite only** — no Postgres support. Single file at `/data/platybill.db`, WAL, FKs on.
- **One all-in-one container**: Next standalone + uvicorn under supervisord. `/api/*` is reverse-proxied by Next rewrites to `127.0.0.1:8010`. One published port (3010), one volume (`/data`).
- **Unraid runtime model**: PUID/PGID entrypoint (defaults 99/100 when root; compose runs as `user: 10001:10001` and the entrypoint skips privilege handling), JWT_SECRET auto-generated and persisted in `/data` when unset (env wins), `TZ` honored (tzdata installed).
- **Builds from commits**: no GitHub Releases, no version-sync commits. On green `main`: `sha-<7>`, `main`, `latest`. Env var `PLATYBILL_TAG` (default `latest`). UI footer shows the commit SHA.
- **Unraid CA**: files prepared (`ca_profile.xml`, `templates/platybill.xml`, icons) but **not submitted** until the user has tested the container. User actions: GHCR package public, forum support thread, submission.
- Existing deployment migrates Postgres → SQLite via `scripts/migrate_postgres_to_sqlite.py` (all rows, original IDs). Keep old `JWT_SECRET` to preserve browser sessions.

## Backend — SQLite

1. `app/core/types.py`
   - `UTCDateTime(TypeDecorator)`: bind → UTC (naive stored), result → aware UTC.
   - `Money(TypeDecorator)`: `impl = BigInteger`, Decimal ↔ integer cents, quantize 2dp. SQL aggregates inherit the column type (`func.sum` uses `ReturnTypeFromArgs`), so `sum`/`coalesce`/`case` keep returning `Decimal`.
2. Models: swap `DateTime(timezone=True)` → `UTCDateTime`, `Numeric(12,2)` → `Money` (bill, payment, user, reset_token, restore_snapshot, category). Booleans: `server_default=sa.text("0"/"1")`; drop the `"null"` default on `users.monthly_summary_last_sent`. (`sqlalchemy.UUID` and `JSON` are SQLite-compatible already.)
3. `app/core/database.py`: sqlite branch — `connect_args={"check_same_thread": False}`, PRAGMAs `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL`; no pool_size/max_overflow for sqlite.
4. `app/core/config.py`: default `database_url = "sqlite:////data/platybill.db"`.
5. `app/services/stats.py`: `greatest(x, 0)` → `case((x > 0, x), else_=0)` (×3); `to_char(paid_on, 'YYYY-MM')` → `func.strftime('%Y-%m', Payment.paid_on)` (×2). `with_for_update()` in `auth.py` is silently omitted by SQLite — leave (single-writer serialization covers it).
6. Migration squash: delete `backend/alembic/versions/*`, generate one baseline against an empty SQLite DB, hand-review against models; `alembic/env.py` adds `render_as_batch=True`. Pre-4.0 Postgres DBs migrate via ETL, not Alembic.
7. Tests: `conftest.py` → session-scoped temp-file SQLite engine (`tmp_path_factory`), keep `create_all`/fixtures (rename `postgres_engine` → `sqlite_engine`); `pyproject.toml` drops `testcontainers` and runtime `psycopg2` (keep `psycopg2-binary` in dev for the ETL).
8. ETL `backend/scripts/migrate_postgres_to_sqlite.py`: `--source postgresql://… --target ./platybill.db`; `alembic upgrade head` on target, refuse non-empty DB, copy users (id, email, password_hash, token_version, prefs, timestamps), categories, bill_templates, payment_instances (incl. soft-deletes), payments, restore_snapshots, password_reset_tokens with original IDs; per-table count + `SUM(amount)` reconciliation; abort on mismatch.

## Container

- Root `Dockerfile`: stage 1 `node:22-bookworm-slim` builds frontend (`NEXT_PUBLIC_APP_VERSION` build arg); stage 2 `python:3.13-slim` + uv syncs backend venv; runtime copies venv + standalone frontend + `node` binary, installs `tzdata` + supervisor, non-root user `appuser` (10001).
- `docker/entrypoint.sh`: ensure `/data`; if root → apply PUID/PGID, chown `/data`, prepare/write `jwt_secret`, pre-migration `sqlite3.Connection.backup()` to `/data/backups/pre-upgrade-<ts>.db` (keep last 10), run `alembic upgrade head` as appuser, start supervisord (programs `user=appuser`); if non-root → same minus privilege bits. `HEALTHCHECK` on `127.0.0.1:3010`.
- `docker/supervisord.conf`: `uvicorn app.main:app --host 127.0.0.1 --port 8010` (cwd `/backend`) + `node server.js` (`HOSTNAME=0.0.0.0 PORT=3010`, cwd `/frontend`).
- `frontend/next.config.ts`: `rewrites()` `/api/:path*` → `http://127.0.0.1:8010/:path*` (baked; backend always local in-container). `frontend/src/proxy.ts`: exclude `api/` from the matcher so API calls bypass auth-routing/CSP.
- Compose: dev `docker-compose.yml` builds locally; prod `docker-compose.prod.yml` uses `ghcr.io/mjc668/platybill:${PLATYBILL_TAG:-latest}`; one `app` service (`user: 10001:10001`, cap_drop ALL, no-new-privileges), `platybill_data:/data`, port 3010 (dev all interfaces, prod 127.0.0.1). `demo` profile uses the same image with `entrypoint: /backend/.venv/bin/python /app/demo/seed.py`, `SEED_BASE_URL=http://app:3010/api`; `demo/seed.py` switches `requests` → `httpx`.
- `infra/backup.sh`: SQLite backup via `docker compose exec` python + `docker compose cp`, gzip, retention.

## CI / builds from commits

- Delete `.github/workflows/release.yml`.
- `ci.yml`: keep frontend/backend/docker-e2e; backend no longer needs Docker; e2e `E2E_API_URL=http://localhost:3010/api` (and compose up of the single service). Add publish job on `push` to `main`, `needs: [frontend, backend, docker-e2e]`: native matrix amd64 (`ubuntu-latest`) + arm64 (`ubuntu-24.04-arm`), push by digest, merge manifest with tags `sha-<7>`, `main`, `latest`; GHA cache; concurrency cancel per ref; OCI revision/source labels; `workflow_dispatch`.
- Version fields become static cosmetic (`0.0.0`); remove version-sync job and release references. Footer (`AppFooter.tsx`) shows `NEXT_PUBLIC_APP_VERSION` = `sha-<short>` in CI, `dev` locally.

## Unraid CA (prepare only, do not submit)

- Root `ca_profile.xml` (`<Profile>`, `<Icon>`, `<WebPage>`), `templates/platybill.xml` (`<Repository>ghcr.io/mjc668/platybill:latest`, `<WebUI>http://[IP]:[PORT:3010]`, Config: WebUI port 3010, `/data` → `/mnt/user/appdata/platybill`, PUID=99/PGID=100, TZ, ENVIRONMENT=production, COOKIE_SECURE, APP_BASE_URL, TRUST_PROXY=true, JWT_SECRET (masked, optional), APPRISE_*, SMTP_*; `<Category>Productivity</Category>`, `<ExtraParams>--restart=unless-stopped</ExtraParams>`, `<MinVer>6.12`, MIT license, `<DefaultTagDescription>Rolling builds from main</DefaultTagDescription>`).
- `icon.png` (128×128) + `icon.svg` — wombat mark; README Unraid/CA install section.
- User prerequisites later: GHCR package public, forum support thread, submit at ca.unraid.net.

## Rebrand sweep

`Bill Tracker` → `Platybill` across frontend i18n (en/pl/de), metadata/manifest, emails, README/docs, `AGENTS.md`, `infrastructure.md`, `.env.example`, LICENSE modification line, image/env references (`BILL_TRACKER_*` → `PLATYBILL_*`). Upstream Pay Tracker credit stays.

## Verification

```
cd backend && nix shell nixpkgs#python313 -c bash -c 'export UV_PYTHON=python3.13; nix run nixpkgs#uv -- run black --check --target-version py313 .; nix run nixpkgs#uv -- run mypy app; nix run nixpkgs#uv -- run pytest tests/ -q'
cd frontend && nix shell nixpkgs#nodejs_22 -c bash -c 'npm run lint; npm run build; npx tsc --noEmit -p tests/e2e/tsconfig.json'
```
Container: build image, run with a bind mount, register → bill → payment → backup/restore, upgrade path with the ETL against a temp Postgres.

## Out of scope

- CA submission (user tests first).
- Digest pinning of base images, GHCR cleanup of old `pay-tracker-*`/`bill-tracker-*` packages.
- Web Push.

## Status (implementation notes)

- Repo/product renamed to Platybill; JWT issuer/audience changed to `platybill*` (users sign in once after migrating).
- Supervisord config is generated by `docker/entrypoint.sh` (no static file) to support both root/PUID and non-root compose modes; renames base images fully-qualified for podman compatibility.
- Boolean `server_default`s are `text("0"/"1")`; a `GUID` type decorator replaced `sqlalchemy.UUID` (SQLite reflected it as NUMERIC and broke `alembic check`).
- `stats.py` uses `type_coerce(..., Money)` for `remaining` because TypeDecorator arithmetic delegates to the impl and loses the cents result processor.
- ETL verified end-to-end (podman postgres:17 at the old head `b9c0d1e2f3a4`, seeded edge cases, exact count/sum reconciliation, Decimal/aware-datetime/UUID round-trip).
- Container verified end-to-end (root+PUID 99/100 and non-root 10001 paths, register/bill/sync/stats through the Next `/api` rewrite, demo seeder via httpx).
- CA files (`ca_profile.xml`, `templates/platybill.xml`, `icon.png`) are prepared but not submitted; forum support thread + public GHCR package still pending.
- Local `.env` was migrated (Postgres vars removed, `PLATYBILL_TAG`/`TRUST_PROXY` added); a backup copy ` .env.bak-*` was kept.
- Final-tree re-verification (after the last rebrand edits): full check suite green (black/mypy/574 pytest, eslint/build/e2e tsc), image rebuilt from the current tree, non-root container smoke passed through the Next `/api` rewrite (register → bill → sync → partial pay → mark paid → stats → export → restore → logout) and restart produced a valid `pre-upgrade-*.db` snapshot with idempotent Alembic at `4fc2c1940c54`.
- Branding settled on **Platybill**: first pass was Hearthbill/wombat, then Wombill, then Platybill; the final mark is a traced swimming platypus (accentuated bill) rendered to all icon sizes, with a light-theme variant (yellow disc, no tile) swapped via the `dark` class.
- UI refresh: green/emerald accents replaced with the blue scale, dark theme by default (toggle retained), language switcher and pl/de messages removed — UI is English-only for now (backend email languages untouched).
- e2e re-verified locally on NixOS: 24/24 green. Fixed two latent issues in `frontend/playwright.config.ts` — the stale `webServer` command still listed the removed postgres/backend/frontend services (now `app demo-data` via `-f ../docker-compose.yml`), and the PWA service worker bypassed `page.route` mocks once active (now `serviceWorkers: 'block'`). Added a `PLAYWRIGHT_CHROMIUM_PATH` override for FHS-less systems.
- Security audit finding: with `TRUST_PROXY=true` and the container port exposed directly, a client-supplied `X-Forwarded-For` is forwarded unchanged by Next (`??=`), so spoofed values bypassed IP rate limits (verified against a live container). `TRUST_PROXY` now defaults to `false` everywhere (.env.example, CA template), docs explain it is only safe behind a proxy that appends the real address, and SECURITY.md gained a deployment-hardening section.

