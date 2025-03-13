import zipfile
import io
import logging
import json
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from base.base import async_session
from task.enums import TaskStatus
from task.exceptions import FileSizeExceededException, ZipValidationException, ProcessingException, \
    TaskNotFoundException, InvalidFileException
from task.models import Task
from task.repositories import StorageRepository, TaskRepository
from task.schemas import TaskResultResponse, TaskResponse, CheckResult, SonarQubeResults

logger = logging.getLogger("api")

class TaskService:
    MAX_FILE_SIZE = 100 * 1024 * 1024
    def __init__(self, storage_repo: StorageRepository, task_repo: TaskRepository):
        self.task_repo = task_repo
        self.storage_repo = storage_repo

    async def create_task(self, task_id: str, file: UploadFile, session: AsyncSession = None) -> None:
        logger.info(f"Создание задачи с id: {task_id}")

        if session is not None:
            self.task_repo.session = session

        # Валидация размера файла
        file_size = file.size
        if file_size is None or file_size > self.MAX_FILE_SIZE:
            logger.error(f"Размер файла {file_size} превышает лимит {self.MAX_FILE_SIZE} байт")
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
            raise ZipValidationException(message=f"Ошибка валидации ZIP-архива: {str(e)}")

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
        logger.info(f"Задача {task_id} создана в базе данных со статусом: {task.status}")

    async def process_task(self, task_id: str, session: AsyncSession = None) -> None:
        if session is not None:
            self.task_repo.session = session

        task = await self.task_repo.get(task_id)
        if not task:
            logger.error(f"Задача {task_id} не найдена")
            return

        # Обновление статуса на IN_PROGRESS
        task.status = TaskStatus.IN_PROGRESS
        try:
            await self.task_repo.update(task)
        except Exception as e:
            logger.error(f"Ошибка обновления статуса задачи: {str(e)}")
            raise ProcessingException(message=f"Ошибка обновления статуса: {str(e)}")
        logger.info(f"Статус задачи {task_id} обновлён до IN_PROGRESS")

        # Симуляция анализа через SonarQube (фиктивные данные)
        results = {
            "sonarqube": {
                "overall_coverage": 85.5,
                "bugs": {"total": 12, "critical": 2, "major": 5, "minor": 5},
                "code_smells": {"total": 20, "critical": 3, "major": 10, "minor": 7},
                "vulnerabilities": {"total": 4, "critical": 1, "major": 2, "minor": 1}
            }
        }

        # Сохранение результатов
        task.results = json.dumps(results)
        task.status = TaskStatus.SUCCESS
        try:
            await self.task_repo.update(task)
        except Exception as e:
            logger.error(f"Ошибка сохранения результатов: {str(e)}")
            raise ProcessingException(message=f"Ошибка сохранения результатов: {str(e)}")
        logger.info(f"Задача {task_id} обработана и обновлена до SUCCESS с результатами: {results}")

    async def get_task_result(self, task_id: str, session: AsyncSession = None) -> Optional[TaskResultResponse]:
        logger.info(f"Получение результата для task_id: {task_id}")

        if session is not None:
            self.task_repo.session = session

        task = await self.task_repo.get(task_id)
        if not task:
            logger.error(f"Задача {task_id} не найдена")
            raise TaskNotFoundException()

        if task.results:
            try:
                results_data = json.loads(task.results)
                sonarqube_results = results_data.get('sonarqube', {})
                check_result = CheckResult(**sonarqube_results) if sonarqube_results else None
                results = SonarQubeResults(sonarqube=check_result) if check_result else None
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON: {str(e)}")
                raise ProcessingException(message=f"Ошибка обработки результатов: {str(e)}")
        else:
            results = None

        return TaskResultResponse(status=task.status, results=results)

    async def upload_and_process_file(
            self, file: UploadFile,
            background_tasks: BackgroundTasks,
            session: AsyncSession) -> TaskResponse:
        logger.info("Начало upload_and_process_file")

        # Валидация расширения файла
        if not file.filename or not file.filename.lower().endswith(".zip"):
            logger.error(f"Недопустимое расширение файла: {file.filename}")
            raise InvalidFileException()

        # Валидация размера файла
        file_size = file.size
        if file_size is None or file_size > self.MAX_FILE_SIZE:
            logger.error(f"Размер файла {file_size} превышает лимит {self.MAX_FILE_SIZE} байт")
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
                    logger.error(f"Ошибка в фоновой задаче для {task_id_wrap}: {str(e)}")
                    await new_session.rollback()
                    raise ProcessingException(message=f"Ошибка обработки задачи: {str(e)}")

        background_tasks.add_task(wrapped_process_task, task_id)
        logger.info(f"Фоновая задача добавлена для {task_id}")

        return TaskResponse(task_id=task_id)