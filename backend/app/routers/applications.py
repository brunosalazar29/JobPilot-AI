from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Application, Job, JobMatch, User
from app.schemas.application import APPLICATION_STATUSES, ApplicationCreate, ApplicationRead, ApplicationStatusUpdate
from app.schemas.common import TaskAcceptedResponse
from app.services.generation import generate_application_responses
from app.services.matching import get_parsed_resume
from app.services.task_dispatch import dispatch_task
from app.services.task_logger import create_task_run, log_activity
from app.tasks.automation_tasks import prepare_application_form_task


router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    job = db.get(Job, payload.job_id) if payload.job_id else None
    if job is None and (not payload.company or not payload.position):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide job_id or company and position",
        )

    match = None
    if job is not None:
        match = db.scalar(select(JobMatch).where(JobMatch.user_id == current_user.id, JobMatch.job_id == job.id))
    parsed_resume = get_parsed_resume(db, current_user.id, payload.resume_id)
    profile = current_user.profile
    responses = generate_application_responses(profile, job, parsed_resume)

    application = Application(
        user_id=current_user.id,
        job_id=job.id if job else None,
        resume_id=payload.resume_id,
        company=job.company if job else payload.company or "",
        position=job.title if job else payload.position or "",
        url=job.url if job else payload.url,
        score=match.score if match else None,
        status="pending",
        generated_responses=responses,
        logs=[],
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    log_activity(db, current_user.id, "application", "created", application.position, entity_id=application.id)
    return application


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .options(selectinload(Application.job))
            .where(Application.user_id == current_user.id)
            .order_by(Application.created_at.desc())
        )
    )


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    application = db.scalar(
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.id == application_id, Application.user_id == current_user.id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.post("/{application_id}/prepare", response_model=TaskAcceptedResponse, status_code=202)
def prepare_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskAcceptedResponse:
    application = get_application(application_id, current_user, db)
    task_run = create_task_run(db, current_user.id, "prepare_application_form", {"application_id": application.id})
    dispatch_task(db, task_run, prepare_application_form_task, task_run.id, application.id)
    return TaskAcceptedResponse(task_run_id=task_run.id, status=task_run.status, message="Application preparation queued")


@router.patch("/{application_id}/status", response_model=ApplicationRead)
def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported application status")
    application = get_application(application_id, current_user, db)
    application.status = payload.status
    if payload.status == "applied":
        application.applied_at = datetime.now(UTC)
    db.add(application)
    db.commit()
    db.refresh(application)
    log_activity(db, current_user.id, "application", "status_updated", payload.status, entity_id=application.id)
    return application
