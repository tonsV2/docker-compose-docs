FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ /app/src/

RUN pip install --no-cache-dir .

USER nobody

ENTRYPOINT ["python", "-m", "src.cli"]
