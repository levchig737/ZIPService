import zipfile
import io
import json
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile, HTTPException, BackgroundTasks

from task.enums import TaskStatus
from task.models import Task
from task.repositories import StorageRepository, TaskRepository
from task.schemas import TaskResultResponse, TaskResponse


class TaskService:
    def __init__(self, storage_repo: StorageRepository, task_repo: TaskRepository):
        self.task_repo = task_repo
        self.storage_repo = storage_repo

    async def create_task(self, task_id: str, file: UploadFile) -> None:
        # Читаем содержимое файла один раз
        file_content = await file.read()

        # Проверка целостности ZIP
        try:
            with zipfile.ZipFile(io.BytesIO(file_content), "r") as zip_ref:
                if zip_ref.testzip() is not None:
                    raise ValueError("Invalid ZIP file")
        except zipfile.BadZipFile as e:
            raise ValueError(f"File is not a valid ZIP file: {str(e)}")

        # Сохранение файла в MinIO через StorageRepository
        file_name = f"{task_id}.zip"
        await file.seek(0)  # Сбрасываем курсор в начало
        file.file.write(file_content)  # Восстанавливаем содержимое для save_file
        await self.storage_repo.save_file(file, file_name)

        # Создание задачи в базе данных
        task = Task(task_id=task_id, file_path=file_name, status=TaskStatus.PENDING)
        await self.task_repo.create(task)

    async def process_task(self, task_id: str) -> None:
        # Обновление статуса на IN_PROGRESS
        task = await self.task_repo.get(task_id)
        if not task:
            return
        task.status = TaskStatus.IN_PROGRESS
        await self.task_repo.update(task)

        # Симуляция анализа через SonarQube (dummy data)
        results = {
            "sonarqube": {
                "overall_coverage": 85.5,
                "bugs": {
                    "total": 12,
                    "critical": 2,
                    "major": 5,
                    "minor": 5
                },
                "code_smells": {
                    "total": 20,
                    "critical": 3,
                    "major": 10,
                    "minor": 7
                },
                "vulnerabilities": {
                    "total": 4,
                    "critical": 1,
                    "major": 2,
                    "minor": 1
                }
            }
        }

        # Сохранение результатов
        task.results = json.dumps(results)
        task.status = TaskStatus.SUCCESS
        await self.task_repo.update(task)

    async def get_task_result(self, task_id: str) -> Optional[TaskResultResponse]:
        task = await self.task_repo.get(task_id)
        if not task:
            return None
        return TaskResultResponse(
            status=task.status,
            results=json.loads(task.results) if task.results else None
        )

    async def upload_and_process_file(
            self, file: UploadFile,
            background_tasks: BackgroundTasks = None) -> TaskResponse:
        # Проверка расширения файла
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

        # Генерация уникального task_id
        task_id = str(uuid4())

        # Создание задачи
        await self.create_task(task_id, file)

        # Запуск фоновой обработки
        if background_tasks:
            background_tasks.add_task(self.process_task, task_id)

        return TaskResponse(task_id=task_id)