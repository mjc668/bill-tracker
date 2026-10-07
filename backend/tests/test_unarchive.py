"""Tests for POST /bills/{id}/unarchive — resume-next-date seeding.

Covers the unarchive contract: flags are cleared, the first scheduled
occurrence on/after today is seeded without backfilling the archived gap,
idempotency (including tombstones), cap re-anchoring, and cross-user 404.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.bill import BillTemplate, PaymentInstance, PaymentStatus
from app.services.recurrence import (
    _due_date_for_period,
    _first_occurrence_on_or_after,
    seed_next_occurrence,
)
from tests.conftest import auth, register_and_login

_BILL = {
    "name": "Electricity",
    "category": "utilities",
    "frequency": "monthly",
    "amount": "120.00",
    "currency": "PLN",
    "due_day": 15,
    "notes": None,
    "is_paused": False,
}


def _create_bill(client: TestClient, token: str, overrides: dict | None = None) -> int:
    payload = {**_BILL, **(overrides or {})}
    r = client.post("/bills", json=payload, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _insert_instance(
    db,
    bill_id: int,
    period: str,
    due_date: date,
    status=PaymentStatus.upcoming,
    is_deleted: bool = False,
) -> PaymentInstance:
    inst = PaymentInstance(
        bill_id=bill_id,
        period=period,
        due_date=due_date,
        amount="120.00",
        status=status,
        is_deleted=is_deleted,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _rows(db, bill_id: int) -> list[PaymentInstance]:
    db.expire_all()
    return (
        db.query(PaymentInstance)
        .filter(PaymentInstance.bill_id == bill_id)
        .order_by(PaymentInstance.due_date, PaymentInstance.id)
        .all()
    )


def _shift_period(period: str, delta: int) -> str:
    year, month = map(int, period.split("-"))
    total = year * 12 + (month - 1) + delta
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _next_candidate(today: date, due_day: int) -> tuple[str, date]:
    """The first period/due date on/after today, mirroring seed semantics."""
    current = today.strftime("%Y-%m")
    period = current
    if _due_date_for_period(period, due_day) < today:
        period = _shift_period(current, 1)
    return period, _due_date_for_period(period, due_day)


def _archive(client: TestClient, token: str, bill_id: int) -> None:
    r = client.post(f"/bills/{bill_id}/archive", headers=auth(token))
    assert r.status_code == 204, r.text


# ---------------------------------------------------------------------------
# Resume semantics — no gap backfill
# ---------------------------------------------------------------------------


def test_unarchive_monthly_resumes_next_due_without_gap(client_db):
    """Paused/archived monthly bill seeds exactly one occurrence >= today."""
    client, db = client_db
    token = register_and_login(client, "monthly_resume@test.com")
    today = date.today()

    overrides: dict = {"is_paused": True, "due_day": 1}
    if today.month > 2:
        overrides["due_month"] = today.month - 2  # past due_month
    bill_id = _create_bill(client, token, overrides)

    # Creation backfills the paused gap; clear it and backdate the anchor so
    # the bill looks like a long-archived schedule with no live history.
    db.query(PaymentInstance).filter(PaymentInstance.bill_id == bill_id).delete()
    bill = db.get(BillTemplate, bill_id)
    bill.start_period = _shift_period(today.strftime("%Y-%m"), -3)
    db.commit()

    _archive(client, token, bill_id)
    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_archived"] is False
    assert data["is_paused"] is False

    expected_period, expected_due = _next_candidate(today, 1)
    rows = _rows(db, bill_id)
    assert len(rows) == 1  # no gap rows
    assert rows[0].due_date == expected_due
    assert rows[0].due_date >= today
    assert rows[0].period == expected_period


def test_unarchive_weekly_resumes_only_next_occurrence(client_db):
    """Weekly resume seeds the first occurrence >= today, not the gap."""
    client, db = client_db
    token = register_and_login(client, "weekly_resume@test.com")
    today = date.today()
    start = today - timedelta(days=21)

    bill_id = _create_bill(
        client,
        token,
        {
            "frequency": "weekly",
            "start_date": start.isoformat(),
            "due_day": None,
            "is_paused": True,
        },
    )
    db.query(PaymentInstance).filter(PaymentInstance.bill_id == bill_id).delete()
    db.commit()

    _archive(client, token, bill_id)
    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text

    rows = _rows(db, bill_id)
    assert len(rows) == 1
    assert rows[0].due_date == _first_occurrence_on_or_after(start, 1, today)
    assert rows[0].due_date >= today


def test_unarchive_one_off_past_due_creates_overdue_occurrence(client_db):
    """A one-off past-due bill materializes its single (overdue) occurrence."""
    client, db = client_db
    token = register_and_login(client, "oneoff_resume@test.com")
    today = date.today()
    past_period = _shift_period(today.strftime("%Y-%m"), -1)
    past_due = _due_date_for_period(past_period, 5)

    bill_id = _create_bill(
        client, token, {"frequency": "one_off", "due_day": 5, "is_paused": True}
    )
    bill = db.get(BillTemplate, bill_id)
    bill.start_period = past_period
    db.commit()

    _archive(client, token, bill_id)
    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text

    rows = _rows(db, bill_id)
    assert len(rows) == 1
    assert rows[0].due_date == past_due
    assert rows[0].period == past_period

    # The stored status stays `upcoming`; the API derives `overdue`.
    payments = client.get(
        f"/bills/payments?month={past_period}&include_overdue=true",
        headers=auth(token),
    ).json()
    mine = [p for p in payments if p["bill_id"] == bill_id]
    assert len(mine) == 1
    assert mine[0]["status"] == "overdue"

    # Unarchiving again must not resurrect or duplicate the past occurrence.
    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text
    assert len(_rows(db, bill_id)) == 1


# ---------------------------------------------------------------------------
# Idempotency + tombstones
# ---------------------------------------------------------------------------


def test_unarchive_twice_creates_one_row(client_db):
    """Two consecutive unarchives are idempotent on (bill_id, due_date)."""
    client, db = client_db
    token = register_and_login(client, "double_resume@test.com")
    today = date.today()
    bill_id = _create_bill(client, token, {"is_paused": True, "due_day": today.day})
    _archive(client, token, bill_id)

    first = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert first.status_code == 200, first.text
    second = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert second.status_code == 200, second.text

    rows = _rows(db, bill_id)
    assert len(rows) == 1
    assert rows[0].due_date == today


def test_unarchive_existing_future_instance_not_duplicated(client_db):
    """An already-present live future instance blocks seeding."""
    client, db = client_db
    token = register_and_login(client, "existing_future@test.com")
    today = date.today()
    bill_id = _create_bill(client, token, {"is_paused": True, "due_day": today.day})
    existing = _insert_instance(db, bill_id, today.strftime("%Y-%m"), today)
    _archive(client, token, bill_id)

    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text

    rows = _rows(db, bill_id)
    assert len(rows) == 1
    assert rows[0].id == existing.id


def test_unarchive_respects_tombstone_at_candidate_date(client_db):
    """A soft-deleted row on the target date is not resurrected."""
    client, db = client_db
    token = register_and_login(client, "tombstone_resume@test.com")
    today = date.today()
    bill_id = _create_bill(client, token, {"is_paused": True, "due_day": today.day})
    tombstone = _insert_instance(
        db, bill_id, today.strftime("%Y-%m"), today, is_deleted=True
    )
    _archive(client, token, bill_id)

    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text

    rows = _rows(db, bill_id)
    assert len(rows) == 1
    assert rows[0].id == tombstone.id
    assert rows[0].is_deleted is True


# ---------------------------------------------------------------------------
# Cap-aware re-anchoring
# ---------------------------------------------------------------------------


def test_unarchive_cap_reached_reanchors_then_is_capped_out(client_db):
    """Cap 1 created months ago resumes by re-anchoring to the current cycle."""
    client, db = client_db
    token = register_and_login(client, "cap_reanchor@test.com")
    today = date.today()

    bill_id = _create_bill(
        client,
        token,
        {"is_paused": True, "max_occurrences": 1, "due_day": 1},
    )
    bill = db.get(BillTemplate, bill_id)
    bill.start_period = _shift_period(today.strftime("%Y-%m"), -3)
    db.commit()

    _archive(client, token, bill_id)
    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text
    data = r.json()

    expected_period, expected_due = _next_candidate(today, 1)
    assert data["max_occurrences"] == 1  # 1 - 0 existing rows
    assert data["start_period"] == expected_period  # re-anchored

    rows = _rows(db, bill_id)
    assert len(rows) == 1
    assert rows[0].due_date == expected_due

    # A second archive/unarchive resumes the existing instance: capped out.
    _archive(client, token, bill_id)
    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(token))
    assert r.status_code == 200, r.text
    assert len(_rows(db, bill_id)) == 1


def test_unarchive_cap_exhausted_by_existing_rows_creates_nothing(client_db):
    """When rows already meet the cap, the target occurrence is not created."""
    client, db = client_db
    token = register_and_login(client, "cap_exhausted@test.com")
    today = date.today()
    past_period = _shift_period(today.strftime("%Y-%m"), -3)

    bill_id = _create_bill(
        client,
        token,
        {"is_paused": True, "max_occurrences": 1, "due_day": 1},
    )
    bill = db.get(BillTemplate, bill_id)
    bill.start_period = past_period
    _insert_instance(db, bill_id, past_period, _due_date_for_period(past_period, 1))
    db.commit()

    db.expire_all()
    bill = db.get(BillTemplate, bill_id)
    result = seed_next_occurrence(db, bill, today)
    db.commit()

    assert result is None
    assert bill.max_occurrences == 1  # cap not reduced further
    assert bill.start_period == past_period  # schedule not re-anchored
    assert len(_rows(db, bill_id)) == 1


# ---------------------------------------------------------------------------
# Scoping
# ---------------------------------------------------------------------------


def test_unarchive_other_user_returns_404(client_db):
    client, _ = client_db
    tok_a = register_and_login(client, "owner@test.com")
    tok_b = register_and_login(client, "intruder@test.com")
    bill_id = _create_bill(client, tok_a)

    r = client.post(f"/bills/{bill_id}/unarchive", headers=auth(tok_b))
    assert r.status_code == 404


def test_unarchive_missing_bill_returns_404(client_db):
    client, _ = client_db
    token = register_and_login(client, "missing@test.com")

    r = client.post("/bills/99999/unarchive", headers=auth(token))
    assert r.status_code == 404
