import os, json, threading, time, queue
from lib.synology import login, list_people, thumb_photo, download_photo
from lib.google import (
    get_service, get_or_create_album, add_photos_to_album,
    upload_photo_bytes, delete_all_photos_from_album
)
from service.google_service import get_photos_upload_to_album
from flask import jsonify
from config.config import Config
from service.batch_service import create_new_batch, update_batch_status
import logging
from dotenv import load_dotenv
import requests
from cachetools import TTLCache
from service.user_service import get_user_info_service
import datetime

load_dotenv()
logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

DOWNLOAD_DIR = Config.SYNO_DOWNLOAD_DIR
IMG_URL = Config.IMG_URL
ACCOUNT = Config.SYNO_ACCOUNT
PASSWORD = Config.SYNO_PASSWORD
FID = Config.SYNO_FID
TIMEZONE = Config.SYNO_TIMEZONE
NUM_DOWNLOAD_THREADS = 16
NUM_UPLOAD_THREADS = 16

download_queue = queue.Queue()
photo_queue = queue.Queue()
token_map = {}
face_cache = TTLCache(maxsize=100, ttl=60)

def background_upload(creds, auth, token, album_name, person_id, album_id, num_photos, start_time, batch_id):
    try:
        service = get_service(creds)
        google_album_id = get_or_create_album(service, album_name)
    except Exception as e:
        logging.exception("❌ 建立 Google 相簿失敗")
        update_batch_status(batch_id, "failed")
        try:
            requests.post(
                f"{Config.SERVER_URL}/api/line/notify",
                json={
                    "message": f"❌ 建立相簿失敗，第 {batch_id} 批次中止",
                    "token": token
                }
            )
        except Exception as notify_error:
            logging.error(f"LINE 通知失敗：{notify_error}")
        return

    try:
        update_people_list(auth, token)
    except Exception as e:
        logging.exception("⚠️ 更新人員列表失敗（可略過）")

    try:
        delete_all_photos_from_album(creds, google_album_id)
    except Exception as e:
        logging.exception("⚠️ 刪除 Google 相簿照片失敗（可能是配額或限速）")

    try:
        update_batch_status(batch_id, "uploading")
        result = run_upload(auth, creds, person_id, album_id, num_photos, google_album_id, token)

        logging.info(f"✅ 同步完成，共上傳 {result['uploaded']} 張照片，耗時 {round(time.time() - start_time, 2)} 秒")
        update_batch_status(batch_id, "success")

        requests.post(
            f"{Config.SERVER_URL}/api/line/notify",
            json={
                "message": f"✅ 上傳完成，共上傳 {result['uploaded']} 張照片",
                "token": token
            }
        )
    except Exception as e:
        logging.exception("❌ 同步過程發生錯誤")
        update_batch_status(batch_id, "failed")

        requests.post(
            f"{Config.SERVER_URL}/api/line/notify",
            json={
                "message": f"❌ 上傳失敗,第{batch_id}批次",
                "token": token
            }
        )

def update_people_list(auth, user_id):
    if not auth:
        logging.error("Synology 登入失敗，請檢查帳號密碼或網路連線")
        return []

    try:
        people_list = list_people(auth, 8)
        if not people_list:
            logging.error("無法獲取人員列表，請檢查 Synology 服務是否正常")
            return []
        logging.info(f"成功獲取 {len(people_list)} 人員資料")
        result_list = []
        for person in people_list:
            thumb_photo(person['id'], person['additional']['thumbnail']['cache_key'], auth)
            result_list.append({
                "name": person['name'],
                "ID": person['id'],
                "img": f"{IMG_URL}/{person['id']}.jpg"
            })

        if 'faces' not in face_cache or not face_cache['faces']:
            requests.post(
                f"{Config.SERVER_URL}/api/line/faces",
                json={
                    "faces": result_list,
                    "user_id": user_id
                }
            )
        elif 'faces' in face_cache:
            requests.post(
                f"{Config.SERVER_URL}/api/line/faces",
                json={
                    "faces": face_cache['faces'],
                    "user_id": user_id
                }
            )
        face_cache['faces'] = result_list
        return face_cache['faces']
    except Exception as e:
        logging.exception("⚠️ 更新人員資料過程中發生錯誤")
        return []

def handle_upload(request, creds, session):
    try:
        data = request.get_json(force=True)
    except Exception as e:
        logging.error("JSON 解析失敗: %s", str(e))
        return jsonify({"error": "無法解析 JSON，請檢查資料格式"}), 400

    person_id = request.args.get('personID') or data.get('personID')
    if person_id:
        logging.error(f"同步人員 ID: {person_id}")
    else:
        logging.error("請求中未提供 personID")
        return jsonify({"error": "請提供 personID"}), 400
    album_id = data.get("albumID")
    album_name = data.get("albumName") or os.getenv("DEFAULT_ALBUM_NAME", "My New Album")
    num_photos = data.get("numPhotos") or os.getenv("DEFAULT_NUM_PHOTOS", 5)
    token = request.args.get('token') or data.get('token')
    auth = session.get('auth')
    if not auth:
        auth = login(ACCOUNT, PASSWORD, FID, TIMEZONE)
    if not person_id and not album_id:
        return jsonify({"error": "請提供 personID 或 albumID"}), 400

    start_time = time.time()
    new_batch = create_new_batch(auth)
    if not new_batch:
        return jsonify({"error": "目前尚無上傳批次資料"}), 404

    threading.Thread(target=background_upload, args=(
        creds, auth, token, album_name, person_id, album_id, num_photos, start_time, new_batch.id
    )).start()

    user_info = get_user_info_service(creds)
    if not user_info or 'name' not in user_info:
        return jsonify({"error": "使用者資訊取得失敗"}), 500

    batch_time = new_batch.created_at
    dt = datetime.fromisoformat(batch_time)
    batch_time_taipei = dt.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "message": f"同步作業已在背景啟動，使用者:{user_info.get('name')}, 第{new_batch.id}批次, 上傳時間{batch_time_taipei}, 上傳張數{new_batch.count}"
    })

def run_upload(auth, creds, person_id, album_id, num_photos, google_album_id, token):
    token_map.clear()
    report = get_photos_upload_to_album(auth, person_id, album_id, num_photos, token)
    if not report:
        logging.error("⚠️ 獲取照片上傳報告失敗，請檢查 Synology 服務是否正常")
        return {"uploaded": 0, "messages": ["無法獲取照片上傳報告"]}
    logging.error(f"獲取到 {len(report.get('photos', []))} 張照片，準備下載和上傳到 Google 相簿")
    for photo in report.get("photos", []):
        download_queue.put(photo)

    def download_worker():
        while True:
            try:
                p = download_queue.get(timeout=2)
            except queue.Empty:
                break
            saved_path = os.path.join(DOWNLOAD_DIR, p['filename'])
            download_photo(auth, p, save_path=saved_path)
            photo_queue.put(p['filename'])

    def upload_worker():
        while True:
            try:
                filename = photo_queue.get(timeout=2)
            except queue.Empty:
                break
            saved_path = os.path.join(DOWNLOAD_DIR, filename)
            token_map[filename] = upload_photo_bytes(creds, saved_path)
            photo_queue.task_done()

    downloaders = [threading.Thread(target=download_worker) for _ in range(NUM_DOWNLOAD_THREADS)]
    uploaders = [threading.Thread(target=upload_worker) for _ in range(NUM_UPLOAD_THREADS)]
    [t.start() for t in downloaders]
    [t.start() for t in uploaders]
    [t.join() for t in downloaders]
    photo_queue.join()
    [t.join() for t in uploaders]

    add_photos_to_album(creds, google_album_id, token_map)
    return {
        "uploaded": len(token_map),
        "messages": report['messages']
    }

