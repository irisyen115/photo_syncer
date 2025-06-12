from service.synology_service import (
    save_photos_to_db_with_album, save_exit_db_with_person,
    save_photos_to_db_with_person, randam_pick_from_person_database,
    randam_pick_from_album_database, save_exit_db_with_album
)
from lib.synlogy import list_photos_by_album, list_photos_by_person
from lib.google import get_service
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def get_photos_upload_to_album(auth, person_ID, album_ID, upload_photo_num):
    random_photos = []

    if person_ID:
        person_photo_list = list_photos_by_person(auth=auth, person_id=person_ID, limit=upload_photo_num)
        save_photos_to_db_with_person(person_photo_list, person_ID)
        random_photos = randam_pick_from_person_database(person_id=person_ID, limit=upload_photo_num)
        exit_person_filename = [photo.filename for photo in save_exit_db_with_person(person_id=person_ID, photos=random_photos)]
        print(f"現存於Google相簿照片檔名: {exit_person_filename}")
    elif album_ID:
        album_photo_list = list_photos_by_album(auth=auth, album_id=album_ID, limit=upload_photo_num)
        save_photos_to_db_with_album(album_photo_list, album_ID)
        random_photos = randam_pick_from_album_database(album_id=album_ID, limit=upload_photo_num)
        exit_album_filename = [photo.filename for photo in save_exit_db_with_album(album_id=album_ID, photos=random_photos)]
        print(f"現存於Google相簿照片檔名: {exit_album_filename}")
    return random_photos

def delete_photos_by_filename(creds, album_id, filenames):
    service = get_service(creds)
    photos = []
    next_page_token = None

    while True:
        response = service.mediaItems().search(body={
            "albumId": album_id,
            "pageSize": 100,
            "pageToken": next_page_token
        }).execute()

        items = response.get("mediaItems", [])
        for item in items:
            filename = item.get("filename")
            media_id = item.get("id")
            if filename in filenames:
                photos.append(media_id)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    logging.error(f"🗑️ 符合條件要刪除的照片ID數量：{len(photos)}")

    for photo_id in photos:
        try:
            service.mediaItems().delete(mediaItemId=photo_id).execute()
            logging.error(f"✅ 已刪除：{photo_id}")
        except Exception as e:
            logging.error(f"❌ 刪除失敗：{photo_id} - {e}")
