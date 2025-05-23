# service.py
import os
import requests
import urllib3
from models.database import SessionLocal
from models.photo import Photo
from datetime import datetime
from models.album import Album
from models.person import Person
from sqlalchemy import func
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv('SYNO_URL')
FID = os.getenv('SYNO_FID')
TIMEZONE = os.getenv('SYNO_TIMEZONE')
DOWNLOAD_DIR = os.getenv('SYNO_DOWNLOAD_DIR')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session = requests.Session()

HEADERS = {
    'accept': '*/*',
    'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': BASE_URL,
    'referer': f"{BASE_URL}/",
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/135.0.0.0 Safari/537.36'
}


def login(account, password, fid, timezone):
    url = f"{BASE_URL}/webapi/entry.cgi?api=SYNO.API.Auth"
    print(BASE_URL)
    print(f"url: {url}")
    payload = {
        'api': 'SYNO.API.Auth',
        'version': '7',
        'method': 'login',
        'session': 'webui',
        'enable_syno_token': 'yes',
        'account': account,
        'passwd': password,
        'logintype': 'local',
        'timezone': timezone,
        'client': 'browser',
        'fid': fid
    }
    resp = session.post(url, headers=HEADERS, data=payload, verify=False)
    resp.raise_for_status()
    data = resp.json()
    if 'data' not in data:
        data['data'] = {}
    if 'synotoken' not in data['data']:
        data['data']['synotoken'] = session.cookies.get('synotoken')
    return data

def get_album(auth, album_id):
    token = auth['data']['synotoken']
    url = f"{BASE_URL}/webapi/entry.cgi"
    payload = {
        "api": "SYNO.Foto.Browse.Album",
        "method": "get",
        "version": "4",
        "album_id": album_id,
        "additional": '["sharing_info","thumbnail"]'
    }
    resp = session.post(url, headers=HEADERS, params={'SynoToken': token}, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()['data']

def get_person(auth, person_id):
    token = auth['data']['synotoken']
    url = f"{BASE_URL}/webapi/entry.cgi"
    payload = {
        "api": "SYNO.Foto.Browse.Person",
        "method": "get",
        "version": "4",
        "person_id": person_id,
        "additional": '["thumbnail"]'
    }
    resp = session.post(url, headers=HEADERS, params={'SynoToken': token}, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()['data']

def list_albums(auth):
    token = auth['data']['synotoken']
    url = f"{BASE_URL}/webapi/entry.cgi"
    payload = {
        "api": "SYNO.Foto.Browse.Album",
        "method": "list",
        "version": "4",
        "offset": 0,
        "limit": 5,
        "category": "all",
        "sort_by": "create_time",
        "sort_direction": "desc",
        "additional": "[\"sharing_info\",\"thumbnail\"]"
    }
    resp = session.post(url, headers=HEADERS, params={'SynoToken': token}, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()


def list_photos_by_album(auth, album_id, offset=0, limit=100):
    token = auth['data']['synotoken']
    url = f"{BASE_URL}/webapi/entry.cgi/SYNO.Foto.Browse.Item"
    headers = HEADERS.copy()
    headers['x-syno-token'] = token

    payload = {
        "api": "SYNO.Foto.Browse.Item",
        "method": "list",
        "version": "4",
        "additional": '["thumbnail","resolution","orientation","video_convert","video_meta","provider_user_id"]',
        "offset": offset,
        "limit": limit,
        "sort_direction": "asc",
        "album_id": album_id,
    }

    resp = session.post(url, headers=headers, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()['data']['list']

def list_photos_by_person(auth, person_id, offset=0, limit=100):
    token = auth['data']['synotoken']
    url = f"{BASE_URL}/webapi/entry.cgi/SYNO.Foto.Browse.Item"
    headers = HEADERS.copy()
    headers['x-syno-token'] = token

    payload = {
        "api": "SYNO.Foto.Browse.Item",
        "method": "list",
        "version": "4",
        "additional": '["thumbnail","resolution","orientation","video_convert","video_meta","provider_user_id"]',
        "offset": offset,
        "limit": limit,
        "sort_direction": "asc",
        "person_id": person_id,
    }

    resp = session.post(url, headers=headers, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()['data']['list']

def list_all_photos_by_album(auth, album_id):
    all_photos = []
    offset = 0
    limit = 100

    while True:
        photos = list_photos_by_album(auth, album_id, offset, limit)
        if not photos:
            break
        all_photos.extend(photos)
        offset += limit

    return all_photos

def list_all_photos_by_person(auth, person_id):
    all_photos = []
    offset = 0
    limit = 100

    while True:
        photos = list_photos_by_person(auth, person_id, offset, limit)
        if not photos:
            break
        all_photos.extend(photos)
        offset += limit

    return all_photos

def download_photo(auth, item, save_path=None):
    token = auth['data']['synotoken']
    item_id = item['id']
    filename = item['filename']

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    save_path = save_path or os.path.join(DOWNLOAD_DIR, filename)

    url = f"{BASE_URL}/webapi/entry.cgi/{filename}"
    params = {'SynoToken': token}
    data = {
        'force_download': 'true',
        'item_id': f'[{item_id}]',
        'download_type': 'source',
        'api': 'SYNO.Foto.Download',
        'method': 'download',
        'version': '2'
    }

    resp = session.post(url, headers=HEADERS, params=params, data=data, verify=False)
    resp.raise_for_status()

    with open(save_path, 'wb') as f:
        f.write(resp.content)

def save_photos_to_db_with_album(photo_list, album_id):
    db = SessionLocal()
    existing_ids = {
        p.item_id for p in db.query(Photo.item_id).filter(
            Photo.item_id.in_([p['id'] for p in photo_list])
        )
    }

    new_photos = []
    new_album = []

    for p in photo_list:
        if p['id'] not in existing_ids:
            photo = Photo(
                item_id=p['id'],
                filename=p['filename'],
                shooting_time=datetime.fromtimestamp(p['time']),
                saved_path=DOWNLOAD_DIR + p['filename'],
            )
            new_photos.append(photo)
        existing_pair = db.query(Person).filter_by(
            album_id=album_id,
            photo_id=p['id']
        ).first()

        if existing_pair is None:
            album = Album(album_id=album_id, photo_id=p['id'])
            new_album.append(album)
        else:
            album = existing_pair

        print(f"person: {album.album_photo_pair}")

    if new_album:
        db.bulk_save_objects(new_album)
        db.commit()
        print(f"✅ 共儲存 {len(new_album)} 張與人臉關聯的照片")

    if new_photos:
        db.bulk_save_objects(new_photos)
        db.commit()
        print(f"✅ 共儲存 {len(new_photos)} 張與相簿關聯的照片")
    else:
        print("⚠️ 沒有新照片需要儲存")

def save_photos_to_db_with_person(photo_list, person_id):
    db = SessionLocal()
    existing_ids = {
        p.item_id for p in db.query(Photo.item_id).filter(
            Photo.item_id.in_([p['id'] for p in photo_list])
        )
    }

    new_photos = []
    new_person = []

    for p in photo_list:
        if p['id'] not in existing_ids:
            photo = Photo(
                item_id=p['id'],
                filename=p['filename'],
                shooting_time=datetime.fromtimestamp(p['time']),
                saved_path=DOWNLOAD_DIR + p['filename'],
            )
            new_photos.append(photo)

        existing_pair = db.query(Person).filter_by(
            person_id=person_id,
            photo_id=p['id']
        ).first()

        if existing_pair is None:
            person = Person(person_id=person_id, photo_id=p['id'])
            new_person.append(person)
        else:
            person = existing_pair

        print(f"person: {person.person_photo_pair}")

    if new_person:
        db.bulk_save_objects(new_person)
        db.commit()
        print(f"✅ 共儲存 {len(new_person)} 張與人臉關聯的照片")

    if new_photos:
        db.bulk_save_objects(new_photos)
        db.commit()
        print(f"✅ 共儲存 {len(new_photos)} 張與相簿關聯的照片")
    else:
        print("⚠️ 沒有新照片需要儲存")

def randam_pick_from_person_database(person_id=None, limit=30):
    db = SessionLocal()
    if person_id:
        photos = (
            db.query(Photo)
            .join(Person, Person.photo_id == Photo.item_id)
            .filter(Person.person_id == person_id)
            .order_by(func.random())
            .limit(limit)
            .all()
        )
    else:
        photos = db.query(Photo).order_by(func.random()).limit(limit).all()
    return [{"filename": photo.filename, "id": photo.item_id} for photo in photos]

def randam_pick_from_album_database(album_id=None, limit=30):
    db = SessionLocal()
    if album_id:
        photos = (
            db.query(Photo)
            .join(Person, Person.photo_id == Photo.item_id)
            .filter(Person.person_id == album_id)
            .order_by(func.random())
            .limit(limit)
            .all()
        )
    else:
        photos = db.query(Photo).order_by(func.random()).limit(limit).all()
    return [{"filename": photo.filename, "id": photo.item_id} for photo in photos]
