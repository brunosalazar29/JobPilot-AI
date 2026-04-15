from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import SessionLocal


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "database": "ok" if db_ok else "unavailable"}
