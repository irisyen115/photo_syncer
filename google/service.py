import os
import pickle
import mimetypes
import requests
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.sharing",
    "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
]

API_BASE_URL = 'https://photoslibrary.googleapis.com/v1/'
UPLOAD_PHOTO_BYTES_ENDPOINT = f'{API_BASE_URL}uploads'
ADD_MEDIA_ITEMS_TO_ALBUM_ENDPOINT = f'{API_BASE_URL}mediaItems:batchCreate'


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
            creds = flow.run_local_server()
        with open("token.pickle", "wb") as tokenFile:
            pickle.dump(creds, tokenFile)
    return creds


def get_service(creds):
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
