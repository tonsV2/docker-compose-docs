FROM python:3.12-slim

# We lose caching benefits but can run as nobody (for an app of this size it doesn't matter)
ENV UV_NO_CACHE=1

RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

WORKDIR /app
COPY ./main.py .

USER nobody

ENTRYPOINT ["uv", "run", "main.py"]
