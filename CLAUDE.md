# photo_syncer

把 **Synology Photos（NAS）** 上依「人臉/人物」分類的照片，同步到本地 PostgreSQL，並隨機挑選後上傳到 **Google Photos 相簿**。前端互動是 LINE bot（`line-reply` 服務，已拆到另一個 repo），本 repo 只負責後端 API 與排程同步。

## 目錄（各子目錄有自己的 CLAUDE.md）

| 路徑 | 內容 |
|---|---|
| `src/` | Flask app（容器 `google-photos`，port 5050）。controllers → service → lib/models 三層。見 `src/CLAUDE.md` |
| `src/tools/` | 排程用的獨立同步腳本（cron 透過 `docker exec` 執行）。見 `src/tools/CLAUDE.md` |
| `script/` | NAS 主機上的 cron wrapper + Prometheus textfile 指標。見 `script/CLAUDE.md` |
| `docker/` | `Dockerfile`（python:3.11-slim）與 `docker-compose.yml` |
| `configuration/` | `.env.template`、VS Code workspace |
| `textfile/` | `photo_sync.prom`，node-exporter textfile collector 讀取（由 script 產生，會被 commit 但內容是執行結果） |
| `README.md` | 只有 Google Cloud OAuth 用戶端設定教學 |

## 部署（docker-compose，於 `docker/` 下執行）

- `python-google-photos` → 容器名 `google-photos`，`../src` 掛載到 `/app`（改程式碼即時生效，Flask `debug=True` 會 reload），`PYTHONPATH=/app`，port `5050:5050`。
- `pgsql_photos` → Postgres，帳密 `user/password`、DB `photodatabase`，主機 port `5434`，資料在 `../pg_data`。
- `node-exporter` → port 9100，讀 `/volume1/src/photo_syncer/textfile`（NAS 上的絕對路徑）。
- network `shared_net` 是 **external**，需先 `docker network create shared_net`；`line-reply` 也在這個網路上。
- 部署主機是 Synology NAS（路徑 `/volume1/src/photo_syncer`）。

## 機密檔（皆在 .gitignore，放在 `src/` 也就是容器 `/app`）

`.env`、`client_secret.json`（Google OAuth）、`token.pickle`（OAuth token 快取）。`downloaded_albums/`、`face_image/`、`pg_data/`、`error.log` 都是執行期產物。

## 外部依賴

- Synology Photos Web API（`SYNO.API.Auth`、`SYNO.Foto.*`），自簽憑證，`verify=False`。
- Google Photos Library API + People API（取使用者名稱）。注意：Google 自 2025-03 起限制 Library API 只能讀寫「本 app 建立的」相簿與媒體。
- `Config.SERVER_URL` 上的 LINE 服務：`/api/line/notify`、`/api/line/album`、`/api/line/faces`（本服務主動 POST 過去通知使用者）。
