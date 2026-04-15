from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def ensure_database_exists() -> None:
    """Create the SQL Server database named in DATABASE_URL when it is missing."""
    url = make_url(settings.database_url)
    if not url.drivername.startswith("mssql") or not url.database:
        return

    database_name = url.database
    escaped_identifier = database_name.replace("]", "]]")
    escaped_literal = database_name.replace("'", "''")
    master_url = url.set(database="master")
    admin_engine = create_engine(master_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True, future=True)

    try:
        with admin_engine.connect() as connection:
            connection.execute(
                text(f"IF DB_ID(N'{escaped_literal}') IS NULL CREATE DATABASE [{escaped_identifier}]")
            )
    finally:
        admin_engine.dispose()


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
