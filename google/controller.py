from google.service import authenticate, get_service, get_or_create_album, upload_photo_bytes, add_photos_to_album, list_photos
from models.database import SessionLocal
from models.photo import Photo

if __name__ == "__main__":
    creds = authenticate()
    service = get_service(creds)
    album_id = get_or_create_album(service, album_name="My New Album")
    db = SessionLocal()
    try:
        for p in db.query(Photo).all():
            if p.saved_path:
                upload_token = upload_photo_bytes(creds, p.saved_path)
                print(f"Upload token for {p.filename}: {upload_token}")
                add_photos_to_album(creds, album_id, {p.filename: upload_token})
                print(f"{p.filename} has been successfully added to the album.")
            else:
                print(f"⚠️ Skipped {p.filename}")
    except Exception as e:
        print("An error occurred:", e)
    finally:
        db.close()

    # photos = list_photos(service)
    # for photo in photos:
    #     print(photo['filename'], photo.get('baseUrl', 'No URL'))
    # photo_path = "/app/downloaded_albums/test.jpg"
    # filename = "test.jpg"

    # try:
    #     upload_token = upload_photo_bytes(creds, photo_path)
    #     print(f"Upload token for {filename}: {upload_token}")

    #     add_photos_to_album(creds, album_id, {filename: upload_token})
    #     print(f"{filename} has been successfully added to the album.")

