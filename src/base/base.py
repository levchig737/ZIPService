from typing import AsyncGenerator

from fastapi import Depends

from settings import Settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

settings = Settings()
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)


engine = create_async_engine(
    DATABASE_URL,
    max_overflow=10,
    pool_pre_ping=5,
    pool_recycle=-1,
    pool_size=5,
    pool_timeout=30,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
        await session.commit()


class Base(DeclarativeBase):
    __allow_unmapped__ = True
