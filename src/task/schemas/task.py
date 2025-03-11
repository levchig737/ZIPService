from pydantic import BaseModel
from typing import Optional

from task.enums.TaskStatus import TaskStatus


class Bugs(BaseModel):
    total: int
    critical: int
    major: int
    minor: int

class CodeSmells(BaseModel):
    total: int
    critical: int
    major: int
    minor: int

class Vulnerabilities(BaseModel):
    total: int
    critical: int
    major: int
    minor: int

class CheckResult(BaseModel):
    overall_coverage: float
    bugs: Bugs
    code_smells: CodeSmells
    vulnerabilities: Vulnerabilities

class TaskResponse(BaseModel):
    task_id: str

class TaskResultResponse(BaseModel):
    status: TaskStatus
    results: Optional[CheckResult] = None