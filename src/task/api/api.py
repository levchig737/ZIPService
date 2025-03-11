from fastapi import APIRouter

from task.api.endpoints.task import router as task_router

router = APIRouter()

router.include_router(task_router)