from lib.synlogy import (
    login, download_photo
)
from lib.google import (
    authenticate, get_service, get_or_create_album,
    upload_photo_bytes, add_photos_to_album, get_photos_upload_to_album
)
from delete_photo import delete_all_photos_from_album
from models.database import SessionLocal
from dotenv import load_dotenv
import os
import time
import queue
import threading
import argparse

load_dotenv()
print("開始解析參數...")

parser = argparse.ArgumentParser()
parser.add_argument('--personID', help='指定要查詢的 Person ID')
parser.add_argument('--albumID', help='指定要查詢的 Album ID')
parser.add_argument('--albumName', type=str, help='指定要命名的 Album name')
args = parser.parse_args()

BASE_URL = os.getenv('SYNO_URL')
ACCOUNT = os.getenv('SYNO_ACCOUNT')
PASSWORD = os.getenv('SYNO_PASSWORD')
FID = os.getenv('SYNO_FID')
TIMEZONE = os.getenv('SYNO_TIMEZONE')
DOWNLOAD_DIR = os.getenv('SYNO_DOWNLOAD_DIR', '/app/downloaded_albums/')

ALBUM_NAME = args.albumName
PERSON_ID = args.personID
ALBUM_ID = args.albumID

NUM_DOWNLOAD_THREADS = 16
NUM_UPLOAD_THREADS = 16
UPLOAD_PHOTO_NUM = 10

download_queue = queue.Queue()
photo_queue = queue.Queue()
token_map = {}

def download_worker(auth,):
    db = SessionLocal()
    while True:
        try:
            p = download_queue.get(timeout=2)
        except queue.Empty:
            break
        try:
            saved_path = os.path.join(DOWNLOAD_DIR, p['filename'])
            if not photo_queue or not saved_path:
                print(f"⚠️ 略過 {p['filename']}（無儲存路徑）")
                continue
            print(f"🔽 下載中: {p['filename']}")
            download_photo(auth, p, save_path=saved_path)
            photo_queue.put((p['filename']))
        except Exception as e:
            print(f"❌ 下載錯誤: {p['filename']} - {e}")
    db.close()

i = [1]
def upload_worker(creds,):
    while True:
        try:
            filename = photo_queue.get(timeout=2)
        except queue.Empty:
            if all(not t.is_alive() for t in threading.enumerate() if t.name.startswith("Downloader")):
                break
            else:
                continue
        try:
            x = i[0]
            i[0] += 1
            print(f"====== 上傳中 =====, 第 {x} 張照片 ======")
            saved_path = os.path.join(DOWNLOAD_DIR, filename)
            begin = time.time()
            print(f"🔼第 {x} 張， 上傳開始時間: {begin:.2f}")
            upload_token = upload_photo_bytes(creds, saved_path)

            token_map[filename] = upload_token
            end= time.time()
            print(f"🔼第 {x} 張， 上傳結束時間: {end:.2f}, 共耗時: {end-begin:.2f}")
        except Exception as e:
            print(f"❌ 上傳錯誤: {filename} - {e}")
        finally:
            photo_queue.task_done()

def initialize_services():
    auth = login(ACCOUNT, PASSWORD, FID, TIMEZONE)
    creds = authenticate()
    return auth, creds

def sync_all(auth):
    random_photos = get_photos_upload_to_album(auth, PERSON_ID, ALBUM_ID, UPLOAD_PHOTO_NUM)
    for photo in random_photos:
        download_queue.put(photo)

    downloaders = []
    for i in range(NUM_DOWNLOAD_THREADS):
        t = threading.Thread(target=download_worker, args=(auth,), name=f"Downloader-{i}")
        t.start()
        downloaders.append(t)

    uploaders = []
    for i in range(NUM_UPLOAD_THREADS):
        t = threading.Thread(target=upload_worker, args=(creds,), name=f"Uploader-{i}")
        t.start()
        uploaders.append(t)

    for t in downloaders:
        t.join()

    photo_queue.join()
    for t in uploaders:
        t.join()

    add_photos_to_album(creds, google_album_id, token_map)

if __name__ == "__main__":
    try:
        auth, creds = initialize_services()
        service = get_service(creds)

        start_time = time.time()
        google_album_id = get_or_create_album(service, album_name=ALBUM_NAME)

        delete_all_photos_from_album(google_album_id)
        sync_all(auth)

        print("🔄 開始同步：從 Synology 下載並上傳至 Google Photos")
        if PERSON_ID:
            print(f"🔍 根據 Person ID = {PERSON_ID} 執行操作...")
        elif ALBUM_ID:
            print(f"📸 查詢 Album ID = {ALBUM_ID} 的相片列表...")
        else:
            print("⚠️ 請至少提供一個參數：--personID 或 --albumID")

        print("✅ 同步完成")
        print(f"⏱️ 總耗時: {time.time() - start_time:.2f} 秒")

    except Exception as e:
        print("發生例外錯誤:", e)
