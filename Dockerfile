FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir poetry uvicorn
COPY pyproject.toml poetry.lock /app/
# Install dependency globally in container
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi
COPY . .

EXPOSE ${APP_PORT}
CMD ["sh", "-c", "python3 -m uvicorn src.app:app --host 0.0.0.0 --port ${APP_PORT}"]


