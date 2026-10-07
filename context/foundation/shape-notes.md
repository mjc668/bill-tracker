---
project: bill-tracker
context_type: greenfield
updated: 2026-06-11
product_type: web-app
target_scale:
  users: small
timeline_budget:
  mvp_weeks: 7
  hard_deadline: null
  after_hours_only: true
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  frs_drafted: 15
  quality_check_status: accepted
---

# Shape Notes — Bill Tracker

## Vision & Problem Statement

Managing household bills and recurring payments in Excel is tedious and error-prone.
The pain combines three compounding problems: too many manual steps (updating sheets each
month), missing capability (no reminders, no automation, no multi-user sync), and
coordination overhead (family members can't share and update the same payment list easily).

The insight: existing tools (YNAB, Mint, similar) are SaaS-heavy, subscription-based, and
over-engineered for a simple personal bill tracker that needs to work both online and
offline without depending on a third-party cloud service.

Bill Tracker is a personal-first web app that replaces the Excel sheet: it tracks recurring
and one-time bills, automates next-month instance creation, and gives a real-time shared
view to the whole household.

## User & Persona

**Primary persona:** A single household finance manager (the owner/developer, likely alone
or with one partner) who tracks all bills for the household. Other family members are
secondary users — they can view and occasionally mark bills as paid, but the primary persona
owns the setup and maintenance.

## Access Control

Authentication: email + password login.

Role model: **flat** — all authenticated users share the same household view. No permissions
differences between accounts.

Self-registration is supported (required for family onboarding). No invite-only flow for
v1 — registration is open to anyone with the app URL, which is acceptable for a private,
self-hosted or personally-managed deployment.

## Success Criteria

### Primary

**The core bill-tracking loop works end-to-end:**
Given a user has created a bill template (e.g., "Electricity — 15th, monthly, €120"),
when they mark this month's payment instance as paid (defaulting to €120 or overriding
to the actual amount), then the system automatically generates next month's instance on
the dashboard — with no manual intervention required.

Validated in local self-hosted deployment.

### Secondary

System sends email reminders for payments that are upcoming or overdue — so the user
doesn't need to check the dashboard proactively.

### Guardrails

1. **No data loss.** Payment history is never silently corrupted or deleted. Exports and
   backups produce accurate, complete data.
2. **Auth secure.** No unauthenticated access to any finance data.

## Timeline acknowledgment

Acknowledged on 2026-06-11: 6–8 week MVP requires sustained dedication across evenings
and weekends; user accepted with eyes open.

## Functional Requirements

### Authentication

- FR-001: User can register with email and password. Priority: must-have
  > Socrates: No counter-argument — registration is essential for family access.

- FR-002: User can log in with email and password. Priority: must-have
  > Socrates: No counter-argument — authentication is foundational; cannot be deferred.

### Bill Templates

- FR-003: User can create a bill template with name, amount, category, due day of month,
  recurrence type, and paused flag. Priority: must-have
  > Socrates: Category kept as must-have — needed for export reporting and filtering.

- FR-004: User can edit an existing bill template. Priority: must-have
  > Socrates: No counter-argument — template values (amount, due day) change over time.

- FR-005: User can archive a bill template (hidden from active view; existing payment
  history preserved). Priority: must-have
  > Socrates: Renamed delete → archive to prevent accidental financial history loss.
  > Archived templates' instances remain in the database and are exportable.

### Payment Instances

- FR-006: System auto-generates a payment instance from a template for the current period
  using idempotent upsert keyed on (bill_id, period). Priority: must-have
  > Socrates: No counter-argument — idempotent generation via unique constraint prevents
  > duplicates at month boundaries and timezone edges.

- FR-007: User can view a unified payment list sorted by due date with status indicators
  (upcoming / overdue / paid). Priority: must-have
  > Socrates: Unified list chosen over separate upcoming/overdue views — simpler to build;
  > status color-coding makes overdue items visible. Separate filtered views deferred to v2.

- FR-008: User can mark a payment instance as paid; actual amount defaults to the template
  amount with option to override. Priority: must-have
  > Socrates: Default to template amount reduces friction for the common case (actual =
  > expected); override available for variable bills (e.g., utilities).

- FR-009: System auto-creates the next-period payment instance when the current one is
  marked as paid; auto-creation is suppressed if the template has the paused flag set.
  Priority: must-have
  > Socrates: Pause flag at template level — allows stopping recurrence without deleting
  > the template or losing its history.

### Export & Backup

- FR-010: User can export payment data to Excel (.xlsx). Priority: must-have
  > Socrates: Both export and backup kept as must-have — Excel for family review,
  > backup for data portability.

- FR-011: User can download a full data backup in JSON or SQL format. Priority: must-have
  > Socrates: Backup and Excel export serve distinct purposes; both justified for v1.

### Reminders

- FR-012: System sends email reminders for upcoming and overdue payments via SMTP.
  Priority: nice-to-have
  > Socrates: Scoped to email-only — push notifications deferred (service worker + backend
  > push complexity).

### PWA

- FR-013: App is installable as a PWA on mobile and desktop.
  Priority: must-have
  > Local operators are expected to configure HTTPS; guidance deferred to deployment docs.

## User Stories

### US-01: Core bill-tracking loop

**Given** I have created a bill template (e.g., "Electricity — 15th, monthly, €120"),
**When** I mark this month's payment instance as paid (defaulting to €120, or overriding
  to the actual amount),
**Then** the system automatically generates next month's instance, and the current instance's
  status changes to "paid" — no manual action required.

## Business Logic

Bill Tracker applies two domain rules that a spreadsheet cannot replicate automatically:

1. **Status classification rule:** Given today's date and a payment instance's due date and
   paid status, the system classifies each instance as `upcoming` (due in the future),
   `overdue` (past due date, unpaid), or `paid`. This classification drives the dashboard
   display and reminder triggers.

2. **Recurrence automation rule:** Given a bill template with a recurrence type and a
   payment instance that has been marked paid, the system derives the next period's due
   date and creates a new instance for that period — unless the template's paused flag is
   set. The rule inputs are: template's due_day_of_month, recurrence_type, and the
   current instance's period. The output is the next instance record.

These two rules are what distinguish Bill Tracker from a static spreadsheet.

## Non-Functional Requirements

- **Data persistence:** All payment data is written to a durable database; no state is held
  in memory only. The user's payment history survives container restarts and redeployments.

- **Mobile usability:** The app layout is usable on screens as narrow as 375px without
  requiring pinch-zoom. Family members check bills on phones; the primary view must work
  on a standard mobile screen.

## Non-Goals

- **No budgeting or savings goals.** Bill Tracker tracks bills and payments; it does not
  advise on budget allocation, savings targets, or financial planning.

- **No bank or card integrations.** No automatic transaction import (no Plaid, open banking,
  or statement parsing). All data is entered manually by the user.

- **No multi-household or SaaS mode.** One household per deployment. No public sign-up, no
  per-user billing, no tenant isolation. Personal-first, not platform-first.

- **No native mobile app.** PWA is the mobile story. No App Store or Play Store
  distribution; no React Native or Flutter build.

## Quality cross-check

All elements present — no warnings.

- Access Control: present (email + password, flat model)
- Business Logic: present (two-rule domain: status classification + recurrence automation)
- Project artifacts: present
- Timeline-cost acknowledged: present (6–8 weeks, acknowledged 2026-06-11)
- Non-Goals: present (4 items)
- Preserved behavior: n/a (greenfield)

## Open Questions

- FR-013: Local-mode PWA requires HTTPS. Local deployment docs should include a self-signed
  cert or reverse-proxy setup guide. Defer to implementation planning.
- FR-012 (reminders): SMTP configuration (credentials, provider) is a deployment concern.
  Defer to bootstrapper / deployment docs.

## Forward: tech-stack

The following preferences were expressed in the seed document and should inform
tech-stack selection but are NOT part of the PRD:

- Frontend: Next.js (React), PWA
- Backend: Python, FastAPI, OpenPyXL
- Database: PostgreSQL
- Auth: FastAPI JWT
- Infrastructure: Docker, Docker Compose
- Export: .xlsx via OpenPyXL; backup as JSON
- Reminder delivery: email via SMTP