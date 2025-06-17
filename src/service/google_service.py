from service.synology_service import (
    save_photos_to_db_with_person, random_pick_from_person_database
)
from utils.sync_utils import (
    needs_sync_warning, background_sync_and_upload
)
from lib.synlogy import list_photos_by_person
import logging
from models.photo import Photo
from models.database import SessionLocal
from models.person import Person
import threading

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def get_photos_upload_to_album(auth, person_id, album_id, upload_photo_num, token):
    if not person_id:
        logging.error("⚠️ person_id 為空，無法處理")
        return {"photos": [], "messages": ["person_id 為空，無法處理"]}

    db = SessionLocal()
    person_photos = db.query(Photo).join(Person, Person.photo_id == Photo.item_id).filter(Person.person_id == person_id).all()
    if not person_photos:
        logging.error(f"⚠️ 找不到 person_id={person_id} 的照片，將花時間從全部資料中挑選。")

    sync_warn, messages = needs_sync_warning(
        person_photos,
        person_id,
        upload_photo_num
    )

    if sync_warn:
        logging.warning(f"⚠️ 人員 {person_id} 需要同步，將於背景延遲執行")

        threading.Timer(
            interval=2,
            function=background_sync_and_upload,
            args=(auth, person_id, upload_photo_num, token)
        ).start()

        return {
            "photos": [],
            "messages": ["✅ 任務已提交，由於您是第一次上傳，系統將在背景同步資料與上傳照片，需等候數十分鐘，請稍後再試"]
        }

    person_photo_list = list_photos_by_person(auth=auth, person_id=person_id, limit=upload_photo_num)
    random_photos = random_pick_from_person_database(person_id=person_id, limit=upload_photo_num)

    if not person_photo_list or not random_photos:
        return {"photos": [], "messages": ["沒有可上傳的照片"]}

    save_photos_to_db_with_person(person_photo_list, person_id)

    return {
        "photos": random_photos,
        "messages": messages
    }

