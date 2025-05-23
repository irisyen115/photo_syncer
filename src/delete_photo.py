from lib.google import authenticate, get_service, get_or_create_album, get_media_items_in_album, remove_all_items_from_album
import os
from dotenv import load_dotenv

load_dotenv()

def delete_all_photos_from_album(google_album_id):
    creds = authenticate()
    service = get_service(creds)
    media_ids = get_media_items_in_album(service, google_album_id)

    if media_ids:
        remove_all_items_from_album(service, google_album_id, media_ids)
        print(f"✅ 已從相簿中移除所有媒體項目")
    else:
        print("相簿已是空的。")

if __name__ == "__main__":
    delete_all_photos_from_album()
