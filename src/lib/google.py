import os
import pickle
import mimetypes
import requests
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import json
from google_auth_oauthlib.flow import Flow
from google_auth_oauthlib.flow import InstalledAppFlow
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.sharing",
    "https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata",
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary",
    "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

API_BASE_URL = 'https://photoslibrary.googleapis.com/v1/'
UPLOAD_PHOTO_BYTES_ENDPOINT = f'{API_BASE_URL}uploads'
ADD_MEDIA_ITEMS_TO_ALBUM_ENDPOINT = f'{API_BASE_URL}mediaItems:batchCreate'
UPLOAD_PHOTO_NUM = 10


def get_mime(file_path):
    return str(mimetypes.guess_type(file_path)[0])

def authenticate():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as tokenFile:
            creds = pickle.load(tokenFile)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)
        with open("token.pickle", "wb") as tokenFile:
            pickle.dump(creds, tokenFile)
    return creds

def get_service(creds):
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

def get_or_create_album(service, album_name="My New Album"):
    results = service.albums().list(pageSize=50, fields="albums(id,title)").execute()
    albums = results.get('albums', [])
    for album in albums:
        if album['title'] == album_name:
            return album['id']

    new_album = {"album": {"title": album_name}}
    created_album = service.albums().create(body=new_album).execute()
    return created_album['id']

def get_albums_with_cover_urls(service):
    albums_with_covers = []
    next_page_token = None

    while True:
        response = service.albums().list(
            pageSize=50,
            pageToken=next_page_token,
            fields="albums(id,title,coverPhotoMediaItemId),nextPageToken"
        ).execute()

        albums = response.get("albums", [])

        for album in albums:
            cover_url = ""
            media_item_id = album.get("coverPhotoMediaItemId")
            if media_item_id:
                try:
                    item = service.mediaItems().get(mediaItemId=media_item_id).execute()
                    cover_url = item.get("baseUrl", "") + "=w512-h384"
                except Exception as e:
                    print(f"⚠️ 無法取得封面圖: {e}")

            albums_with_covers.append({
                "id": album["id"],
                "title": album["title"],
                "cover_url": cover_url
            })
            logging.error(f"Album: {album['title']}, Cover URL: {cover_url}")

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return albums_with_covers


def get_media_items_in_album(service, album_id):
    media_item_ids = []
    next_page_token = None

    while True:
        body = {"albumId": album_id}
        if next_page_token:
            body["pageToken"] = next_page_token

        response = service.mediaItems().search(body=body).execute()

        if "mediaItems" in response:
            for item in response["mediaItems"]:
                media_item_ids.append(item["id"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return media_item_ids

def list_media_items_in_album(service, album_id):
    media_items = []
    next_page_token = None

    while True:
        body = {"albumId": album_id}
        if next_page_token:
            body["pageToken"] = next_page_token

        response = service.mediaItems().search(body=body).execute()

        items = response.get("mediaItems", [])
        media_items.extend(items)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return media_items

def find_media_item_ids_by_filenames(media_items, filenames):
    filename_set = set(filenames)
    found_ids = []

    for item in media_items:
        fname = item.get("mediaMetadata", {}).get("filename") or item.get("filename")
        if fname in filename_set:
            found_ids.append(item["id"])

    return found_ids

def remove_all_items_from_album(service, album_id, media_item_ids):
    url = f"{API_BASE_URL}albums/{album_id}:batchRemoveMediaItems"

    headers = {
        "Content-Type": "application/json"
    }

    batch_size = 49
    for i in range(0, len(media_item_ids), batch_size):
        batch = media_item_ids[i:i + batch_size]
        body = json.dumps({
            "mediaItemIds": batch
        })

        response, content = service._http.request(
            uri=url,
            method="POST",
            body=body,
            headers=headers
        )

        if response.status == 200:
            logging.error(f"成功移除媒體項目")
        else:
            logging.error(f"失敗：", response.status, content.decode())
            break

def list_photos(service):
    photos = []
    nextPageToken = None
    while True:
        response = service.mediaItems().list(pageSize=50, pageToken=nextPageToken).execute()
        items = response.get('mediaItems', [])
        photos.extend(items)
        nextPageToken = response.get('nextPageToken')
        if not nextPageToken:
            break
    return photos

def upload_photo_bytes(creds, photo_path):
    mime_type = get_mime(photo_path)
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-type": "application/octet-stream",
        "X-Goog-Upload-Content-Type": mime_type,
        "X-Goog-Upload-Protocol": "raw"
    }
    with open(photo_path, "rb") as file:
        binary_data = file.read()

    response = requests.post(UPLOAD_PHOTO_BYTES_ENDPOINT, headers=headers, data=binary_data)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")

def add_photos_to_album(creds, album_id, filename_token_mapping):
    batch_size = 45
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {creds.token}"
    }

    tokens = list(filename_token_mapping.values())

    for i in range(0, len(tokens), batch_size):
        batch_tokens = tokens[i:i + batch_size]
        new_media_items = []
        for token in batch_tokens:
            filename = [fname for fname, t in filename_token_mapping.items() if t == token][0]
            new_media_items.append({
                "description": "Uploaded via API",
                "simpleMediaItem": {
                    "fileName": filename,
                    "uploadToken": token
                }
            })

        request_body = {
            "albumId": album_id,
            "newMediaItems": new_media_items
        }

        response = requests.post(ADD_MEDIA_ITEMS_TO_ALBUM_ENDPOINT, json=request_body, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to add media items: {response.status_code} - {response.text}")

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

def delete_all_photos_from_album(creds, google_album_id):
    service = get_service(creds)
    media_ids = get_media_items_in_album(service, google_album_id)

    if media_ids:
        remove_all_items_from_album(service, google_album_id, media_ids)
        logging.error(f"✅ 已從相簿中移除所有媒體項目")
    else:
        logging.error("相簿已是空的。")