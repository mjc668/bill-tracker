from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def configure_sqlite_engine(engine: Engine) -> None:
    """Apply the PRAGMAs every SQLite connection needs.

    WAL keeps readers (dashboard queries, scheduler) from blocking the single
    writer; foreign_keys is off by default in SQLite and the schema relies on
    ON DELETE CASCADE; busy_timeout makes concurrent writer threads wait
    instead of failing with "database is locked".
    """

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
configure_sqlite_engine(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
