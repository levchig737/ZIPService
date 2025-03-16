import logging
from typing import Annotated
from fastapi import APIRouter, UploadFile, Depends, BackgroundTasks, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from task.api.deps import get_task_service, get_current_user
from task.schemas import TaskResponse, TaskResultResponse
from task.services.task_service import TaskService
from base.base import get_async_session

router = APIRouter()
logger = logging.getLogger("api")

TaskServiceDeps = Annotated[TaskService, Depends(get_task_service)]
UserDeps = Annotated[dict, Depends(get_current_user)]

cache_namespace = "TASK"

@router.post("/upload", response_model=TaskResponse, status_code=201)
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    task_service: TaskServiceDeps,
    current_user: UserDeps,
    session: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    return await task_service.upload_and_process_file(file, background_tasks, session)


@router.get("/results/{task_id}", response_model=TaskResultResponse)
# @cache(namespace=cache_namespace, expire=60)
async def get_results(
    task_id: str,
    task_service: TaskServiceDeps,
    current_user: UserDeps,
    session: AsyncSession = Depends(get_async_session),
) -> TaskResultResponse:
    result = await task_service.get_task_result(task_id, session)
    if result is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return result
