FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt .

RUN apt update && apt install -y vim curl && \
    apt clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# 移除所有 __pycache__（可選）
RUN find . -type d -name "__pycache__" -exec rm -r {} + || true

COPY src/ .

ENV PYTHONPATH=/app

CMD ["python", "app.py"]
