import os
import io
import zipfile
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Tuple, Optional
from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

# Импорт исключений и классов схем
from task.exceptions import (
    FileSizeExceededException,
    ZipValidationException,
    ProcessingException,
    InvalidFileException,
)
from task.enums import TaskStatus
from task.schemas import TaskResponse

# Установка переменных окружения ДО импорта модулей
os.environ["DB_HOST"] = "test_host"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "test_db"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASS"] = "test_pass"
os.environ["POSTGRES_PASSWORD"] = "test_postgres_password"
os.environ["MINIO_NAME"] = "test_minio"
os.environ["MINIO_PORT"] = "9000"
os.environ["MINIO_ACCESS_KEY"] = "test_access_key"
os.environ["MINIO_SECRET_KEY"] = "test_secret_key"
os.environ["SECRET"] = "test_secret"

from task.services.task_service import TaskService


def create_valid_zip_bytes() -> bytes:
    """Создает валидный ZIP-архив в памяти и возвращает его байты."""
    bytes_io = io.BytesIO()
    with zipfile.ZipFile(bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dummy.txt", "This is dummy text.")
    return bytes_io.getvalue()


# -------------------- Фикстуры --------------------


@pytest.fixture
def task_service() -> Tuple[TaskService, MagicMock, MagicMock]:
    storage_repo = MagicMock()
    task_repo = MagicMock()
    service = TaskService(storage_repo, task_repo)
    return service, storage_repo, task_repo


@pytest.fixture
def valid_file() -> MagicMock:
    file = MagicMock(spec=UploadFile)
    file.size = 1024
    file.read = AsyncMock(return_value=create_valid_zip_bytes())
    file.seek = AsyncMock(return_value=None)
    file.file = MagicMock()
    return file


@pytest.fixture
def valid_upload_file(valid_file) -> MagicMock:
    valid_file.filename = "test.zip"
    return valid_file


@pytest.fixture
def invalid_zip_file() -> MagicMock:
    file = MagicMock(spec=UploadFile)
    file.size = 1024
    file.read = AsyncMock(return_value=b"not a valid zip content")
    file.seek = AsyncMock(return_value=None)
    file.file = MagicMock()
    file.filename = "test.zip"
    return file


@pytest.fixture
def big_file() -> MagicMock:
    file = MagicMock(spec=UploadFile)
    file.size = TaskService.MAX_FILE_SIZE + 1
    file.read = AsyncMock(return_value=create_valid_zip_bytes())
    file.seek = AsyncMock(return_value=None)
    file.file = MagicMock()
    file.filename = "test.zip"
    return file


@pytest.fixture
def invalid_extension_file(valid_file) -> MagicMock:
    valid_file.filename = "test.txt"
    return valid_file


class DummyTask:
    def __init__(
        self,
        task_id: str,
        status: TaskStatus = TaskStatus.PENDING,
        results: Optional[str] = None,
    ):
        self.task_id: str = task_id
        self.status: TaskStatus = status
        self.results: Optional[str] = results


# -------------------- Тесты для create_task --------------------


@pytest.mark.asyncio
async def test_create_task_success(
    task_service: Tuple[TaskService, MagicMock, MagicMock], valid_file: MagicMock
) -> None:
    service, storage_repo, task_repo = task_service
    storage_repo.save_file = AsyncMock()
    task_repo.create = AsyncMock()

    await service.create_task("test_id", valid_file, MagicMock(spec=AsyncSession))

    storage_repo.save_file.assert_called_once_with(valid_file, "test_id.zip")
    task_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_file_size_exceeded(
    task_service: Tuple[TaskService, MagicMock, MagicMock], big_file: MagicMock
) -> None:
    service, _, _ = task_service
    with pytest.raises(FileSizeExceededException):
        await service.create_task("test_id", big_file, MagicMock(spec=AsyncSession))


@pytest.mark.asyncio
async def test_create_task_invalid_zip(
    task_service: Tuple[TaskService, MagicMock, MagicMock], invalid_zip_file: MagicMock
) -> None:
    service, _, _ = task_service
    with pytest.raises(ZipValidationException):
        await service.create_task(
            "test_id", invalid_zip_file, MagicMock(spec=AsyncSession)
        )


@pytest.mark.asyncio
async def test_create_task_storage_failure(
    task_service: Tuple[TaskService, MagicMock, MagicMock], valid_file: MagicMock
) -> None:
    service, storage_repo, task_repo = task_service
    storage_repo.save_file = AsyncMock(side_effect=Exception("Storage error"))
    task_repo.create = AsyncMock()

    with pytest.raises(ProcessingException):
        await service.create_task("test_id", valid_file, MagicMock(spec=AsyncSession))


@pytest.mark.asyncio
async def test_create_task_db_failure(
    task_service: Tuple[TaskService, MagicMock, MagicMock], valid_file: MagicMock
) -> None:
    service, storage_repo, task_repo = task_service
    storage_repo.save_file = AsyncMock()
    task_repo.create = AsyncMock(side_effect=Exception("DB error"))

    with pytest.raises(ProcessingException):
        await service.create_task("test_id", valid_file, MagicMock(spec=AsyncSession))


# -------------------- Тесты для process_task --------------------


@pytest.mark.asyncio
async def test_process_task_no_task_found(
    task_service: Tuple[TaskService, MagicMock, MagicMock],
) -> None:
    service, _, task_repo = task_service
    task_repo.get = AsyncMock(return_value=None)
    result = await service.process_task("nonexistent", MagicMock(spec=AsyncSession))
    task_repo.get.assert_called_once_with("nonexistent")
    if hasattr(task_repo, "update"):
        task_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_process_task_success(
    task_service: Tuple[TaskService, MagicMock, MagicMock],
) -> None:
    service, _, task_repo = task_service
    dummy_task = DummyTask("test_id")
    task_repo.get = AsyncMock(return_value=dummy_task)
    task_repo.update = AsyncMock()

    await service.process_task("test_id", MagicMock(spec=AsyncSession))

    assert task_repo.update.call_count == 2
    assert dummy_task.status == TaskStatus.SUCCESS
    assert dummy_task.results is not None
    results = json.loads(dummy_task.results)
    assert "sonarqube" in results


@pytest.mark.asyncio
async def test_process_task_update_failure(
    task_service: Tuple[TaskService, MagicMock, MagicMock],
) -> None:
    service, _, task_repo = task_service
    dummy_task = DummyTask("test_id")
    task_repo.get = AsyncMock(return_value=dummy_task)
    task_repo.update = AsyncMock(side_effect=Exception("Update error"))

    with pytest.raises(ProcessingException):
        await service.process_task("test_id", MagicMock(spec=AsyncSession))


# -------------------- Тесты для upload_and_process_file --------------------


@pytest.mark.asyncio
async def test_upload_and_process_file_success(
    task_service: Tuple[TaskService, MagicMock, MagicMock], valid_upload_file: MagicMock
) -> None:
    service, _, _ = task_service
    service.create_task = AsyncMock()
    background_tasks = MagicMock(spec=BackgroundTasks)
    session = MagicMock(spec=AsyncSession)

    response = await service.upload_and_process_file(
        valid_upload_file, background_tasks, session
    )

    assert isinstance(response, TaskResponse)
    assert response.task_id is not None
    background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_upload_and_process_file_invalid_extension(
    task_service: Tuple[TaskService, MagicMock, MagicMock], valid_file: MagicMock
) -> None:
    service, _, _ = task_service
    valid_file.filename = "invalid.txt"
    background_tasks = MagicMock(spec=BackgroundTasks)
    session = MagicMock(spec=AsyncSession)
    with pytest.raises(InvalidFileException):
        await service.upload_and_process_file(valid_file, background_tasks, session)


@pytest.mark.asyncio
async def test_upload_and_process_file_file_size_exceeded(
    task_service: Tuple[TaskService, MagicMock, MagicMock], big_file: MagicMock
) -> None:
    service, _, _ = task_service
    background_tasks = MagicMock(spec=BackgroundTasks)
    session = MagicMock(spec=AsyncSession)
    with pytest.raises(FileSizeExceededException):
        await service.upload_and_process_file(big_file, background_tasks, session)
