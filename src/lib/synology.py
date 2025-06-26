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
from models.exist_album import ExistAlbum
from models.exist_person import ExistPerson
import urllib.parse
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

BASE_URL = os.getenv('SYNO_URL')
FID = os.getenv('SYNO_FID')
TIMEZONE = os.getenv('SYNO_TIMEZONE')
DOWNLOAD_DIR = os.getenv('SYNO_DOWNLOAD_DIR')
WEB_STATION_URL = 'https://192-168-50-163.irisyen115.direct.quickconnect.to:5001'

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

    if not data.get("success"):
        logging.warning(f"❌ 登入失敗，回應內容：{data}")
        return None  # 或者 return {"error": "Login failed"} 視情況而定

    # 若成功就補上 synotoken / sid
    if 'data' not in data:
        data['data'] = {}
    if 'synotoken' not in data['data']:
        data['data']['synotoken'] = session.cookies.get('synotoken')
    sid = session.cookies.get("id") or session.cookies.get("_sid")
    data['data']['sid'] = sid
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
    logging.info(f"Fetching person with token: {token}")
    logging.info(f"Fetching person with ID: {person_id}")

    url = f"{BASE_URL}/webapi/entry.cgi/SYNO.Foto.Browse.Person"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": f"{BASE_URL}",
        "referer": f"{BASE_URL}/?launchApp=SYNO.Foto.AppInstance",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-syno-token": token
    }

    data = {
        "api": "SYNO.Foto.Browse.Person",
        "method": "get",
        "version": "1",
        "id": f'[{person_id}]',
        "additional": '["thumbnail"]'
    }

    cookies = auth.get('cookies', {})

    resp = session.post(url, headers=headers, data=data, cookies=cookies, verify=False)
    resp.raise_for_status()
    result = resp.json()

    if not result.get('success'):
        logging.error(f"Synology get_person API 回傳失敗: {result}")
        return None

    return result.get('data')


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

def list_people(auth, limit):
    token = auth['data']['synotoken']
    url = f"{BASE_URL}/webapi/entry.cgi"
    payload = {
        "api": "SYNO.Foto.Browse.Person",
        "method": "list",
        "version": "1",
        "offset": 0,
        "limit": limit,
        "sort_by": "name",
        "sort_direction": "asc",
        "additional": '["thumbnail"]'
    }
    resp = session.post(
        url,
        headers=HEADERS,
        params={'SynoToken': token},
        data=payload,
        verify=False
    )
    resp.raise_for_status()
    return resp.json()['data']['list']

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
        "person_id": person_id,
    }

    resp = session.post(url, headers=headers, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()['data']['list']

def list_photos_by_person_and_interval_time(auth, person_id, start_dt, end_dt, offset=0, limit=100):
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
        "start_time": int(start_dt.timestamp()),
        "end_time": int(end_dt.timestamp()),
        "person_id": person_id
    }

    resp = session.post(url, headers=headers, data=payload, verify=False)
    resp.raise_for_status()
    data = resp.json()

    return data['data']['list']


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

def thumb_photo(id, cache_key, auth):
    url = f'{BASE_URL}/synofoto/api/v2/p/Thumbnail/get?id={id}&cache_key="{cache_key}"&type="person"&SynoToken={auth["data"]["synotoken"]}'
    response = session.get(url, verify=False)
    response.raise_for_status()

    with open(f"/app/face_image/{id}.jpg", "wb") as f:
        f.write(response.content)

