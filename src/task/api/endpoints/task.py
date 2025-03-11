import logging
from typing import Annotated
from fastapi import APIRouter, UploadFile, Depends

from task.api.deps import get_task_service
from task.schemas import TaskResponse, TaskResultResponse
from task.services.task_service import TaskService

router = APIRouter()
logger = logging.getLogger("api")

TaskServiceDeps = Annotated[TaskService, Depends(get_task_service)]

@router.post("/upload", response_model=TaskResponse, status_code=201)
async def upload_file(
        file: UploadFile,
        task_service: TaskServiceDeps
) -> TaskResponse:
    return await task_service.upload_and_process_file(file)

@router.get("/results/{task_id}", response_model=TaskResultResponse)
async def get_results(
    task_id: str,
    task_service: TaskServiceDeps
) -> TaskResultResponse:
    return await task_service.get_task_result(task_id)