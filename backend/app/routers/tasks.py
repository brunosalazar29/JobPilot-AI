from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import ActivityLog, TaskRun, User
from app.schemas.task import ActivityLogRead, TaskRunRead


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRunRead])
def list_task_runs(
    task_status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskRun]:
    query = select(TaskRun).where(TaskRun.user_id == current_user.id)
    if task_status:
        query = query.where(TaskRun.status == task_status)
    return list(db.scalars(query.order_by(TaskRun.created_at.desc())))


@router.get("/activity", response_model=list[ActivityLogRead])
def list_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ActivityLog]:
    return list(
        db.scalars(
            select(ActivityLog).where(ActivityLog.user_id == current_user.id).order_by(ActivityLog.created_at.desc())
        )
    )


@router.get("/{task_run_id}", response_model=TaskRunRead)
def get_task_run(
    task_run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskRun:
    task_run = db.scalar(select(TaskRun).where(TaskRun.id == task_run_id, TaskRun.user_id == current_user.id))
    if task_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task run not found")
    return task_run
