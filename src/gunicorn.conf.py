# gunicorn 設定（k8s 用：`gunicorn -c gunicorn.conf.py app:app`）。
# NAS 的 docker-compose 仍用 `python app.py`，不受影響。
import logging
import os
import sys

bind = f"0.0.0.0:{os.getenv('PORT', '5050')}"
# 一定要單一 worker：背景上傳 thread 與 face_cache 都在 process 記憶體內
workers = 1
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "8"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "300"))
accesslog = "-"
# 只記 path、不記 query string：line-reply 的請求帶 ?token=（LINE 使用者的 session handle）
access_log_format = '%(h)s %(t)s "%(m)s %(U)s" %(s)s %(b)s %(L)ss "%(a)s"'
errorlog = "-"

# 在 app import 前先把 root logger 指到 stdout；
# 各模組之後的 logging.basicConfig(filename="error.log") 因 root 已有 handler 而不會生效。
logging.basicConfig(
    stream=sys.stdout,
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
