FROM python:3.11-slim

WORKDIR /app
# Need gcc for psutil
RUN apt-get update 
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir poetry

COPY poetry.lock pyproject.toml /app/
COPY src/ /app/src/
COPY etc/ /app/etc/

# Install dependency globally in container
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

EXPOSE ${APP_PORT}
CMD ["sh", "-c", "python3 -m uvicorn src.app:app --host 0.0.0.0 --port ${APP_PORT}"]
