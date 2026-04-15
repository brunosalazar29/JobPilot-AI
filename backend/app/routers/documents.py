from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import GeneratedDocument, Resume, TaskRun, User
from app.schemas.common import TaskAcceptedResponse
from app.schemas.document import GeneratedDocumentCreate, GeneratedDocumentRead, ResumeRead
from app.services.task_dispatch import dispatch_task
from app.services.task_logger import create_task_run, log_activity
from app.tasks.cv_tasks import parse_resume_task
from app.tasks.document_tasks import generate_document_task
from app.tasks.pipeline_tasks import cv_pipeline_task
from app.utils.file_storage import save_upload_file


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=ResumeRead, status_code=201)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    path = save_upload_file(file, current_user.id)
    resume = Resume(
        user_id=current_user.id,
        original_filename=file.filename or path.name,
        storage_path=str(path),
        content_type=file.content_type,
        status="queued",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    log_activity(db, current_user.id, "resume", "uploaded", resume.original_filename, entity_id=resume.id)
    task_run = create_task_run(db, current_user.id, "cv_pipeline", {"resume_id": resume.id, "auto_started": True})
    dispatch_task(db, task_run, cv_pipeline_task, task_run.id, resume.id)
    return resume


@router.get("", response_model=list[ResumeRead])
def list_resumes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Resume]:
    return list(
        db.scalars(
            select(Resume)
            .options(selectinload(Resume.parsed_resume))
            .where(Resume.user_id == current_user.id)
            .order_by(Resume.created_at.desc())
        )
    )


@router.get("/generated/list", response_model=list[GeneratedDocumentRead])
def list_generated_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeneratedDocument]:
    return list(
        db.scalars(
            select(GeneratedDocument)
            .where(GeneratedDocument.user_id == current_user.id)
            .order_by(GeneratedDocument.created_at.desc())
        )
    )


@router.post("/generate", response_model=TaskAcceptedResponse, status_code=202)
def generate_document(
    payload: GeneratedDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskAcceptedResponse:
    task_run = create_task_run(db, current_user.id, "generate_document", payload.model_dump())
    dispatch_task(
        db,
        task_run,
        generate_document_task,
        task_run.id,
        current_user.id,
        payload.kind,
        payload.job_id,
        payload.resume_id,
        payload.application_id,
    )
    return TaskAcceptedResponse(task_run_id=task_run.id, status=task_run.status, message="Document generation queued")


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = db.scalar(
        select(Resume)
        .options(selectinload(Resume.parsed_resume))
        .where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.post("/{resume_id}/parse", response_model=TaskAcceptedResponse, status_code=202)
def parse_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskAcceptedResponse:
    resume = get_resume(resume_id, current_user, db)
    task_run = create_task_run(db, current_user.id, "parse_resume", {"resume_id": resume.id})
    dispatch_task(db, task_run, parse_resume_task, task_run.id, resume.id)
    return TaskAcceptedResponse(task_run_id=task_run.id, status=task_run.status, message="Resume parsing queued")
