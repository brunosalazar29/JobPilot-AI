from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import ActivityLog, TaskRun


def create_task_run(db: Session, user_id: int | None, task_name: str, payload: dict[str, Any] | None = None) -> TaskRun:
    task_run = TaskRun(user_id=user_id, task_name=task_name, status="queued", payload=payload or {}, logs=[])
    db.add(task_run)
    db.commit()
    db.refresh(task_run)
    return task_run


def append_task_log(db: Session, task_run: TaskRun, message: str, level: str = "info", data: dict[str, Any] | None = None) -> None:
    task_run.logs = [
        *(task_run.logs or []),
        {"timestamp": datetime.now(UTC).isoformat(), "level": level, "message": message, "data": data or {}},
    ]
    db.add(task_run)
    db.commit()


def mark_task_running(db: Session, task_run: TaskRun, progress: int = 5) -> None:
    task_run.status = "running"
    task_run.progress = progress
    task_run.started_at = datetime.now(UTC)
    db.add(task_run)
    db.commit()


def mark_task_success(db: Session, task_run: TaskRun, result: dict[str, Any] | None = None) -> None:
    task_run.status = "completed"
    task_run.progress = 100
    task_run.result = result or {}
    task_run.completed_at = datetime.now(UTC)
    db.add(task_run)
    db.commit()


def mark_task_failed(db: Session, task_run: TaskRun, error: str) -> None:
    task_run.status = "failed"
    task_run.error_message = error
    task_run.completed_at = datetime.now(UTC)
    db.add(task_run)
    db.commit()


def log_activity(
    db: Session,
    user_id: int | None,
    entity_type: str,
    action: str,
    message: str | None = None,
    entity_id: int | None = None,
    extra_data: dict[str, Any] | None = None,
) -> ActivityLog:
    log = ActivityLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        message=message,
        extra_data=extra_data or {},
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
