import abc
from typing import Any, Generic, Iterable, Optional, TypeVar

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import Delete, Insert, Select, Update
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(abc.ABC, Generic[T]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def all(self, statement: Select | Delete | Update | Insert) -> Iterable[Any]:
        return (await self.session.execute(statement)).scalars().all()

    async def paginate(self, statement: Select, **kwargs: Any) -> Page:
        return await paginate(self.session, statement, **kwargs)

    async def one_or_none(
        self, statement: Select | Delete | Update | Insert
    ) -> Optional[Any]:
        return (await self.session.execute(statement)).scalars().one_or_none()

    async def save(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remove(self, obj: T) -> None:
        return await self.session.delete(obj)
