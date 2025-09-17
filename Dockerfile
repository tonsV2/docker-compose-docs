FROM python:3.12-slim

RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

WORKDIR /app
COPY ./main.py .

ENTRYPOINT ["uv", "run", "main.py"]
