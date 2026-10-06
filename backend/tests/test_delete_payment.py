"""Tests for DELETE /bills/payments/{id} — single and bulk-future deletion."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.models.bill import PaymentInstance, PaymentStatus
from tests.conftest import auth, register_and_login

_BILL = {
    "name": "Electricity",
    "category": "utilities",
    "frequency": "monthly",
    "amount": 120.00,
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
    db, bill_id: int, period: str, due_date: date, status=PaymentStatus.upcoming
) -> PaymentInstance:
    inst = PaymentInstance(
        bill_id=bill_id,
        period=period,
        due_date=due_date,
        amount=100,
        status=status,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


# ---------------------------------------------------------------------------
# Single delete (no delete_future)
# ---------------------------------------------------------------------------


def test_delete_single_leaves_other_instances(client_db):
    """Without delete_future only the targeted instance is soft-deleted."""
    client, db = client_db
    token = register_and_login(client, "u@test.com")
    bill_id = _create_bill(client, token)

    i_prev = _insert_instance(db, bill_id, "2026-05", date(2026, 5, 15))
    i_target = _insert_instance(db, bill_id, "2026-06", date(2026, 6, 15))
    i_next = _insert_instance(db, bill_id, "2026-07", date(2026, 7, 15))

    r = client.delete(f"/bills/payments/{i_target.id}", headers=auth(token))
    assert r.status_code == 204

    db.expire_all()
    assert db.get(PaymentInstance, i_prev.id).is_deleted is False
    assert db.get(PaymentInstance, i_target.id).is_deleted is True
    assert db.get(PaymentInstance, i_next.id).is_deleted is False


# ---------------------------------------------------------------------------
# delete_future=true
# ---------------------------------------------------------------------------


def test_delete_future_removes_target_and_future_unpaid(client_db):
    """delete_future=true soft-deletes the target and all later unpaid instances."""
    client, db = client_db
    token = register_and_login(client, "u@test.com")
    bill_id = _create_bill(client, token)

    i_past = _insert_instance(db, bill_id, "2026-04", date(2026, 4, 15))
    i_target = _insert_instance(db, bill_id, "2026-05", date(2026, 5, 15))
    i_future1 = _insert_instance(db, bill_id, "2026-06", date(2026, 6, 15))
    i_future2 = _insert_instance(db, bill_id, "2026-07", date(2026, 7, 15))

    r = client.delete(
        f"/bills/payments/{i_target.id}?delete_future=true", headers=auth(token)
    )
    assert r.status_code == 204

    db.expire_all()
    assert db.get(PaymentInstance, i_past.id).is_deleted is False
    assert db.get(PaymentInstance, i_target.id).is_deleted is True
    assert db.get(PaymentInstance, i_future1.id).is_deleted is True
    assert db.get(PaymentInstance, i_future2.id).is_deleted is True


def test_delete_future_does_not_touch_paid_instances(client_db):
    """Paid future instances must not be soft-deleted."""
    client, db = client_db
    token = register_and_login(client, "u@test.com")
    bill_id = _create_bill(client, token)

    i_target = _insert_instance(db, bill_id, "2026-05", date(2026, 5, 15))
    i_paid = _insert_instance(
        db, bill_id, "2026-06", date(2026, 6, 15), status=PaymentStatus.paid
    )
    i_upcoming = _insert_instance(db, bill_id, "2026-07", date(2026, 7, 15))

    r = client.delete(
        f"/bills/payments/{i_target.id}?delete_future=true", headers=auth(token)
    )
    assert r.status_code == 204

    db.expire_all()
    assert db.get(PaymentInstance, i_target.id).is_deleted is True
    assert db.get(PaymentInstance, i_paid.id).is_deleted is False
    assert db.get(PaymentInstance, i_upcoming.id).is_deleted is True


def test_delete_future_does_not_affect_other_bills(client_db):
    """Instances from a different bill must be untouched."""
    client, db = client_db
    token = register_and_login(client, "u@test.com")
    bill_a = _create_bill(client, token)
    bill_b = _create_bill(client, token, {"name": "Water"})

    i_a = _insert_instance(db, bill_a, "2026-05", date(2026, 5, 15))
    i_b_future = _insert_instance(db, bill_b, "2026-06", date(2026, 6, 15))

    r = client.delete(
        f"/bills/payments/{i_a.id}?delete_future=true", headers=auth(token)
    )
    assert r.status_code == 204

    db.expire_all()
    assert db.get(PaymentInstance, i_a.id).is_deleted is True
    assert db.get(PaymentInstance, i_b_future.id).is_deleted is False


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_delete_payment_not_found(client_db):
    client, _ = client_db
    token = register_and_login(client, "u@test.com")

    r = client.delete("/bills/payments/99999", headers=auth(token))
    assert r.status_code == 404


def test_delete_future_cross_user_returns_404(client_db):
    """delete_future=true is still blocked for cross-user access."""
    client, db = client_db
    tok_a = register_and_login(client, "a@test.com")
    tok_b = register_and_login(client, "b@test.com")
    bill_id = _create_bill(client, tok_a)

    i = _insert_instance(db, bill_id, "2026-06", date(2026, 6, 15))

    r = client.delete(f"/bills/payments/{i.id}?delete_future=true", headers=auth(tok_b))
    assert r.status_code == 404
