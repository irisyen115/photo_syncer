# service.py
import os
import requests
import urllib3
from models.database import SessionLocal
from models.photo import Photo

# 設定
BASE_URL = os.getenv('SYNO_URL', 'https://192-168-50-162.rbxhome.direct.quickconnect.to:5001')
ACCOUNT = os.getenv('SYNO_ACCOUNT', 'mtyen')
PASSWORD = os.getenv('SYNO_PASSWORD', 'Iris0115')
FID = os.getenv('SYNO_FID', '20caeeda495760e9963c9fc677b9d2a1')
TIMEZONE = os.getenv('SYNO_TIMEZONE', '+08:00')
DOWNLOAD_DIR = "/app/downloaded_albums"

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


def list_photos(auth, album_id, offset=0, limit=91):
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


def download_photo(auth, item, save_path=None):
    token = auth['data']['synotoken']
    item_id = item['id']
    filename = item['filename']
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.mov', '.avi']:
        print(f"❌ Unsupported type: {filename}")
        return

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

def save_photo_to_db(item_id, filename, album_id=None, shooting_time=None, saved_path=None):
    db = SessionLocal()
    try:
        if db.query(Photo).filter_by(item_id=item_id).first():
            return
        db.add(Photo(
            item_id=item_id,
            filename=filename,
            album_id=album_id,
            shooting_time=shooting_time,
            saved_path=saved_path
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ DB error: {e}")
    finally:
        db.close()
