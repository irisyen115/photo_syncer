FROM python:3.11-slim

WORKDIR /app

COPY src/tools/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN apt update && apt install -y vim curl && \
    apt clean && rm -rf /var/lib/apt/lists/*

COPY src/ .

ENV PYTHONPATH=/app

CMD ["python", "app.py"]
