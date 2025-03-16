FROM python:3.12

RUN mkdir /src

WORKDIR /src

COPY poetry.lock* pyproject.toml ./
COPY pytest.ini ./

RUN pip install --upgrade pip
RUN pip install poetry
RUN poetry config virtualenvs.create false # чтобы ставилось в корень
RUN poetry install --no-root

COPY ./src/. /src/.
