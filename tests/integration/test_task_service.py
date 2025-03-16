import io
import logging
import os
import zipfile

import pytest
from alembic import command
from alembic.config import Config
from minio import Minio
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer

from task.exceptions import (
    InvalidFileException,
    FileSizeExceededException,
    ZipValidationException,
    TaskNotFoundException,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# os.environ["TESTCONTAINERS_HOST_OVERRIDE"] = "127.0.0.1"


# Инициализация контейнеров
postgres = PostgresContainer(image="postgres:16.1", port=5432)

minio = MinioContainer(image="minio/minio:latest")

# -------------------- Фикстуры --------------------


@pytest.fixture(scope="session")
def event_loop():
    import asyncio

    """Переопределение стандартного цикла событий для pytest-asyncio."""
    policy = asyncio.WindowsProactorEventLoopPolicy()  # Для Windows
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_containers(request):
    """Запускает контейнеры PostgreSQL и MinIO перед тестами и останавливает их после."""
    logger.info("Starting Postgres container")
    postgres.start()
    db_connection_url = postgres.get_connection_url()
    logger.info(f"Postgres connection URL: {db_connection_url}")

    logger.info("Starting MinIO container")
    minio.start()
    wait_for_logs(minio, "MinIO Object Storage")

    # Установка переменных окружения
    os.environ["DB_CONN"] = db_connection_url
    os.environ["DB_HOST"] = postgres.get_container_host_ip()
    os.environ["DB_PORT"] = str(postgres.get_exposed_port(5432))
    os.environ["DB_USERNAME"] = postgres.username
    os.environ["DB_PASSWORD"] = postgres.password
    os.environ["DB_USER"] = postgres.username
    os.environ["DB_PASS"] = postgres.password
    os.environ["DB_NAME"] = postgres.dbname
    os.environ["POSTGRES_PASSWORD"] = postgres.password
    os.environ["MINIO_NAME"] = minio.get_container_host_ip()
    os.environ["MINIO_PORT"] = str(minio.get_exposed_port(9000))
    os.environ["MINIO_ACCESS_KEY"] = minio.access_key
    os.environ["MINIO_SECRET_KEY"] = minio.secret_key
    os.environ["SECRET"] = "test_secret"

    os.environ["KEYCLOAK_ADMIN"] = "test_admin"
    os.environ["KEYCLOAK_ADMIN_PASSWORD"] = "test_password"
    os.environ["KC_DB"] = "test_db"
    os.environ["KC_DB_URL"] = "test_db_url"
    os.environ["KC_DB_USERNAME"] = "test_username"
    os.environ["KC_DB_PASSWORD"] = "test_password"
    os.environ["KC_HOSTNAME"] = "test_hostname"
    os.environ["KC_PORT"] = "8080"
    os.environ["KEYCLOAK_SERVER_URL"] = "http://test_hostname:8080"
    os.environ["KEYCLOAK_REALM"] = "test_realm"
    os.environ["KEYCLOAK_CLIENT_ID"] = "test_client"
    os.environ["KEYCLOAK_REDIRECT_URI"] = "http://localhost:8000"
    os.environ["KEYCLOAK_CLIENT_SECRET"] = "test_secret"

    # Применение миграций Alembic
    alembic_ini_path = os.path.join(os.path.dirname(__file__), "../alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option(
        "script_location", os.path.join(os.path.dirname(alembic_ini_path), "alembic")
    )

    alembic_cfg.set_main_option("sqlalchemy.url", db_connection_url)
    command.upgrade(alembic_cfg, "head")

    # Создание бакета в MinIO
    minio_client = Minio(
        f"{minio.get_container_host_ip()}:{minio.get_exposed_port(9000)}",
        access_key=minio.access_key,
        secret_key=minio.secret_key,
        secure=False,
    )
    bucket_name = "zip-bucket"
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    def teardown_containers():
        """Останавливает контейнеры после тестов."""
        logger.info("Stopping Postgres container")
        postgres.stop()
        logger.info("Stopping MinIO container")
        minio.stop()

    request.addfinalizer(teardown_containers)


@pytest.fixture
async def client():
    from main import app
    from httpx import AsyncClient, ASGITransport
    from task.api.deps import get_current_user

    # Мок для get_current_user
    async def mock_get_current_user():
        return {
            "sub": "test_user_id",
            "preferred_username": "test_user",
            "email": "test@example.com",
        }

    # Переопределяем зависимость get_current_user в приложении
    app.dependency_overrides[get_current_user] = mock_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
        # Очищаем переопределение после теста
        app.dependency_overrides.clear()


# -------------------- Вспомогательные функции --------------------


def create_valid_zip_bytes() -> bytes:
    """Создаёт валидный ZIP-архив в памяти и возвращает его байты."""
    bytes_io = io.BytesIO()
    with zipfile.ZipFile(bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dummy.txt", "This is dummy text.")
    return bytes_io.getvalue()


# -------------------- Тесты --------------------


@pytest.mark.asyncio
async def test_upload_and_process_file_success(client):
    """Тестирует успешную загрузку и обработку ZIP-файла."""
    bytes_io = io.BytesIO(create_valid_zip_bytes())
    response = await client.post(
        "/upload", files={"file": ("test.zip", bytes_io, "application/zip")}
    )
    assert response.status_code == 201, (
        f"Ожидался код 201, получен {response.status_code}: {response.text}"
    )
    task_id = response.json()["task_id"]

    # Ожидание завершения фоновой задачи
    import asyncio

    for _ in range(10):
        await asyncio.sleep(1)
        result_response = await client.get(f"/results/{task_id}")
        if result_response.status_code == 200:
            data = result_response.json()
            if data["status"] == "SUCCESS":
                assert "results" in data, "Ожидалось поле 'results' в ответе"
                assert "sonarqube" in data["results"], (
                    "Ожидалось поле 'sonarqube' в результатах"
                )
                return
    pytest.fail("Задача не завершилась в течение 10 секунд")


@pytest.mark.asyncio
async def test_upload_invalid_extension(client):
    """Тестирует загрузку файла с недопустимым расширением."""
    bytes_io = io.BytesIO(b"not a zip")
    with pytest.raises(InvalidFileException):
        response = await client.post(
            "/upload", files={"file": ("test.txt", bytes_io, "text/plain")}
        )
        assert response.status_code == InvalidFileException.status_code, (
            f"Ожидался код {InvalidFileException.status_code}, получен {response.status_code}: {response.text}"
        )


@pytest.mark.asyncio
async def test_upload_file_size_exceeded(client):
    """Тестирует загрузку файла, превышающего максимальный размер."""
    from unittest.mock import patch

    with patch("task.services.task_service.TaskService.MAX_FILE_SIZE", 100):
        bytes_io = io.BytesIO(b"a" * 101)
        with pytest.raises(FileSizeExceededException):
            response = await client.post(
                "/upload", files={"file": ("test.zip", bytes_io, "application/zip")}
            )
            assert response.status_code == FileSizeExceededException.status_code, (
                f"Ожидался код {FileSizeExceededException.status_code}, получен {response.status_code}: {response.text}"
            )


@pytest.mark.asyncio
async def test_upload_invalid_zip(client):
    """Тестирует загрузку некорректного ZIP-архива."""
    bytes_io = io.BytesIO(b"not a valid zip")
    with pytest.raises(ZipValidationException):
        response = await client.post(
            "/upload", files={"file": ("test.zip", bytes_io, "application/zip")}
        )
        assert response.status_code == ZipValidationException.status_code, (
            f"Ожидался код {ZipValidationException.status_code}, получен {response.status_code}: {response.text}"
        )


@pytest.mark.asyncio
async def test_get_results_not_found(client):
    """Тестирует запрос результатов для несуществующей задачи."""
    with pytest.raises(TaskNotFoundException):
        response = await client.get("/results/nonexistent")
        assert response.status_code == TaskNotFoundException.status_code, (
            f"Ожидался код {TaskNotFoundException.status_code}, получен {response.status_code}: {response.text}"
        )


@pytest.mark.asyncio
async def test_upload_and_check_status(client):
    """Тестирует запрос результатов для несуществующей задачи."""
    with pytest.raises(TaskNotFoundException):
        response = await client.get("/results/nonexistent")
        assert response.status_code == TaskNotFoundException.status_code, (
            f"Ожидался код {TaskNotFoundException.status_code}, получен {response.status_code}: {response.text}"
        )
