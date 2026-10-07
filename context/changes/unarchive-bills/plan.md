# Unarchive Bills Implementation Plan

## Frozen contract

- `POST /bills/{bill_id}/unarchive` → 200 `BillTemplateOut`. 404 for missing/other-user IDs (uniform, per the recent hardening). Sets `is_archived = False` **and** `is_paused = False`, then seeds the next occurrence.
- **Resume semantics:** the first scheduled occurrence strictly on/after today is created; archived/skipped periods are NOT backfilled. If the bill already has a non-deleted instance on/after today, nothing new is created.
  - weekly: first occurrence ≥ today (`_first_occurrence_on_or_after`)
  - monthly/annual: first active period from the current month forward whose due date is ≥ today (`_bill_active_in_period` + `_due_date_for_period`, advancing until the date is current/future)
  - one_off: its single anchor due date (may be in the past — created overdue)
- Idempotent: existence is checked on `(bill_id, due_date)` **including soft-deleted tombstones**; a tombstoned date is never resurrected.
- **Cap-aware:** if the candidate date is at/past `max_occurrences` by anchor index, and fewer rows exist for the bill than the cap, re-anchor the schedule to the candidate (month-anchored: `start_period`; weekly: `start_date`) and reduce `max_occurrences` by the number of existing rows. If no occurrences remain, create nothing (the bill stays active but capped out).

## Backend

1. `app/services/recurrence.py`: `seed_next_occurrence(db, template, today) -> PaymentInstance | None` implementing the contract (appends without committing; the caller owns the commit). Reuse `_first_occurrence_on_or_after`, `_bill_active_in_period`, `_due_date_for_period`, `_occurrence_index`/`_cap_reached`, `_step_months`. Bound the month-anchored search (e.g. 2 years or `(60 // interval)` steps).
2. `app/routers/bills.py`: `POST /bills/{id}/unarchive` (literal path declared with the other `/payments`-style literals or before `/{bill_id}` routes as appropriate), response `BillTemplateOut`. Mutate flags, call the helper, commit once, return the bill.
3. Tests (new `backend/tests/test_unarchive.py`):
   - unpauses + unarchives and seeds the next occurrence for a monthly bill (paused at creation with a past `due_month`, archived, unarchived → exactly one instance, `due_date >= today`, no gap rows)
   - weekly resume creates only the next occurrence (start_date weeks in the past), not the gap
   - one-off past-due archive → unarchive creates the single occurrence (overdue)
   - idempotency: a future instance already exists → no duplicate; unarchive twice → one row
   - tombstone at the candidate date is respected (no resurrection)
   - cap re-anchoring: paused monthly cap 1 created months ago → unarchive seeds the current occurrence and re-anchors; a second archive/unarchive creates nothing (capped out)
   - cross-user → 404

## Frontend

1. `src/lib/bills-api.ts`: `unarchiveBill(id): Promise<void>` → `POST /bills/${id}/unarchive`.
2. `src/app/dashboard/bills/archived/page.tsx`: an **Unarchive** button on each row (lucide `ArchiveRestore`), per-row busy state, inline error on failure, and remove the row from the list on success. Keep the existing row/group styling.
3. i18n: `ArchivedBillsPage.unarchive` + `unarchiveFailed` in en/pl/de (exact parity).
4. e2e: extend `tests/e2e/05-archive-bill.spec.ts` (or a new `15-unarchive-bill.spec.ts`): create a bill, archive it via the UI, open Archived, click Unarchive, assert it disappears from Archived and appears on the active Bills page. No fixed dates.

## Verification

```
cd backend && nix shell nixpkgs#python313 -c bash -c 'export UV_PYTHON=python3.13; nix run nixpkgs#uv -- run black --check --target-version py313 .; nix run nixpkgs#uv -- run mypy app'
cd frontend && nix shell nixpkgs#nodejs_22 -c bash -c 'npm run lint; npm run build'
```

## Out of scope

- Backfilling the archived gap (deliberate).
- Unarchiving from the active page (archived only).
- Bulk unarchive.
