from concurrent.futures import ThreadPoolExecutor
from synology.service import login, list_albums, list_photos, download_photo, save_photo_to_db
from google.service import authenticate, get_service, get_or_create_album, upload_photo_bytes, add_photos_to_album
from models.database import SessionLocal
from models.photo import Photo
import os
from dotenv import load_dotenv
from threading import Lock
from datetime import datetime
import time

load_dotenv()
upload_lock = Lock()

BASE_URL = os.getenv('SYNO_URL')
ACCOUNT = os.getenv('SYNO_ACCOUNT')
PASSWORD = os.getenv('SYNO_PASSWORD')
FID = os.getenv('SYNO_FID')
TIMEZONE = os.getenv('SYNO_TIMEZONE')
DOWNLOAD_DIR = os.getenv('SYNO_DOWNLOAD_DIR', '/app/downloaded_albums/')
ALBUM_NAME = os.getenv('ALBUM_NAME', '天澯')

def sync_all():
    print("🔽 登入 Synology...")
    auth = login(ACCOUNT, PASSWORD, FID, TIMEZONE)
    albums = list_albums(auth)
    for album in albums['data']['list']:
        print(f"📁 相簿名稱: {album['name']}, ID: {album['id']}")
    target_album = next((a for a in albums['data']['list'] if a['name'] == '天澯收涎'), None)
    album_id = target_album['id'] if target_album else None
    if not album_id:
        return

    photos = list_photos(auth, album_id, limit=20)
    photo_list = photos['data']['list']
    for p in photo_list:
        save_photo_to_db(p['id'], p['filename'], album_id, datetime.fromtimestamp(p['time']), DOWNLOAD_DIR + p['filename'])
    print(f"📸 總共 {len(photo_list)} 張照片")

    print("☁️ 登入 Google Photos...")
    creds = authenticate()
    service = get_service(creds)
    google_album_id = get_or_create_album(service, album_name=ALBUM_NAME)
    print(f"☁️ Google 相簿 ID: {google_album_id}")

    def download_and_upload(p):
        db = SessionLocal()
        try:
            record = db.query(Photo).filter_by(item_id=p['id']).first()
            if not record or not record.saved_path:
                print(f"⚠️ 略過 {p['filename']}（無儲存路徑）")
                return

            download_photo(auth, p, save_path=record.saved_path)
            print(f"✅ 下載完成: {p['filename']}, 拍攝於: {record.shooting_time}")

            with upload_lock:
                upload_token = upload_photo_bytes(creds, record.saved_path)
                add_photos_to_album(creds, google_album_id, {record.filename: upload_token})
                print(f"☁️ 上傳完成: {p['filename']}, 拍攝於: {record.shooting_time}")

        except Exception as e:
            print(f"❌ 發生錯誤: {p['filename']} - {e}")
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.map(download_and_upload, photo_list)


if __name__ == "__main__":
    print("🔄 開始同步：從 Synology 下載並立即上傳至 Google Photos")
    t = time.time()
    sync_all()
    print("✅ 同步完成")
    print(f"⏱️ 總耗時: {time.time() - t:.2f} 秒")
