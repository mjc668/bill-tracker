#!/usr/bin/env python3
"""One-off Postgres -> SQLite data migration for Wombill.

Copies every application table with original primary keys, then reconciles
row counts and money totals between source and target. The source is read
through SQLAlchemy Core reflection (plain Postgres types) so the SQLite-only
``Money``/``UTCDateTime`` decorators on the models never touch source values;
the target inserts go through the model tables so the decorators convert
Decimals to cents and datetimes to UTC.

Usage (from backend/):

    uv run python scripts/migrate_postgres_to_sqlite.py \
        --source postgresql://user:pass@localhost:5432/paytracker \
        --target ./wombill.db

The target file must not exist yet (or be empty). Existing Wombill data is
never merged: delete the file and re-run if a previous attempt failed.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.engine import Engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import app.models.bill  # noqa: E402,F401
import app.models.category  # noqa: E402,F401
import app.models.payment  # noqa: E402,F401
import app.models.reset_token  # noqa: E402,F401
import app.models.restore_snapshot  # noqa: E402,F401
import app.models.user  # noqa: E402,F401
from app.core.database import Base, configure_sqlite_engine  # noqa: E402

# The Postgres schema revision this script understands (the 3.1.x head).
EXPECTED_SOURCE_REVISION = "b9c0d1e2f3a4"

# Insert order satisfies foreign keys.
COPY_ORDER = [
    "users",
    "categories",
    "bill_templates",
    "payment_instances",
    "payments",
    "restore_snapshots",
    "password_reset_tokens",
]

# (table, column) pairs whose Decimal totals must match between source and target.
MONEY_CHECKS = [
    ("bill_templates", "amount"),
    ("payment_instances", "amount"),
    ("payment_instances", "paid_amount"),
    ("payments", "amount"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Postgres SQLAlchemy URL")
    parser.add_argument("--target", required=True, help="SQLite database file path")
    return parser.parse_args()


def check_target_is_fresh(target_path: Path) -> None:
    if target_path.exists() and target_path.stat().st_size > 0:
        raise SystemExit(
            f"Target {target_path} already exists and is not empty. "
            "Wombill never merges data: delete the file and re-run."
        )


def upgrade_target(target_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", target_url)
    command.upgrade(config, "head")


def check_source_revision(source_engine: Engine) -> None:
    inspector = inspect(source_engine)
    if "alembic_version" not in inspector.get_table_names():
        raise SystemExit(
            "Source database has no alembic_version table — is this the "
            "Wombill/Pay Tracker Postgres database?"
        )
    with source_engine.connect() as conn:
        revision = conn.execute(
            select(
                Table(
                    "alembic_version", MetaData(), autoload_with=source_engine
                ).c.version_num
            )
        ).scalar()
    if revision != EXPECTED_SOURCE_REVISION:
        raise SystemExit(
            f"Source schema revision is {revision!r}, expected "
            f"{EXPECTED_SOURCE_REVISION!r}. Run the 3.1.x Postgres stack once "
            "(migrations run on startup) and retry."
        )


def copy_table(
    source_engine: Engine,
    source_meta: MetaData,
    target_conn: Any,
    name: str,
) -> tuple[int, int]:
    source_table = Table(name, source_meta, autoload_with=source_engine)
    target_table = Base.metadata.tables[name]
    with source_engine.connect() as source_conn:
        rows = [dict(row._mapping) for row in source_conn.execute(select(source_table))]
    if rows:
        target_conn.execute(target_table.insert(), rows)
    return len(rows)


def table_count(conn: Any, table: Table) -> int:
    return int(conn.execute(select(func.count()).select_from(table)).scalar() or 0)


def money_total(conn: Any, table: Table, column: str) -> Decimal:
    return Decimal(
        conn.execute(select(func.coalesce(func.sum(table.c[column]), 0))).scalar()
    )


def reconcile(source_engine: Engine, target_engine: Engine) -> None:
    source_meta = MetaData()
    failures: list[str] = []
    print("\nReconciliation (source -> target):")
    with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
        for name in COPY_ORDER:
            source_table = Table(name, source_meta, autoload_with=source_engine)
            target_table = Base.metadata.tables[name]
            source_count = table_count(source_conn, source_table)
            target_count = table_count(target_conn, target_table)
            mark = "ok" if source_count == target_count else "MISMATCH"
            if source_count != target_count:
                failures.append(f"{name}: {source_count} -> {target_count} rows")
            print(f"  {name:<24} {source_count:>6} -> {target_count:<6} {mark}")

        print("\nMoney totals:")
        for table_name, column in MONEY_CHECKS:
            source_table = Table(table_name, source_meta, autoload_with=source_engine)
            target_table = Base.metadata.tables[table_name]
            source_total = money_total(source_conn, source_table, column)
            target_total = money_total(target_conn, target_table, column)
            mark = "ok" if source_total == target_total else "MISMATCH"
            if source_total != target_total:
                failures.append(
                    f"{table_name}.{column}: {source_total} -> {target_total}"
                )
            print(
                f"  {table_name + '.' + column:<30} "
                f"{source_total:>12} -> {target_total:<12} {mark}"
            )

    if failures:
        raise SystemExit("\nMigration verification failed:\n  " + "\n  ".join(failures))


def main() -> None:
    args = parse_args()
    target_path = Path(args.target).resolve()
    check_target_is_fresh(target_path)

    source_engine = create_engine(args.source)
    if source_engine.dialect.name != "postgresql":
        raise SystemExit(
            f"--source must be a Postgres URL (got {source_engine.dialect.name})"
        )
    check_source_revision(source_engine)

    target_url = f"sqlite:///{target_path}"
    print(f"Creating schema at {target_path} ...")
    upgrade_target(target_url)

    target_engine = create_engine(target_url, connect_args={"check_same_thread": False})
    configure_sqlite_engine(target_engine)

    source_meta = MetaData()
    print("Copying data:")
    with target_engine.begin() as target_conn:
        for name in COPY_ORDER:
            copied = copy_table(source_engine, source_meta, target_conn, name)
            print(f"  {name:<24} {copied:>6} rows")

    reconcile(source_engine, target_engine)
    print(
        f"\nDone. Move {target_path} to the container's /data volume and start Wombill."
    )
    print("Keep the source database until you have verified the new deployment.")


if __name__ == "__main__":
    main()
