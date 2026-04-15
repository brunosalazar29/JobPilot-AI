from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    message: str


class TaskAcceptedResponse(BaseModel):
    task_run_id: int
    status: str
    message: str


class TimestampedModel(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


JsonDict = dict[str, Any]
