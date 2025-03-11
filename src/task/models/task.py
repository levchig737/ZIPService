from sqlalchemy import Column, String, Enum
import uuid

from base import Base
from task.enums.TaskStatus import TaskStatus


class Task(Base):
    __tablename__ = "tasks"
    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)  # UUID в виде строки
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    file_path = Column(String)
    results = Column(String)