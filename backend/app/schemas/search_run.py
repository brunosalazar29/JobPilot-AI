from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import TimestampedModel


class SearchRunRead(TimestampedModel):
    id: int
    user_id: int
    resume_id: int | None
    status: str
    current_stage: str | None
    current_message: str | None
    last_error: str | None
    started_at: datetime | None
    stopped_at: datetime | None
    last_event_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SearchRunCommandResponse(BaseModel):
    run: SearchRunRead
    task_run_id: int | None = None
    message: str
