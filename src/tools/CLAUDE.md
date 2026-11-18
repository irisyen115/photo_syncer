# src/tools/ — 排程/維運腳本

獨立 Python 腳本（無 `main()`，import 即執行），在容器內以 `PYTHONPATH=/app` 跑：
`docker exec google-photos python3 /app/tools/<script>.py`。由 `script/` 下的 wrapper 透過 NAS cron 觸發。

| 腳本 | 作用 |
|---|---|
| `get_cred.py` | 執行 Google OAuth 流程，產生 `/app/token.pickle`（首次部署或 token 失效時手動跑，需 `-it`） |
| `photo_sync.py` | 全量：對 Synology 前 8 位人物抓全部照片寫入 `photos` / `person_photos` |
| `photo_sync_from_previous.py` | 增量：先以 DB 中最新照片更新 `sync_status`，再呼叫 `sync_photos_since_last_time` |
| `photo_sync_from_last_week.py` / `photo_sync_from_last_month.py` | 依區間（7 天 / 1 個月）呼叫 `autonomy_get_interval_time_person` 重抓 |

共通點：都用 `os.getenv("SYNO_*")` 登入、`list_people(auth, 8)` 只處理**前 8 位**人物（依名稱排序）。

注意：
- 區間腳本會刪掉該人物在 `person_photos` 的全部紀錄後只寫回區間內照片（見 `src/CLAUDE.md` 已知問題）。
- 增量同步只會處理已有 `sync_status` 的人物（也就是 DB 裡已有照片的人物）；新人物要先跑 `photo_sync.py`。
