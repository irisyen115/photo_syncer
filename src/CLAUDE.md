# src/ — google-photos Flask 服務

容器內路徑為 `/app`，所有 import 都以 `src/` 為根（`from service.x import ...`、`from lib.google import ...`）。進入點 `app.py`（port 5050）。依賴見 `requirements.txt`（Flask 3、SQLAlchemy 2、psycopg2、google-api-python-client、cachetools）。

## 分層

- `controllers/` — Flask Blueprints，只做參數解析、呼叫 service、回 JSON。
- `service/` — 商業邏輯。
- `lib/google.py` — Google Photos API 包裝（OAuth、相簿、上傳 bytes、batchCreate、移除項目）。
- `lib/synology.py` — Synology Photos API 包裝（login、list_people、list_photos_by_person[_and_interval_time]、download_photo、thumb_photo）。模組層級共用一個 `requests.Session`。
- `models/` — SQLAlchemy ORM。`models/__init__.py` 在 import 時執行 `Base.metadata.create_all`（**沒有 migration**，改欄位要手動 ALTER）。
- `config/config.py` — `Config` 從 `.env` 讀值。
- `utils/sync_utils.py` — 首次上傳時的背景同步。
- `tools/` — cron 腳本，見 `tools/CLAUDE.md`。

## API 端點

| Method | Path | Controller | 作用 |
|---|---|---|---|
| GET/POST | `/upload_photos?token=&personID=` body `{personID, albumName, numPhotos, ...}` | upload | 建立 UploadBatch，背景 thread 執行上傳，立即回應 |
| GET | `/update_people?user_id=` | upload | Synology 登入、抓前 8 位人物＋縮圖存到 `/app/face_image/`，POST 到 LINE `/api/line/faces` |
| GET | `/sync_latest_photo/<person_id>?token=` | sync | 從上次同步時間增量同步，LINE 通知最新拍攝時間 |
| POST | `/sync_interval_time_photos` body `{personID, start_time, end_time}` (YYYY-MM-DD) | sync | 依區間重抓 |
| POST | `/delete_photo` body `{filenames, album_name}` | delete | 從 Google 相簿移除並刪除 ExistPerson |
| GET | `/upload_records?personID=` | photo | 已上傳（ExistPerson）且非黑名單的照片，隨機排序 |
| POST | `/blacklist_photo` / `/remove_blacklist` body `{photo_id, reason}`；GET `/blacklist` | blacklist | 黑名單 CRUD |
| GET | `/upload_batches` | batch | 列出所有 UploadBatch |
| POST | `/list_albums?token=` | album | 列出 Google 相簿（略過「待刪除照片」），POST 到 LINE `/api/line/album` |

## 上傳主流程（`service/upload_service.py`）

`handle_upload` → `create_new_batch`（status pending）→ thread `background_upload`：
1. `get_or_create_album(albumName)`
2. `update_people_list`
3. 清空 Google 相簿既有內容（`move_items_to_trash_album` 複製到「待刪除照片」相簿，再 `batchRemoveMediaItems`，每批 49）
4. `run_upload`：`get_photos_upload_to_album`（`service/google_service.py`）從 DB 隨機挑 `numPhotos` 張該人物照片 → 寫入 ExistPerson → 16 條下載 thread（Synology → `SYNO_DOWNLOAD_DIR`）+ 16 條上傳 thread（`/v1/uploads` 取 upload token）→ `add_photos_to_album`（每批 45）
5. 更新 batch status `uploading` → `success`/`failed`，LINE notify。

若 DB 中沒有該人物照片，改用 `threading.Timer` 背景跑 `background_sync_and_upload`（全量同步該人物到 DB），並回覆使用者稍後再試。

## 資料表（`models/`）

| Model | Table | 說明 |
|---|---|---|
| `Photo` | `photos` | `item_id` = Synology 照片 id（unique），`filename`、`shooting_time`、`saved_path` |
| `Person` | `person_photos` | 人物 ↔ 照片 關聯（Synology 上的全部），unique(person_id, photo_id) |
| `Album` | `album_photos` | 相簿 ↔ 照片 |
| `ExistPerson` / `ExistAlbum` | `exist_person_photos` / `exist_album_photos` | **目前已上傳到 Google** 的集合；每次上傳先刪掉該人物的再重寫 |
| `PhotoBlacklist` | `photo_blacklist` | 不上傳的照片（`photo_id` = `Photo.item_id`） |
| `UploadBatch` | `uploaded_batches` | 上傳批次紀錄、狀態 |
| `SyncStatus` | `sync_status` | 每個 person 最後同步的照片與拍攝時間 |

關聯 join 一律用 `X.photo_id == Photo.item_id`（不是 `Photo.id`）。欄位名 `exit_*` 是 "exist" 的錯字，但已在 DB 中，不要直接改名。

## 環境變數（`.env`）

`SYNO_URL`、`SYNO_ACCOUNT`、`SYNO_PASSWORD`、`SYNO_FID`、`SYNO_TIMEZONE`、`SYNO_DOWNLOAD_DIR`（`/app/downloaded_albums/`）、`SERVER_URL`（**必填**，`Config` import 時做字串相加，缺少會直接 TypeError）、`SECRET_KEY`、`LINE_ACCESS_TOKEN`、選用 `DEFAULT_ALBUM_NAME`、`DEFAULT_NUM_PHOTOS`。`.env.template` 只列了 SYNO_*。
DB 連線字串寫死在 `models/database.py`（`pgsql_photos:5432`），只能在 docker network 內連。

## Google OAuth

`lib/google.authenticate()` 讀寫寫死路徑 `/app/token.pickle`、`/app/client_secret.json`；token 無效時跑 `InstalledAppFlow.run_local_server`。首次授權：`docker exec -it google-photos python tools/get_cred.py`。

## 慣例

- 所有 log 都用 `logging.error(...)` 寫到 `error.log`（含一般資訊），每個模組各自 `basicConfig`。
- 訊息、註解大多是繁體中文。
- 每個 service 函式自己開 `SessionLocal()`，記得在 `finally` 中 close。

## 測試

`docker exec google-photos python -m pytest tests/test_google_service.py`
只有 `test_google_service.py` 是純 mock 且可正常執行。`test_google_auth.py`、`test_synlogy.py` 會打真實服務；`test_sync_service.py` 測的是已不存在的 `background_sync`/`run_sync`，需重寫；其餘測試 import `models` 時會觸發 `create_all` 連線 DB，所以必須在容器內執行。

## 已知問題（修改相關程式碼時留意）

- `sync_photos_since_last_time` 在該人物沒有 `sync_status` 紀錄時會直接回 `[]`；新人物要先跑全量同步（`tools/photo_sync.py`）。
- `autonomy_get_interval_time_person` 會先刪掉該人物**全部** `Person` 紀錄，再只寫回區間內的照片。
- `handle_upload` 永遠傳 `start_dt/end_dt=None`，時間區間挑選沒有作用。
- `get_upload_records_service` 的 person_id 篩選被註解掉，回傳的是所有人的紀錄。

## 隨機挑照片（已知問題）

唯一真正決定「上傳哪些照片」的是 `service/synology_service.random_pick_from_person_database`：Photo JOIN Person，依 person_id／拍攝時間篩選，再交給 PostgreSQL `ORDER BY random() LIMIT n`（無種子、每次不同、不重複抽 n 張；每次會全掃並排序該人物的照片）。由 `service/google_service.get_photos_upload_to_album` 呼叫，結果直接成為 `run_upload` 要下載並上傳的清單。其他 `func.random()` 只用於列表排序（`/upload_records`、`/blacklist`）。

- **黑名單擋不住上傳**：抽選時沒有排除 `photo_blacklist`。`save_exist_db_with_person` 雖然會過濾黑名單，但只影響寫進 `exist_person_photos` 的紀錄；`get_photos_upload_to_album` 回傳給上傳流程的仍是未過濾的 `random_photos`，所以黑名單照片照樣上傳到 Google，只是不出現在 `/upload_records`。
- **修法方向**：應在 SQL 裡加 `NOT IN (SELECT photo_id FROM photo_blacklist)` 排除；若改成抽完才過濾，實際張數會少於 n。
- **不避開上次抽過的照片**：每次都從全部照片重抽，可能重複。Google Photos 每次上傳都會在相簿庫新建媒體項目，「移出相簿」不會刪除，所以重複的照片會在相簿庫累積多份，「待刪除照片」相簿也越來越大。
- **時間區間篩選沒作用**：`start_time`／`end_time` 的篩選邏輯存在，但 `handle_upload` 永遠傳 `None`。
- **多餘的 Synology API 呼叫**：`get_photos_upload_to_album` 呼叫 `list_photos_by_person(..., limit=n)`，結果只用來判斷非空，沒有用在抽選上。
- `utils/sync_utils.background_sync_and_upload` 同步後抽了一次但結果只用來判斷「有沒有照片」就丟掉，名稱有 upload 但實際不會上傳，只發 LINE 通知請使用者重試。
- `randam_pick_from_album_database`（名稱拼錯）沒有任何呼叫者；`get_photos_upload_to_album` 收到的 `album_id` 也沒有被使用。
