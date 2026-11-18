"""k8s CronJob 用的 tools 腳本包裝器。

用法：python run_tool.py tools/photo_sync.py [args...]

- log 輸出到 stdout（kubectl logs 可看），不寫 error.log
- 腳本拋例外或以非 0 結束時，若有設定 TG_URL 就發 Telegram 通知，並以非 0 結束讓 Job 標記失敗
- TG_NOTIFY_SUCCESS=1 時，成功也會發一則靜音通知
"""
import logging
import os
import runpy
import sys
import time
import traceback

logging.basicConfig(
    stream=sys.stdout,
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    force=True,
)


def notify(message, silent):
    url = os.getenv("TG_URL")
    if not url:
        return
    try:
        import requests
        requests.post(url, json={"message": message, "silent": silent}, timeout=10)
    except Exception as e:  # 通知失敗不影響 Job 結果
        logging.warning("Telegram 通知失敗: %s", e)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python run_tool.py <script.py> [args...]")
    script = sys.argv[1]
    job = os.getenv("JOB_NAME", os.path.basename(script))
    sys.argv = sys.argv[1:]
    started = time.time()
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as e:
        if e.code not in (0, None):
            notify(f"❌ photo-syncer `{job}` 失敗（exit {e.code}）", silent=False)
        raise
    except Exception as e:
        traceback.print_exc()
        notify(f"❌ photo-syncer `{job}` 失敗：{type(e).__name__}: {e}"[:3500], silent=False)
        sys.exit(1)
    elapsed = round(time.time() - started)
    logging.info("%s 完成，耗時 %ss", job, elapsed)
    if os.getenv("TG_NOTIFY_SUCCESS") == "1":
        notify(f"✅ photo-syncer `{job}` 完成（{elapsed}s）", silent=True)


if __name__ == "__main__":
    main()
