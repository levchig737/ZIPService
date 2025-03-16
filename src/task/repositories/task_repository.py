from typing_extensions import Optional

from base.base_repository import BaseRepository
from logging import getLogger
from sqlalchemy import select

from task.models import Task

logger = getLogger("api")


class TaskRepository(BaseRepository):
    async def create(self, task: Task) -> None:
        await self.save(task)

    async def get(self, task_id: str) -> Optional[Task]:
        statement = select(Task).where(task_id == Task.task_id)  # type: ignore
        return await self.one_or_none(statement)

    async def update(self, task: Task) -> None:
        await self.save(task)

    async def delete(self, task: Task) -> None:
        await self.remove(task)
