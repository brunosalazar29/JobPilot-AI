from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Resume, User
from app.schemas.search_run import SearchRunCommandResponse, SearchRunRead
from app.services.search_run import get_or_create_search_run, start_search_run, stop_search_run
from app.services.task_dispatch import dispatch_task
from app.services.task_logger import create_task_run, log_activity
from app.tasks.pipeline_tasks import cv_pipeline_task


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/current", response_model=SearchRunRead)
def get_current_run(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchRunRead:
    return get_or_create_search_run(db, current_user.id)


@router.post("/start", response_model=SearchRunCommandResponse, status_code=202)
def start_run(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchRunCommandResponse:
    latest_resume = db.scalar(
        select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc())
    )
    if latest_resume is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Primero sube un CV.")
    if latest_resume.status in {"queued", "parsing"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Espera a que el CV termine de analizarse.")
    if latest_resume.status != "parsed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu CV mas reciente no esta listo para iniciar la busqueda. Revisa el archivo o sube uno nuevo.",
        )

    current_run = get_or_create_search_run(db, current_user.id)
    if current_run.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La busqueda ya esta en curso.")

    search_run = start_search_run(db, current_user.id, latest_resume.id)
    task_run = create_task_run(
        db,
        current_user.id,
        "cv_pipeline",
        {"resume_id": latest_resume.id, "auto_started": False, "started_from_panel": True},
    )
    dispatch_task(db, task_run, cv_pipeline_task, task_run.id, latest_resume.id)
    log_activity(
        db,
        current_user.id,
        "search_run",
        "started",
        "Busqueda y postulacion iniciadas desde el panel",
        entity_id=search_run.id,
        extra_data={"resume_id": latest_resume.id, "task_run_id": task_run.id},
    )
    return SearchRunCommandResponse(
        run=search_run,
        task_run_id=task_run.id,
        message="Busqueda y postulacion iniciadas.",
    )


@router.post("/stop", response_model=SearchRunCommandResponse)
def stop_run(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchRunCommandResponse:
    search_run = stop_search_run(db, current_user.id)
    log_activity(
        db,
        current_user.id,
        "search_run",
        "stopped",
        "Busqueda y postulacion detenidas por el usuario",
        entity_id=search_run.id,
    )
    return SearchRunCommandResponse(run=search_run, task_run_id=None, message="Busqueda detenida.")
