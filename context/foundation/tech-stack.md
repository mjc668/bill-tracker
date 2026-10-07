---
starter_id: next
package_manager: npm
project_name: bill-tracker
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

Bill Tracker is a solo, 7-week after-hours project with auth, background tasks
(auto-generated payment instances + email reminders), Excel/JSON export, and a
self-hosted Docker Compose deployment target.
The stack is intentionally polyglot: Next.js (TypeScript, App Router) is the
frontend and primary scaffolding layer — it passes all four agent-friendly gates
and ships from an official CLI (create-next-app); FastAPI (Python, Pydantic,
uv) handles the backend API, export via OpenPyXL, JWT auth, and email reminders
— functionality that genuinely benefits from Python's data library ecosystem.
Both starters pass all four quality gates. Bootstrapper will scaffold the
Next.js shell; the FastAPI backend is a second service scaffolded manually
alongside it and wired together by Docker Compose. No Cloudflare or Vercel
lock-in; self-host is the deployment target. CI runs on GitHub Actions with
auto-deploy-on-merge.
