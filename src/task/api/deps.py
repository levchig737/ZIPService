from fastapi import Depends
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from base.base import get_async_session
from settings import Settings
from task.repositories import StorageRepository, TaskRepository
from task.services.task_service import TaskService

settings = Settings()


async def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_NAME + ":" + settings.MINIO_PORT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )


async def get_storage_repository(
    minio_client: Minio = Depends(get_minio_client),
) -> StorageRepository:
    return StorageRepository(minio_client, bucket_name="zip-bucket")


async def get_task_repository(
    session: AsyncSession = Depends(get_async_session),
) -> TaskRepository:
    return TaskRepository(session=session)


async def get_task_service(
    storage_repo: StorageRepository = Depends(get_storage_repository),
    task_repo: TaskRepository = Depends(get_task_repository),
) -> TaskService:
    return TaskService(storage_repo=storage_repo, task_repo=task_repo)
