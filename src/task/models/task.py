from sqlalchemy import String, Enum
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from base import Base
from task.enums import TaskStatus


class Task(Base):
    __tablename__ = "tasks"
    task_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )  # UUID в виде строки
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=True
    )
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    results: Mapped[Optional[str]] = mapped_column(String, nullable=True)
