from service.synology_service import (
    list_all_photos_by_person, save_photos_to_db_with_person,
    random_pick_from_person_database
)
import logging
import requests
from config.config import Config

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def needs_sync_warning(person_photos, person_id, upload_photo_num):
    if not person_id:
        return {"photos": [], "messages": ["person_id 為空，無法處理"]}

    messages = []
    sync_warn = False

    if not person_photos and len(person_photos) <= upload_photo_num:
        msg = f"⚠️ 找不到 person_id={person_id} 的照片，將花時間從全部資料中挑選。"
        sync_warn = True
        messages.append(msg)
    if not messages:
        messages.append(f"✅ person_id={person_id} 的照片已經上傳完成，數量為 {upload_photo_num} 張。")
    return sync_warn, messages

def background_sync_and_upload(auth, person_id, upload_photo_num, token):
    logging.info(f"開始背景同步與上傳 person_id={person_id}")

    person_photo_list = list_all_photos_by_person(auth=auth, person_id=person_id)
    if not person_photo_list:
        logging.error(f"⚠️ 人員 {person_id} 沒有同步到任何照片")
        return

    save_photos_to_db_with_person(person_photo_list, person_id)
    random_photos = random_pick_from_person_database(person_id=person_id, limit=upload_photo_num)
    if not random_photos:
        logging.error(f"⚠️ 人員 {person_id} 的隨機照片選取為空")
        return

    requests.post(f"{Config.SERVER_URL}/api/line/notify", json={
        "token": token,
        "message": "✅ 你的人員資料已完成同步！請重新操作。"
    })
