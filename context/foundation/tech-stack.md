---
starter_id: next
package_manager: npm
project_name: wombill
hints:
  language_family: multi
  team_size: solo
  deployment_target: self-host
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: verified
  path_taken: custom
  quality_override: false
  self_check_answers:
    typed: true
    from_official_starter: true
    conventions: true
    docs_current: false
    can_judge_agent: true
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: true
---

## Why this stack

Wombill is a solo, after-hours project with auth, background tasks
(auto-generated payment instances + email reminders), Excel/JSON export, and a
self-hosted deployment target.
The stack is intentionally polyglot: Next.js (TypeScript, App Router) is the
frontend and primary scaffolding layer — it passes all four agent-friendly gates
and ships from an official CLI (create-next-app); FastAPI (Python, Pydantic,
uv) handles the backend API, export via OpenPyXL, JWT auth, and the reminder
scheduler — functionality that genuinely benefits from Python's data library
ecosystem.
Both starters pass all four quality gates. Since the Wombill rearchitecture
the two run in a **single all-in-one Docker image** (supervisord runs uvicorn on
`127.0.0.1:8010` and the Next standalone server on port `3010`, which proxies
`/api/*` to the backend), with all state in one **SQLite** file at
`/data/wombill.db` (WAL). No Postgres, no external service, one
published port and one volume. No Cloudflare or Vercel lock-in; self-host is the
deployment target. CI runs on GitHub Actions: green `main` commits are published
to `ghcr.io/mjc668/wombill` as immutable `sha-<7>` tags plus rolling
`main`/`latest` pointers — **no GitHub Releases and no version numbers** (the
footer shows the deployed commit).
