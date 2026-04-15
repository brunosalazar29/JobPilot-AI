from typing import Any

from celery import Task
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import TaskRun


def dispatch_task(db: Session, task_run: TaskRun, task: Task, *args: Any, **kwargs: Any) -> TaskRun:
    if settings.run_tasks_inline:
        task.run(*args, **kwargs)
        db.refresh(task_run)
        return task_run

    async_result = task.delay(*args, **kwargs)
    task_run.celery_task_id = async_result.id
    db.add(task_run)
    db.commit()
    db.refresh(task_run)
    return task_run
