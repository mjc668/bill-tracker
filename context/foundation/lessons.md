# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## JWT must use HttpOnly cookies, not localStorage

**Rule:** Store JWT access tokens in HttpOnly cookies, not localStorage. localStorage is accessible to any JavaScript on the page — a single XSS vector exposes the token.

**Why:** Platybill currently stores the JWT in localStorage (auth-context.tsx). This is a known risk flagged during the bill-template-management impl review. Migrating requires coordinated changes: backend must set a `Set-Cookie` header with `HttpOnly; SameSite=Strict`, and the frontend removes the localStorage read/write and sends cookies automatically.

**Applies to:** Any future auth implementation or auth refactor. New features must not expand the localStorage JWT pattern. When implementing auth from scratch, always start with HttpOnly cookies.

## Currency must be a per-template field, never hardcoded

**Rule:** Currency belongs on `BillTemplate` as a `String(10)` column (default `PLN`). Never hardcode a currency symbol in display components or form labels.

**Why:** The app was initially shipped with `€` hardcoded in three frontend locations (`BillTemplateForm`, `BillTemplateRow`, archived page) and no `currency` column at all. Fixing it required a DB migration, schema update, and frontend changes across four files — all avoidable if currency had been modeled from the start.

**Applies to:** Any future amount-bearing model (e.g., expense entries, budget limits). Always include a `currency` field alongside any `amount` field. Display as `{amount} {currency}` — no hardcoded symbols.

## Per-user data isolation must be modeled from day one

**Rule:** Any data entity that belongs to a user (bills, payments, expenses, budgets) must carry a `user_id` FK on the table from the first migration. Never model shared-household views as "flat" if the system has per-user accounts — the access-control model must be decided before the schema is created, not retrofitted afterward.

**Why:** Platybill was initially designed as a flat household model (all users share one view). This was changed to per-user isolation after several slices were already shipped, requiring a breaking Alembic migration, a full audit of every bill/payment router endpoint, and updates to both export endpoints. The retrofit cost was significant and the window between "flat schema shipped" and "isolation added" was a real data-leak window.

**Applies to:** Any new data model that touches user-owned resources. Before writing the first migration, answer: "Should User A ever see User B's rows?" If no → add `user_id` FK + NOT NULL constraint in the initial migration. PaymentInstance (and similar child rows) can inherit user scope transitively via their parent FK — no need to denormalize `user_id` onto every table, but the root entity must carry it.

## Soft-delete is the correct tombstone for idempotent instance generation

**Rule:** When a `PaymentInstance` is deleted by the user, set `is_deleted = True` rather than hard-deleting the row. Never use template-level flags (archived, paused, custom columns) to prevent instance regeneration as a side-effect of a payment action.

**Why:** `ensure_current_period_instances` is idempotent — it skips a period if any row already exists for `(bill_id, period)`. A soft-deleted row satisfies this check automatically, making it a zero-cost tombstone. Hard-deleting the row removes the tombstone and the seeder regenerates the entry on the next page load. The alternative (setting `deleted_from_period` on `BillTemplate`) was implemented, shipped, and then reverted: it coupled instance lifecycle to template state, introduced a "reactivate" concept with no natural UX, and made a simple delete action require reasoning about two models simultaneously.

**Applies to:** Any future child entity that is seeded idempotently from a parent template. If the child can be dismissed/deleted by the user, soft-delete on the child is always the right approach — do not reach up to the parent to prevent re-seeding.

## Alembic autogenerate misses columns; alter_column rename is unreliable — write migrations manually

**Rule:** Never trust Alembic autogenerate output without verifying it actually captured the intended change. Always read the generated file before running `upgrade head`. For column renames, use add + data-copy + drop instead of `op.alter_column(..., new_column_name=...)`.

**Why:** Two failures in this project:
1. Autogenerate produced a migration that only contained FK noise (drop/recreate a foreign key) while completely missing the new `email_sent_at` column and the `reminder_send_hour → reminder_send_minute` rename. The app started, migrations appeared to succeed, but the column was absent at runtime.
2. `op.alter_column` with `server_default` on PostgreSQL requires `existing_type` — omitting it causes a silent no-op or error depending on Alembic/SQLAlchemy version. The rename appeared in the migration but did not apply, leaving the old column name in the DB and crashing the startup reminder job.

**Applies to:** Every new migration. After generating with `--autogenerate`, read the file and verify it contains the expected DDL. For renames: write `add_column` + `op.execute("UPDATE … SET new = old")` + `drop_column` explicitly. Never rely on `new_column_name` alone.

## Alembic: omit server_default on nullable columns

**Rule:** For nullable columns with no server-side default, omit `server_default` entirely in the `op.add_column` call. Do not use `server_default=sa.text("null")` — it emits a redundant `DEFAULT null` in the DDL and is non-idiomatic.

**Why:** `sa.text("null")` works on PostgreSQL but is non-standard. The column is already nullable=True, which is sufficient. Omitting `server_default` is the Alembic convention for "this column has no server default."

**Applies to:** Any future migration adding a nullable column. If the column should default to a value server-side, use `server_default="value"` (string literal or `sa.text("expression")`). If it should simply be nullable with no default, omit the argument.

## CLAUDE.md commit protocol overrides skill instructions

**Rule:** Never auto-commit, even when a skill's own procedure instructs it. Always stage, show the proposed commit message, and wait for explicit user approval before running `git commit`.

**Why:** The CLAUDE.md commit protocol is a project-level hard rule. Skill instructions are general-purpose and do not know about project-specific constraints. When the two conflict, CLAUDE.md wins — always.

**Applies to:** Every skill that includes a commit step (`/10x-implement`, `/10x-archive`, any future skill). The rule fires regardless of how mechanical or routine the commit appears.
