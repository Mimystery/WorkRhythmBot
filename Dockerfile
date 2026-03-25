FROM python:3.14-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

COPY . .

CMD ["python", "start.py"]
