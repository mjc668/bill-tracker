---
change_id: unarchive-bills
title: Unarchive bills and resume from the next due date
status: in-progress
created: 2026-10-07
updated: 2026-10-07
---

## Notes

Archived bills can only be viewed, not restored. Add an Unarchive action on the Archived Bills page: the template returns to the active list (unpaused) and the next scheduled occurrence on/after today is seeded so the bill reappears for its next due date — skipped months while archived are not backfilled. Idempotent with existing instances and soft-deleted tombstones, cap-aware via schedule re-anchoring.
