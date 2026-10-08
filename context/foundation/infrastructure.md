---
project: hearthbill
researched_at: 2026-06-24
updated: 2026-10-08
recommended_platform: self-hosted-docker-compose
runner_up: railway
context_type: mvp
tech_stack:
  language: TypeScript + Python
  framework: Next.js 16 + FastAPI
  runtime: Node.js + Python 3.13
  database: SQLite (WAL)
---

## Recommendation

**Self-hosted Docker with one all-in-one image published to GitHub Container Registry (GHCR).**

Hearthbill is distributed as a single image (`ghcr.io/mjc668/hearthbill`) containing the Next.js standalone frontend and the FastAPI backend. Inside the container, supervisord runs uvicorn on `127.0.0.1:8010` and Next on `0.0.0.0:3010`; the Next server reverse-proxies `/api/*` to the backend, so the browser only ever talks same-origin. One published port (`3010`) and one volume (`/data`) are all that's required — `/data` holds the SQLite database (`hearthbill.db`, WAL), the auto-generated JWT secret (`jwt_secret`), and pre-upgrade backups (`backups/`). There is no database service and no second container.

Images are published from every green `main` commit in CI: `sha-<7>` (immutable), plus rolling `main` and `latest` pointers. There are no GitHub Releases or version numbers; the app footer shows the deployed commit. Users pull and run via `docker compose up -d`.

The deployment target is any Linux machine (VPS or local). When remote access is needed, a Hetzner CX22 VPS (~€4.30/month) fronted by Cloudflare's free proxy tier is the reference setup. This matches the PRD's explicit self-host intent, keeps costs near-zero, and avoids any vendor dependency at the MVP stage. Railway is the recommended cloud PaaS if the user later wants managed services without operational overhead.

## Platform Comparison

Platforms were evaluated against five agent-friendly criteria: CLI-first tooling, persistent-process support (required by APScheduler), agent-readable docs, stable deploy API, and MCP/integration support. Hard filter: all serverless-only platforms (Vercel, Netlify, Cloudflare Workers) were eliminated — they cannot run a persistent background scheduler.

| Platform | CLI-first | Persistent processes | Agent-readable docs | Stable deploy API | MCP / Integration | Cost fit | EU reach | Co-location |
|---|---|---|---|---|---|---|---|---|
| **Self-hosted Docker** | Pass (docker CLI) | Pass | n/a | Pass | n/a | ~€4.30/mo ✓✓ | Any region via Hetzner | SQLite in the app container |
| **Railway** | Pass | Pass | Pass (llms.txt + markdown) | Pass | Fail | ~$10-15/mo ✓ | Amsterdam GA | Persistent volume for SQLite |
| **Render** | Partial (no CLI rollback) | Pass | Pass (llms.txt + exp. MCP) | Pass | Partial | ~$20/mo | Frankfurt only | Persistent disk for SQLite |
| **Fly.io** | Pass | Pass | Partial (no llms.txt) | Pass | Fail | ~$10-55/mo | 5 EU regions | Fly volume for SQLite |

### Shortlisted Platforms

#### 1. Self-hosted Docker (Recommended)

One image, one port, one volume. Publishing `ghcr.io/mjc668/hearthbill` and providing a `docker-compose.prod.yml` that references a pinned tag is zero infrastructure overhead — no platform account, no vendor dependency, no managed service fees, and no separate database to operate. A Hetzner CX22 (2 vCPU, 4 GB RAM, ~€3.79/month) comfortably runs the container with headroom. Cloudflare's free tier handles SSL termination and global CDN caching, making single-region deployments feel fast globally. The operational overhead (WAL-safe backup script, reverse-proxy config) is real but manageable for a solo dev and mirrors the household's existing self-host comfort level.

#### 2. Railway

Railway is the best cloud PaaS option if operational overhead becomes a pain point. It supports persistent processes (APScheduler), has EU Amsterdam GA since February 2025, full LLM-readable docs (`railway.com/llms.txt`), and can mount a volume for the SQLite file. The Hobby plan ($5/month minimum) typically runs $10-15/month. Main adaptation step: attach a persistent volume for `/data` so the database survives redeploys. Good escape hatch from self-hosting without rewriting anything.

#### 3. Render

Render offers managed deployments with a Frankfurt EU region and both `llms.txt` and experimental MCP server support. A persistent disk handles the SQLite file, and the Background Worker model fits APScheduler. Main downsides: ~$20/month for a viable setup, no CLI rollback (dashboard only), and Frankfurt is the only EU region. A reasonable option if Railway isn't available, but not the first choice.

## Anti-Bias Cross-Check: Self-hosted Docker

### Devil's Advocate — Weaknesses

1. **No managed database backups.** The SQLite file lives on a Docker volume, so snapshots are your job. Hearthbill mitigates this: `infra/backup.sh` takes WAL-safe snapshots on the host, the entrypoint copies the database to `/data/backups` before every migration, and the in-app JSON export gives users a portable per-account backup. A broken backup cron is still silently broken until disaster.

2. **Zero-downtime deploys don't come free.** `docker compose up -d` causes a brief service restart gap. A blue-green deploy requires additional scripting not included in a basic Docker Compose setup.

3. **SSL certificate management is on you.** Certbot + Let's Encrypt requires renewal automation (every 90 days). Cloudflare as a proxy sidesteps this but adds a DNS dependency. PWA installation and secure cookies require HTTPS.

4. **No platform-level health monitoring.** There's no equivalent to Railway's service health dashboard. A crashed container restarts automatically via Docker's `restart: unless-stopped` policy and the image's `HEALTHCHECK`, but silent failures (e.g. APScheduler stops without crashing) are invisible until a user notices missed reminders.

5. **Hetzner support is community-only.** No live chat, no ticketed support on basic plans. DigitalOcean at $12/month offers ticketed support if that matters.

### Pre-Mortem — How This Could Fail

The household self-hosted Hearthbill on a Hetzner CX22 in 2026. Eight months later, the `/data` volume on the VPS disk filled up — Docker named volumes don't auto-expand, and nobody was monitoring disk usage. Writes to `hearthbill.db` started failing with `SQLITE_FULL`, and the app returned errors. The `infra/backup.sh` cron that was set up on day one had been silently failing for two months because the compose project name had changed. The last usable snapshot was two months old; reconstructing the missing payments required cross-referencing the household's bank statements. The second failure: Let's Encrypt certificate renewal failed because the Certbot container wasn't in the Compose file — it had been set up separately via SSH and was forgotten when the server was reprovisioned. The PWA install broke for household members because the cert expired. Both failures were entirely preventable with monitoring, but monitoring wasn't included in the MVP scope.

### Unknown Unknowns

1. **Docker named volumes don't auto-expand.** The `/data` volume grows with usage (database + backups). The CX22's 40 GB SSD is generous for a household app, but monitoring `df -h` should be part of the ops checklist. A full disk causes SQLite write failures (`SQLITE_FULL`) with no advance warning.

2. **APScheduler and DST/UTC mismatch.** The scheduler fires on the container's time zone (`TZ` env var; tzdata is installed). If the host clock drifts or DST handling is wrong, reminders can arrive an hour early or late. Prefer a fixed `Etc/UTC` or a well-known zone, and test reminder timing across DST transitions.

3. **Docker Compose `restart: unless-stopped` is not the same as systemd supervision.** If the VPS reboots, Docker itself must autostart (enabled by default on most distros), then Compose services restart. But if Docker fails to start (e.g., after a kernel update requiring a reboot), services don't come up. Set `docker.service` as a systemd dependency: `systemctl enable docker`.

4. **GHCR image visibility.** GitHub Container Registry images default to private if the repo is private. Publishing Hearthbill images for self-hosters requires explicitly setting the package visibility to public — check GitHub repo → Packages → `hearthbill` → Settings.

5. **Cloudflare proxying WebSocket / long-poll.** Cloudflare's free plan proxies HTTP/HTTPS and WebSocket connections but has a 100-second timeout on connections. For Hearthbill this is irrelevant (no WebSockets), but worth knowing if the app ever adds real-time features.

## Operational Story

- **Preview deploys**: No platform-provided preview URLs. Test locally with `docker compose up --build` before pushing. For staging, a second VPS or a `staging` branch with a separate Compose override (`docker-compose.staging.yml`) is the standard pattern.
- **Secrets**: `.env` file on the VPS (never committed). Copy to server via `scp .env user@server:/app/.env` or use a GitHub Actions secret → SSH deploy step that writes the file before `docker compose up`. `JWT_SECRET` may be left empty: the entrypoint generates one and persists it at `/data/jwt_secret`; setting it explicitly keeps a stable secret across reinstalls.
- **Rollback**: set `HEARTHBILL_TAG` to a previous immutable `sha-<7>` tag and `docker compose -f docker-compose.prod.yml up -d`. Rollback time: ~60 seconds. If the bad deploy had already run a database migration, restore the matching pre-upgrade snapshot from `/data/backups/pre-upgrade-<timestamp>.db` before starting the old image (Alembic downgrades are not the supported path on SQLite).
- **Approval**: All production actions (deploy, rollback, secret rotation, server access) require a human SSH session. No unattended agent access to the VPS.
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f --tail=100 app` (supervisord merges uvicorn and Next output into the container log). For persistent logs across restarts: configure Docker's `json-file` log driver with `max-size: 10m` and `max-file: 3` in `/etc/docker/daemon.json`.

## Notification channels

Reminders and the monthly summary are delivered through the first configured channel:

1. **Apprise** — preferred whenever `APPRISE_BASE_URL` is set. The gateway may hold its own targets (its `APPRISE_STATELESS_URLS` or a saved config key) — `APPRISE_URLS` and `APPRISE_KEY` are optional request-level overrides.
2. **SMTP email** — optional legacy fallback, used when Apprise is not configured or fails. Password reset still requires SMTP; without it the "Forgot password" link is hidden.
3. Neither configured — the scheduler logs a warning and skips; the "send now" endpoints return `400 No notification channel configured`.

Note: `unraid/apprise-go` is a CLI-only port with no HTTP server — run `caronc/apprise` or `lscr.io/linuxserver/apprise-api` as the gateway, or wrap the Go CLI yourself.

| Env var | Default | Meaning |
|---|---|---|
| `APPRISE_BASE_URL` | — | Apprise API base URL, e.g. `http://apprise:8000` on the compose network or `http://<your-host-ip>:8000` otherwise (trailing `/` stripped) |
| `APPRISE_URLS` | — | Stateless mode: space/comma-separated target URLs passed through as-is |
| `APPRISE_KEY` | — | Stateful mode: config key stored in the Apprise container (wins over `APPRISE_URLS`) |
| `APPRISE_TIMEOUT_SECONDS` | `10` | HTTP timeout for the Apprise call |
| `SMTP_HOST` / `SMTP_PORT` | — / `587` | SMTP server and submission port (fallback channel, required for password reset) |
| `SMTP_USER` / `SMTP_PASSWORD` | — | SMTP credentials |
| `SMTP_USE_TLS` | `true` | STARTTLS for SMTP |
| `REMINDER_FROM` | — | From address for reminder emails |
| `EMAIL_BLOCKED_DOMAINS` | `["test.com","example.com"]` | JSON array of domains silently skipped by the scheduler |

The Apprise container must be reachable from the app container — use the host IP or a shared Docker network (`localhost` would point at the app container itself). Example sidecar:

```yaml
services:
  apprise:
    image: caronc/apprise:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - apprise-config:/config

volumes:
  apprise-config:
```

Stateless example:

```bash
APPRISE_BASE_URL=http://apprise:8000
APPRISE_URLS="ntfy://hearthbill discord://1234/abcdef"
```

Apprise failures fall back to email immediately (no queue or retry). `email_sent_at` is stamped only for email deliveries; reminder flags are set for any successful channel.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Host backup cron fails silently | Devil's advocate | M | H | Test the backup script on day 1 with a dry-run restore; add a cron health-check (`healthchecks.io` free tier or similar) that pings on successful backup |
| Disk fills up (`/data` volume) | Unknown unknowns | L | H | Set up a disk-usage alert: `df -h` cron that emails when >80% full; bound `/data/backups` with `BACKUP_KEEP`/`BACKUP_KEEP_DAYS` |
| APScheduler stops without crashing | Devil's advocate | L | M | Add a `/health` probe (the image already has a `HEALTHCHECK`) and monitor for missing reminders; alerts on missed scheduled sends |
| Let's Encrypt cert expires | Pre-mortem | M | M | Use Cloudflare as TLS proxy (eliminates cert management entirely); or put Certbot renewal in a Compose service with `restart: always` |
| Docker doesn't autostart after VPS reboot | Unknown unknowns | L | M | `systemctl enable docker`; `restart: unless-stopped` is set on the app service; test with `sudo reboot` before going live |
| GHCR image accidentally private | Unknown unknowns | L | L | Explicitly set package visibility to Public in GitHub repo → Packages → `hearthbill` → Settings |
| DST causes reminder timing shift | Unknown unknowns | L | L | Set the container `TZ` deliberately (or `Etc/UTC`); document the UTC-to-local offset in the user-facing settings UI |
| Zero-downtime deploy gap | Devil's advocate | H | L | For a household app, a 5-10 second restart gap is acceptable; document expected downtime during deploys |
| Bad build runs a schema migration | Devil's advocate | L | M | Pin `HEARTHBILL_TAG` to a `sha-<7>` tag; pre-upgrade snapshots in `/data/backups` make rollback a file copy |

## Getting Started

These steps assume Hetzner CX22 (Ubuntu 24.04) + Cloudflare DNS + GHCR-published images. Adapt for local-only use by skipping steps 3-4.

1. **Provision the VPS and install Docker:**
   ```bash
   # On the VPS (SSH in first)
   curl -fsSL https://get.docker.com | sh
   systemctl enable docker
   usermod -aG docker $USER
   ```

2. **Get images to GHCR:** CI already publishes multi-arch `ghcr.io/mjc668/hearthbill` from green `main` commits (`sha-<7>`, `main`, `latest`). No manual publishing step is needed; just confirm the package visibility is public (GitHub repo → Packages → `hearthbill` → Settings).

3. **Write a production Compose file** (`docker-compose.prod.yml`) referencing a pinned image tag instead of a `build:` directive:
   ```yaml
   services:
     app:
       image: ghcr.io/mjc668/hearthbill:${HEARTHBILL_TAG:-latest}
       restart: unless-stopped
       env_file: .env
       user: "10001:10001"
       ports:
         - "127.0.0.1:3010:3010"
       volumes:
         - hearthbill_data:/data

   volumes:
     hearthbill_data:
   ```

4. **Set up Cloudflare:** Point your domain's nameservers to Cloudflare, add an A record to the VPS IP, enable the orange-cloud proxy. This gives free SSL, CDN, and DDoS mitigation — no Certbot needed. Set `COOKIE_SECURE=true` and `TRUST_PROXY=true` in `.env`.

5. **Deploy:**
   ```bash
   # On the VPS
   cd /app
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d
   docker compose -f docker-compose.prod.yml logs -f
   ```

6. **Set up the SQLite backup cron** (on the VPS, from a checkout of this repo):
   ```bash
   # /etc/cron.daily/hearthbill-backup
   #!/bin/bash
   cd /app && ./infra/backup.sh
   # Writes ./backups/hearthbill-<timestamp>.db.gz and prunes files older
   # than BACKUP_KEEP_DAYS (default 30). Test restore quarterly:
   # gunzip -c backups/hearthbill-*.db.gz > /tmp/restore.db
   ```

## HTTPS & PWA deployment

PWA installation and secure cookies both require HTTPS (browsers exempt only `localhost`). The all-in-one container listens on **one port (3010)** and serves both the UI and `/api/*` (the Next server proxies API calls internally), so the reverse proxy is a single upstream — no separate API hostname or prefix stripping. A reference Caddy config lives at `infra/caddy/Caddyfile`.

Relevant env vars:

| Env var | HTTPS value | Why |
|---|---|---|
| `COOKIE_SECURE` | `true` | Adds `Secure` to the auth cookies. Over plain HTTP browsers drop them and login bounces back to `/login` — the backend logs a startup warning if this is misconfigured. |
| `TRUST_PROXY` | `true` | Rate limiting uses the real client IP from `X-Forwarded-For`. |
| `APP_BASE_URL` | `https://pay.example.com` | Used in password-reset links. |
| `ENVIRONMENT` | `production` | Disables API docs and rejects a weak/default JWT secret. |

### Option A — Caddy (recommended)

`infra/caddy/Caddyfile` terminates HTTPS and proxies everything to the container:

```caddy
pay.example.com {
	reverse_proxy 127.0.0.1:3010
}
```

(Use the compose service name `app:3010` instead when Caddy runs in the same compose network as Hearthbill.)

- **Public domain:** point an A record at the host; Caddy obtains and renews Let's Encrypt certificates automatically.
- **LAN-only:** use a local name (e.g. `pay.local`) and add `tls internal`. Caddy signs with its own CA — install Caddy's root certificate on every device, or PWA installation can fail silently on some platforms.

### Option B — nginx + Certbot

```nginx
server {
    listen 443 ssl;
    server_name pay.example.com;

    ssl_certificate     /etc/letsencrypt/live/pay.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pay.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3010;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
    }
}
```

Renew with `certbot renew` (systemd timer or cron). Keep the renewal in the same managed stack as the app — the pre-mortem above is exactly the failure mode where a forgotten renewal breaks PWA installs when the certificate expires.

### Option C — Cloudflare proxy (public domain)

Point the domain's nameservers at Cloudflare and proxy the A record to the host. TLS terminates at Cloudflare (no Certbot) and the origin can stay HTTP on the LAN. Still set `COOKIE_SECURE=true` and `TRUST_PROXY=true` — the browser sees HTTPS. Use Cloudflare Tunnel if no inbound ports should be opened.

### Verify the install

1. DevTools → Application → Cookies: `access_token` and `auth_logged_in` show the `Secure` flag.
2. DevTools → Application → Service Workers: the service worker is active and the manifest lists the Hearthbill icons.
3. The install prompt appears (Chrome/Edge address bar; iOS Safari → Share → Add to Home Screen).
4. Layout stays usable at 375px.

Common pitfalls:

- **`COOKIE_SECURE=true` over plain HTTP:** browsers drop the auth cookies; login appears to succeed then bounces to `/login`.
- **`tls internal`:** the Caddy CA must be trusted on every device.
- **Reverse proxy target:** proxy to port `3010` only; the container handles `/api/*` itself. Do not expose `8010` — it is bound to loopback inside the container.

## Out of Scope

The following were not evaluated in this research:
- CI/CD pipeline configuration beyond the image-publish workflow (GitHub Actions deploy workflow to a specific host)
- Production-scale architecture (multi-region, HA, disaster recovery)
- Email delivery provider configuration (FR-012)
