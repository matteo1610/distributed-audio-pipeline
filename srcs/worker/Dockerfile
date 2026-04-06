FROM python:3.12.13-slim-bookworm

WORKDIR /app

ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY worker/pyproject.toml ./pyproject.toml
RUN poetry install --only main --no-root

COPY app ./app
COPY worker/worker.py ./worker.py

CMD ["python", "worker.py"]
