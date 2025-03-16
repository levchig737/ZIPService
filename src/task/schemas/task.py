from pydantic import BaseModel
from typing import Optional

from gateways.sonarqube import SonarQubeResults
from task.enums.TaskStatus import TaskStatus


class TaskResponse(BaseModel):
    task_id: str


class TaskResultResponse(BaseModel):
    status: TaskStatus
    results: Optional[SonarQubeResults] = None
