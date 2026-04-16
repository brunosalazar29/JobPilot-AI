from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models import Application, SearchRun, TaskRun

ACTIVE_APPLICATION_STATUSES = {"found", "matched", "queued", "preparing", "applying"}
ACTIVE_TASK_STATUSES = {"queued", "running"}
STOPPABLE_TASKS = {"cv_pipeline", "prepare_application_form"}


def get_or_create_search_run(db: Session, user_id: int) -> SearchRun:
    search_run = db.scalar(select(SearchRun).where(SearchRun.user_id == user_id))
    if search_run is None:
        search_run = SearchRun(
            user_id=user_id,
            status="idle",
            current_stage="Sin actividad",
            current_message="Sube tu CV y luego inicia la busqueda desde el panel.",
            last_event_at=datetime.now(UTC),
        )
        db.add(search_run)
        db.commit()
        db.refresh(search_run)
    return search_run


def update_search_run(
    db: Session,
    search_run: SearchRun,
    *,
    status: str | None = None,
    stage: str | None = None,
    message: str | None = None,
    last_error: str | None = None,
    resume_id: int | None = None,
    started_at: datetime | None = None,
    stopped_at: datetime | None = None,
) -> SearchRun:
    if status is not None:
        search_run.status = status
    if stage is not None:
        search_run.current_stage = stage
    if message is not None:
        search_run.current_message = message
    if last_error is not None:
        search_run.last_error = last_error
    if resume_id is not None:
        search_run.resume_id = resume_id
    if started_at is not None:
        search_run.started_at = started_at
    if stopped_at is not None:
        search_run.stopped_at = stopped_at
    search_run.last_event_at = datetime.now(UTC)
    db.add(search_run)
    db.commit()
    db.refresh(search_run)
    return search_run


def start_search_run(db: Session, user_id: int, resume_id: int) -> SearchRun:
    search_run = get_or_create_search_run(db, user_id)
    return update_search_run(
        db,
        search_run,
        status="running",
        stage="Iniciando busqueda",
        message="Buscando vacantes relacionadas con tu perfil.",
        last_error=None,
        resume_id=resume_id,
        started_at=datetime.now(UTC),
        stopped_at=None,
    )


def stop_search_run(db: Session, user_id: int) -> SearchRun:
    search_run = get_or_create_search_run(db, user_id)
    active_tasks = list(
        db.scalars(
            select(TaskRun).where(
                TaskRun.user_id == user_id,
                TaskRun.task_name.in_(STOPPABLE_TASKS),
                TaskRun.status.in_(ACTIVE_TASK_STATUSES),
            )
        )
    )
    for task_run in active_tasks:
        if task_run.celery_task_id:
            try:
                celery_app.control.revoke(task_run.celery_task_id, terminate=True)
            except Exception:
                pass
        task_run.status = "stopped"
        task_run.completed_at = datetime.now(UTC)
        task_run.logs = [
            *(task_run.logs or []),
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "warning",
                "message": "Search run stopped by user",
            },
        ]
        db.add(task_run)

    active_applications = list(
        db.scalars(
            select(Application).where(
                Application.user_id == user_id,
                Application.status.in_(ACTIVE_APPLICATION_STATUSES),
            )
        )
    )
    for application in active_applications:
        application.status = "cancelled"
        application.logs = [
            *(application.logs or []),
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "warning",
                "message": "Search run stopped by user",
            },
        ]
        db.add(application)

    db.commit()
    return update_search_run(
        db,
        search_run,
        status="stopped",
        stage="Detenido por usuario",
        message="La busqueda y postulacion automatica fueron detenidas.",
        stopped_at=datetime.now(UTC),
    )


def should_continue_search(db: Session, user_id: int) -> bool:
    search_run = get_or_create_search_run(db, user_id)
    return search_run.status == "running"


def mark_search_stage(db: Session, user_id: int, stage: str, message: str) -> SearchRun:
    search_run = get_or_create_search_run(db, user_id)
    return update_search_run(db, search_run, stage=stage, message=message)


def mark_search_completed(db: Session, user_id: int, message: str) -> SearchRun:
    search_run = get_or_create_search_run(db, user_id)
    remaining_active = db.scalar(
        select(Application.id).where(
            Application.user_id == user_id,
            Application.status.in_(ACTIVE_APPLICATION_STATUSES),
        )
    )
    if remaining_active is not None:
        return update_search_run(db, search_run, stage="Procesando cola", message=message)
    return update_search_run(
        db,
        search_run,
        status="completed",
        stage="Busqueda completada",
        message=message,
        stopped_at=datetime.now(UTC),
    )


def mark_search_failed(db: Session, user_id: int, error: str) -> SearchRun:
    search_run = get_or_create_search_run(db, user_id)
    return update_search_run(
        db,
        search_run,
        status="failed",
        stage="Busqueda fallida",
        message="La busqueda se detuvo por un error.",
        last_error=error,
        stopped_at=datetime.now(UTC),
    )
