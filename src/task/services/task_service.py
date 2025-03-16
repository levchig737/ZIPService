import zipfile
import io
import logging
import json  # Импортируем json для преобразования
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile, BackgroundTasks
from fastapi_cache import FastAPICache
from sqlalchemy.ext.asyncio import AsyncSession

from base.base import async_session
from gateways.sonarqube import CheckResult, SonarQubeResults
from gateways.sonarqube.sonarqube import SonarqubeService
from task.enums import TaskStatus
from task.exceptions import (
    FileSizeExceededException,
    ZipValidationException,
    ProcessingException,
    TaskNotFoundException,
    InvalidFileException,
)
from task.models import Task
from task.repositories import StorageRepository, TaskRepository
from task.schemas import TaskResultResponse, TaskResponse

logger = logging.getLogger("api")


class TaskService:
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(
        self,
        storage_repo: StorageRepository,
        task_repo: TaskRepository,
        sonarqube_service: SonarqubeService,
    ):
        self.task_repo = task_repo
        self.storage_repo = storage_repo
        self.sonarqube_service = sonarqube_service
        self.cache_namespace = "TASK"

    async def create_task(
        self, task_id: str, file: UploadFile, session: Optional[AsyncSession] = None
    ) -> None:
        logger.info(f"Создание задачи с id: {task_id}")

        if session is not None:
            self.task_repo.session = session

        # Валидация размера файла
        file_size = file.size
        if file_size is None or file_size > self.MAX_FILE_SIZE:
            logger.error(
                f"Размер файла {file_size} превышает лимит {self.MAX_FILE_SIZE} байт"
            )
            raise FileSizeExceededException()

        file_content = await file.read()

        # Проверка целостности ZIP-файла
        try:
            with zipfile.ZipFile(io.BytesIO(file_content), "r") as zip_ref:
                if zip_ref.testzip() is not None:
                    logger.error("ZIP-архив недействителен")
                    raise ZipValidationException()
        except zipfile.BadZipFile as e:
            logger.error(f"Ошибка валидации ZIP: {str(e)}")
            raise ZipValidationException(
                message=f"Ошибка валидации ZIP-архива: {str(e)}"
            )

        # Сохранение файла в MinIO
        file_name = f"{task_id}.zip"
        await file.seek(0)
        file.file.write(file_content)
        try:
            await self.storage_repo.save_file(file, file_name)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла в MinIO: {str(e)}")
            raise ProcessingException(message=f"Ошибка при сохранении файла: {str(e)}")
        logger.info(f"Файл {file_name} сохранён в MinIO")

        # Создание задачи в базе данных
        task = Task(task_id=task_id, file_path=file_name, status=TaskStatus.PENDING)
        try:
            await self.task_repo.create(task)
        except Exception as e:
            logger.error(f"Ошибка создания задачи в базе данных: {str(e)}")
            raise ProcessingException(message=f"Ошибка создания задачи: {str(e)}")
        logger.info(
            f"Задача {task_id} создана в базе данных со статусом: {task.status}"
        )

    async def process_task(
        self, task_id: str, session: Optional[AsyncSession] = None
    ) -> None:
        if session is not None:
            self.task_repo.session = session

        task = await self.task_repo.get(task_id)
        if not task:
            logger.error(f"Задача {task_id} не найдена")
            return

        # Обновление статуса на IN_PROGRESS
        task.status = TaskStatus.IN_PROGRESS  # type: ignore[assignment]

        await FastAPICache.clear(namespace=self.cache_namespace)

        try:
            await self.task_repo.update(task)
        except Exception as e:
            logger.error(f"Ошибка обновления статуса задачи: {str(e)}")
            raise ProcessingException(message=f"Ошибка обновления статуса: {str(e)}")
        logger.info(f"Статус задачи {task_id} обновлён до IN_PROGRESS")

        # Получение содержимого ZIP-файла из MinIO
        try:
            file_content = await self.storage_repo.get_file(
                f"{task_id}.zip"
            )  # file_content уже bytes
        except Exception as e:
            logger.error(f"Ошибка получения файла из MinIO: {str(e)}")
            raise ProcessingException(message=f"Ошибка получения файла: {str(e)}")

        # Вызов SonarqubeService для анализа
        try:
            results = await self.sonarqube_service.check_zip(file_content)
        except Exception as e:
            logger.error(f"Ошибка анализа SonarQube: {str(e)}")
            raise ProcessingException(message=f"Ошибка анализа SonarQube: {str(e)}")

        # Сохранение результатов
        task.results = json.dumps(results.dict())  # type: ignore[assignment]
        task.status = TaskStatus.SUCCESS  # type: ignore[assignment]
        await FastAPICache.clear(namespace=self.cache_namespace)

        try:
            await self.task_repo.update(task)
        except Exception as e:
            logger.error(f"Ошибка сохранения результатов: {str(e)}")
            raise ProcessingException(
                message=f"Ошибка сохранения результатов: {str(e)}"
            )
        logger.info(
            f"Задача {task_id} обработана и обновлена до SUCCESS с результатами: {results}"
        )

    async def get_task_result(
        self, task_id: str, session: Optional[AsyncSession] = None
    ) -> Optional[TaskResultResponse]:
        logger.info(f"Получение результата для task_id: {task_id}")

        if session is not None:
            self.task_repo.session = session

        task = await self.task_repo.get(task_id)
        if not task:
            logger.error(f"Задача {task_id} не найдена")
            raise TaskNotFoundException()

        if task.results:
            try:
                # Преобразуем строку из базы обратно в словарь, затем в Pydantic-модель
                results_data = json.loads(
                    str(task.results)
                )  # Преобразуем строку в словарь
                sonarqube_results = results_data.get("sonarqube", {})
                check_result = (
                    CheckResult(**sonarqube_results) if sonarqube_results else None
                )
                results = (
                    SonarQubeResults(sonarqube=check_result) if check_result else None
                )
            except Exception as e:
                logger.error(f"Ошибка обработки результатов: {str(e)}")
                raise ProcessingException(
                    message=f"Ошибка обработки результатов: {str(e)}"
                )
        else:
            results = None

        return TaskResultResponse(status=task.status, results=results)  # type: ignore

    async def upload_and_process_file(
        self, file: UploadFile, background_tasks: BackgroundTasks, session: AsyncSession
    ) -> TaskResponse:
        logger.info("Начало upload_and_process_file")

        # Валидация расширения файла
        if not file.filename or not file.filename.lower().endswith(".zip"):
            logger.error(f"Недопустимое расширение файла: {file.filename}")
            raise InvalidFileException()

        # Валидация размера файла
        file_size = file.size
        if file_size is None or file_size > self.MAX_FILE_SIZE:
            logger.error(
                f"Размер файла {file_size} превышает лимит {self.MAX_FILE_SIZE} байт"
            )
            raise FileSizeExceededException()

        # Генерация уникального task_id
        task_id = str(uuid4())

        # Создание задачи
        await self.create_task(task_id, file, session)

        # Запуск фоновой обработки
        async def wrapped_process_task(task_id_wrap: str):
            async with async_session() as new_session:
                try:
                    await self.process_task(task_id_wrap, new_session)
                    await new_session.commit()
                except Exception as e:
                    logger.error(
                        f"Ошибка в фоновой задаче для {task_id_wrap}: {str(e)}"
                    )
                    await new_session.rollback()
                    raise ProcessingException(
                        message=f"Ошибка обработки задачи: {str(e)}"
                    )

        background_tasks.add_task(wrapped_process_task, task_id)
        logger.info(f"Фоновая задача добавлена для {task_id}")

        return TaskResponse(task_id=task_id)
