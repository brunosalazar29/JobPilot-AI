from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import JsonDict, TimestampedModel


class TaskRunRead(TimestampedModel):
    id: int
    user_id: int | None
    task_name: str
    celery_task_id: str | None
    status: str
    progress: int
    payload: JsonDict = Field(default_factory=dict)
    result: JsonDict = Field(default_factory=dict)
    logs: list[JsonDict] = Field(default_factory=list)
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ActivityLogRead(TimestampedModel):
    id: int
    user_id: int | None
    entity_type: str
    entity_id: int | None
    action: str
    message: str | None
    extra_data: JsonDict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
