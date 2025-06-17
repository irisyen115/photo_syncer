FROM python:3.10-slim

WORKDIR /app

COPY . /app

# 安裝需要的套件
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update ; apt install -y vim curl

# 設定 PYTHONPATH
ENV PYTHONPATH=/app

# 啟動指令
CMD ["python", "app.py"]
