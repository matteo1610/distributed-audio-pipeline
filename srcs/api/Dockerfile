FROM python:3.12-slim

WORKDIR /app

ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY pyproject.toml ./
RUN poetry install --only main --no-root

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
