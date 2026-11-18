# script/ — NAS 主機 cron wrapper

在 Synology NAS 主機（非容器內）由 cron 執行，用 `docker exec` 呼叫容器內的 `src/tools/` 腳本，輸出附加到 `/var/log/myscriptN.log`。此目錄也被掛載到容器的 `/app/script`。

| Wrapper | 呼叫 | Log |
|---|---|---|
| `wrapper_all_photo_sync.sh` | `tools/photo_sync.py` | `/var/log/myscript.log` |
| `wrapper_photo_sync_from_previous.sh` | `tools/photo_sync_from_previous.py`，並寫 Prometheus 指標 | `/var/log/myscript3.log` |
| `wrapper_photo_sync_from_last_week.sh` | `tools/photo_sync_from_last_week.py` | `/var/log/myscript4.log` |
| `wrapper_photo_sync_from_last_month.sh` | `tools/photo_sync_from_last_month.py` | `/var/log/myscript5.log` |
| `wrapper_line.sh` | `line-reply` 容器的 `webhook_service.py`（該服務已拆到另一個 repo） | `/var/log/myscript2.log` |

## 監控指標

`wrapper_photo_sync_from_previous.sh` 執行後覆寫 `/volume1/src/photo_syncer/textfile/photo_sync.prom`（= repo 的 `textfile/`），由 node-exporter textfile collector 提供：
`photo_sync_last_run_timestamp_seconds`、`photo_sync_last_run_duration_seconds`、`photo_sync_last_run_success`（docker exec 的 exit code 為 0 則 1）。
