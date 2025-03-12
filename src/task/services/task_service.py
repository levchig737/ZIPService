import zipfile
import io
import logging
import json
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from base.base import async_session
from task.enums import TaskStatus
from task.models import Task
from task.repositories import StorageRepository, TaskRepository
from task.schemas import TaskResultResponse, TaskResponse, CheckResult, SonarQubeResults

logger = logging.getLogger("api")

class TaskService:
    def __init__(self, storage_repo: StorageRepository, task_repo: TaskRepository):
        self.task_repo = task_repo
        self.storage_repo = storage_repo

    async def create_task(self, task_id: str, file: UploadFile, session: AsyncSession) -> None:
        logger.info(f"Создание задачи с id: {task_id}")

        file_content = await file.read()

        # Проверка целостности ZIP-файла
        try:
            with zipfile.ZipFile(io.BytesIO(file_content), "r") as zip_ref:
                if zip_ref.testzip() is not None:
                    raise ValueError("Недействительный ZIP-файл")
        except zipfile.BadZipFile as e:
            logger.error(f"Ошибка валидации ZIP: {str(e)}")
            raise ValueError(f"Файл не является валидным ZIP-файлом: {str(e)}")

        # Сохранение файла в MinIO
        file_name = f"{task_id}.zip"
        await file.seek(0)
        file.file.write(file_content)
        await self.storage_repo.save_file(file, file_name)
        logger.info(f"Файл {file_name} сохранён в MinIO")

        # Создание задачи в базе данных
        task = Task(task_id=task_id, file_path=file_name, status=TaskStatus.PENDING)
        self.task_repo.session = session
        await self.task_repo.create(task)
        logger.info(f"Задача {task_id} создана в базе данных со статусом: {task.status}")

    async def process_task(self, task_id: str, session: AsyncSession) -> None:
        logger.info(f"Начало process_task для task_id: {task_id}")
        task_repo = TaskRepository(session)
        task = await task_repo.get(task_id)
        if not task:
            logger.error(f"Задача {task_id} не найдена")
            return

        # Обновление статуса на IN_PROGRESS
        task.status = TaskStatus.IN_PROGRESS
        await task_repo.update(task)
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
        await task_repo.update(task)
        logger.info(f"Задача {task_id} обработана и обновлена до SUCCESS с результатами: {results}")

    async def get_task_result(self, task_id: str, session: AsyncSession) -> Optional[TaskResultResponse]:
        logger.info(f"Получение результата для task_id: {task_id}")
        task_repo = TaskRepository(session)
        task = await task_repo.get(task_id)
        if not task:
            return None

        if task.results:
            results_data = json.loads(task.results)
            # Извлекаем данные из 'sonarqube' и создаём объект CheckResult
            sonarqube_results = results_data.get('sonarqube', {})
            check_result = CheckResult(**sonarqube_results) if sonarqube_results else None
            results = SonarQubeResults(sonarqube=check_result) if check_result else None
        else:
            results = None

        return TaskResultResponse(status=task.status, results=results)

    async def upload_and_process_file(
            self, file: UploadFile,
            background_tasks: BackgroundTasks,
            session: AsyncSession) -> TaskResponse:
        logger.info("Начало upload_and_process_file")

        # Проверка расширения файла
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Разрешены только ZIP-файлы")

        # Генерация уникального task_id
        task_id = str(uuid4())

        # Создание задачи
        await self.create_task(task_id, file, session)

        # Запуск фоновой обработки
        if background_tasks:
            async def wrapped_process_task(task_id: str):
                async with async_session() as new_session:
                    await self.process_task(task_id, new_session)
                    await new_session.commit()
            background_tasks.add_task(wrapped_process_task, task_id)
            logger.info(f"Фоновая задача добавлена для {task_id}")

        return TaskResponse(task_id=task_id)