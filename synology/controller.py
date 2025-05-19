from dotenv import load_dotenv
from datetime import datetime
from synology.service import login, list_albums, list_photos, download_photo, save_photo_to_db
from models.database import SessionLocal
from models.photo import Photo
import os

load_dotenv()

BASE_URL = os.getenv('SYNO_URL')
ACCOUNT = os.getenv('SYNO_ACCOUNT')
PASSWORD = os.getenv('SYNO_PASSWORD')
FID = os.getenv('SYNO_FID')
TIMEZONE = os.getenv('SYNO_TIMEZONE')
DOWNLOAD_DIR = os.getenv('SYNO_DOWNLOAD_DIR')

if __name__ == '__main__':
    auth = login(ACCOUNT, PASSWORD, FID, TIMEZONE)
    albums = list_albums(auth)
    print('Albums:', albums)
    album_list = albums['data']['list']
    vacation_album = next((a for a in album_list if a['name'] == '天澯收涎'), None)
    album_id = vacation_album['id'] if vacation_album else None

    print(f"Album ID: {album_id}")

    photos = list_photos(auth, album_id)
    for p in photos['data']['list']:
        print(p)
        save_photo_to_db(
            item_id=p['id'],
            filename=p['filename'],
            album_id=album_id,
            takentime=datetime.fromtimestamp(p['time']),
            saved_path=f"/app/downloaded_albums/{p['filename']}"
        )

    db = SessionLocal()
    try:
        for p in photos['data']['list']:
            record = db.query(Photo).filter_by(item_id=p['id']).first()
            if record and record.saved_path:
                download_photo(auth, p, save_path=record.saved_path)
                print(f"Downloaded {p['filename']} in {record.takentime} to {record.saved_path}")
            else:
                print(f"⚠️ Skipped {p['filename']}")
    finally:
        db.close()
