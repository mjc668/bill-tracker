#!/usr/bin/env python3
"""Seed the database with demo data via the restore API endpoint."""

import json
import os
import sys
from datetime import date
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency. Run: pip install requests")
    sys.exit(1)

BASE_URL = os.environ.get("SEED_BASE_URL", "http://localhost:8010")
EMAIL = "demo@demo.com"
PASSWORD = "demo1234"
DATA_FILE = Path(__file__).parent / "seed_data.json"


def register(session: requests.Session) -> None:
    r = session.post(f"{BASE_URL}/auth/register", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 201:
        print(f"  User created: {EMAIL}")
    elif r.status_code in (400, 409) and "already" in r.text.lower():
        print(f"  User already exists: {EMAIL}")
    else:
        print(f"  Register failed ({r.status_code}): {r.text}")
        sys.exit(1)


def login(session: requests.Session) -> str:
    r = session.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print(f"  Login failed ({r.status_code}): {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    print("  Logged in, token received")
    return token


def inject_paid_today(data: dict) -> dict:
    """Replace two instances with ones paid today, using today's actual date."""
    today = date.today()
    period = today.strftime("%Y-%m")
    today_iso = today.isoformat()
    created_at = f"{today_iso}T09:00:00+00:00"

    # Bill 1 = Rent, Bill 14 = Gym Membership — both monthly, good demo candidates
    paid_today = [
        {
            "id": 9001,
            "bill_id": 1,
            "period": period,
            "due_date": today_iso,
            "amount": 1200.0,
            "status": "upcoming",
            "paid_at": None,
            "paid_amount": None,
            "notes": None,
            "created_at": created_at,
            "reminder_sent_upcoming": True,
            "reminder_sent_overdue": False,
        },
        {
            "id": 9002,
            "bill_id": 14,
            "period": period,
            "due_date": today_iso,
            "amount": 45.0,
            "status": "upcoming",
            "paid_at": None,
            "paid_amount": None,
            "notes": None,
            "created_at": created_at,
            "reminder_sent_upcoming": True,
            "reminder_sent_overdue": False,
        },
    ]

    # Remove any static instance that would collide on (bill_id, period)
    today_keys = {(inst["bill_id"], period) for inst in paid_today}
    data["payment_instances"] = [
        inst for inst in data["payment_instances"]
        if (inst["bill_id"], inst["period"]) not in today_keys
    ]
    data["payment_instances"].extend(paid_today)
    return data


def has_data(session: requests.Session, token: str) -> bool:
    r = session.get(
        f"{BASE_URL}/bills",
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.status_code == 200 and len(r.json()) > 0


def restore(session: requests.Session, token: str) -> None:
    if has_data(session, token):
        print("  Demo data already present, skipping restore.")
        return
    data = json.loads(DATA_FILE.read_text())
    data = inject_paid_today(data)
    payload = json.dumps(data)
    r = session.post(
        f"{BASE_URL}/export/restore",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("seed_data.json", payload, "application/json")},
    )
    if r.status_code != 200:
        print(f"  Restore failed ({r.status_code}): {r.text}")
        sys.exit(1)
    result = r.json()
    print(f"  Restored {result['restored_templates']} bill templates")
    print(f"  Restored {result['restored_instances']} payment instances")


def main() -> None:
    if not DATA_FILE.exists():
        print(f"Seed data file not found: {DATA_FILE}")
        sys.exit(1)

    print("Bill Tracker — demo seed")
    print(f"Target: {BASE_URL}")
    print()

    with requests.Session() as session:
        print("1. Registering user...")
        register(session)

        print("2. Logging in...")
        token = login(session)

        print("3. Restoring seed data...")
        restore(session, token)

    print()
    print("Done. Log in at http://localhost:3010")
    print(f"  Email:    {EMAIL}")
    print(f"  Password: {PASSWORD}")


if __name__ == "__main__":
    main()
