# ZIP Service
## Описание проекта

**ZIP Service** — это микросервис для проверки содержимого ZIP-архивов с использованием запросов к сторонним системам и получения набора характеристик файла.
---

## Основные функции

- Прием ZIP-архива от пользователя 
- Проверка целостности архива 
- Выполнение запросов к сторонним системам для получения характеристик (условно считаем что у нас таких систем 3)
- Агрегация и возврат результатов проверки

---

## Основные технологии проекта
- **Python 3.12** – основа проекта, предоставляет современные возможности языка.  
- **FastAPI** – асинхронный веб-фреймворк для создания API с высокой производительностью.  
- **Pydantic Settings** – управление конфигурацией приложения через Pydantic.  
- **SQLAlchemy** – ORM для работы с реляционными базами данных.  
- **Alembic** – инструмент миграций базы данных для SQLAlchemy.  
- **Asyncpg** – асинхронный драйвер для PostgreSQL.  
- **Uvicorn** – ASGI-сервер для запуска FastAPI-приложения.  
- **Minio** – клиент для работы с объектным хранилищем MinIO.  
- **Python-Multipart** – обработка multipart-запросов (например, загрузка файлов).  
- **Ruff** – статический анализатор кода для поддержания качества.  
- **Pytest** – тестовый фреймворк для автоматизированного тестирования.  
- **Pytest-Asyncio** – поддержка асинхронных тестов в Pytest.  
- **Testcontainers** – тест контейнеры в тестах.  
- **Psycopg2-binary** – синхронный PostgreSQL-драйвер (используется для совместимости).  
- **Python-Keycloak** – взаимодействие с Keycloak для аутентификации.  
- **FastAPI-Cache2 (Redis)** – кэширование данных в Redis для оптимизации API. 

--- 

## Инструкция по развертыванию:
### Запуск в докере
1. Клонируйте репозиторий

```shell
git clone https://github.com/levchig737/ZIPService.git && cd ZIPService
```

2. Запуск в контейнере

```shell
docker-compose up -d
```


### Локальный запуск
1. Клонируйте репозиторий

```shell
git clone https://github.com/levchig737/ZIPService.git 
cd ZIPService
```

2. Скопируйте настройки окружения из **.env-local** в **.env**

3. Запуск в контейнере

```shell
docker-compose up -d db minio keycloak redis
```

4. Установите зависимости

```shell
python.exe -m pip install --upgrade pip
pip install poetry
poetry update
```

5. Запуск приложения

```shell
cd src
alembic upgrade head  
python main.py
```

### Swagger
Доступ по ссылке: http://localhost:8000/docs


### Аутентификация в Keycloak Swagger
Для аутентификации в Swagger необходимо вставить из **.env** **KEYCLOAK_CLIENT_ID** и **KEYCLOAK_CLIENT_SECRET** в соответствующие поля

**Тестовый пользователь:**
- login: test
- password: test


## Локальный запуск тестов
```shell
pytest .\tests\integration
pytest .\tests\unit
```