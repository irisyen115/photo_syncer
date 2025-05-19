import os
from dotenv import load_dotenv
import requests
import urllib3
from models.database import SessionLocal
from models.photo import Photo
from datetime import datetime
load_dotenv()

# Configuration
BASE_URL = os.getenv('SYNO_URL', 'https://192-168-50-162.rbxhome.direct.quickconnect.to:5001')
ACCOUNT = os.getenv('SYNO_ACCOUNT', 'mtyen')
PASSWORD = os.getenv('SYNO_PASSWORD', 'Iris0115')
FID = os.getenv('SYNO_FID', '20caeeda495760e9963c9fc677b9d2a1')
TIMEZONE = os.getenv('SYNO_TIMEZONE', '+08:00')
download_dir = "/app/downloaded_albums"
# Disable SSL warnings (for self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a session to persist cookies
session = requests.Session()

# Common headers for all requests
HEADERS = {
    'accept': '*/*',
    'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': BASE_URL,
    'referer': f"{BASE_URL}/",
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/135.0.0.0 Safari/537.36'
}


def get_auth_type(account: str) -> dict:
    """
    Step 1: Query supported authentication types.
    Returns the JSON response data.
    """
    url = f"{BASE_URL}/webapi/entry.cgi"
    payload = {
        'api': 'SYNO.API.Auth.Type',
        'method': 'get',
        'version': '1',
        'account': account
    }
    resp = session.post(url, headers=HEADERS, data=payload, verify=False)
    resp.raise_for_status()

    return resp.json()


def login(account: str, password: str, fid: str, timezone: str) -> dict:
    """
    Step 2: Perform login and return auth JSON containing synotoken.
    """
    url = f"{BASE_URL}/webapi/entry.cgi?api=SYNO.API.Auth"
    payload = {
        'api': 'SYNO.API.Auth',
        'version': '7',
        'method': 'login',
        'session': 'webui',
        'tabid': '60109',
        'enable_syno_token': 'yes',
        'account': account,
        'passwd': password,
        'logintype': 'local',
        'otp_code': '',
        'enable_device_token': 'no',
        'timezone': timezone,
        'rememberme': '0',
        'client': 'browser',
        'fid': fid
    }
    resp = session.post(url, headers=HEADERS, data=payload, verify=False)
    resp.raise_for_status()
    auth_data = resp.json()
    if 'data' not in auth_data:
        auth_data['data'] = {}

    if 'synotoken' not in auth_data['data']:
        synotoken_from_cookie = session.cookies.get('synotoken')
        if synotoken_from_cookie:
            auth_data['data']['synotoken'] = synotoken_from_cookie

    return auth_data


def list_albums(auth: dict) -> dict:
    """
    List all albums using the synotoken from auth.
    Returns the JSON response data.
    """
    token = auth.get('data', {}).get('synotoken')
    if not token:
        raise ValueError('No synotoken found in auth response')

    url = f"{BASE_URL}/webapi/entry.cgi"
    params = {'SynoToken': token}
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
    resp = session.post(url, headers=HEADERS, params=params, data=payload, verify=False)
    resp.raise_for_status()
    return resp.json()

def list_photos(auth: dict, album_id: int, offset=0, limit=91):
    token = auth.get('data', {}).get('synotoken')
    if not token:
        raise ValueError('No synotoken found in auth response')

    url = f"{BASE_URL}/webapi/entry.cgi/SYNO.Foto.Browse.Item"

    headers = HEADERS.copy()
    headers['x-syno-token'] = token
    headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

    payload = {
        "api": "SYNO.Foto.Browse.Item",
        "method": "list",
        "version": "4",
        "additional": '["thumbnail","resolution","orientation","video_convert","video_meta","provider_user_id"]',
        "offset": str(offset),
        "limit": str(limit),
        "sort_by": "takentime",
        "sort_direction": "asc",
        "album_id": str(album_id),
    }

    response = session.post(url, headers=headers, data=payload, verify=False)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching photos: {response.status_code} {response.text}")

import mimetypes

def download_photo(auth: dict, item: dict, save_path: str) -> None:
    """
    Download a photo or video based on item metadata.
    Saves to download_dir with original filename.
    """
    token = auth.get('data', {}).get('synotoken')
    if not token:
        raise ValueError('No synotoken found in auth response')

    item_id = item['id']
    filename = item['filename']
    mime_type = item.get('additional', {}).get('type', '')

    # 可依副檔名或 mime type 判斷是否為圖片
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.mov', '.avi']:
        print(f"Skipped unsupported file type: {filename}")
        return

    os.makedirs(download_dir, exist_ok=True)
    save_path = os.path.join(download_dir, filename)

    # 建立下載 URL
    url = f"{BASE_URL}/webapi/entry.cgi/{filename}"
    params = {'SynoToken': token}
    form_data = {
        'force_download': 'true',
        'item_id': f'[{item_id}]',
        'download_type': 'source',
        'api': 'SYNO.Foto.Download',
        'method': 'download',
        'version': '2'
    }

    try:
        resp = session.post(
            url,
            headers={**HEADERS, 'content-type': 'application/x-www-form-urlencoded'},
            params=params,
            data=form_data,
            verify=False
        )
        resp.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(resp.content)

        print(f"✅ Downloaded {filename} -> {save_path}")

    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")

def save_photo_to_db(item_id, filename, album_id=None, takentime=None, saved_path=None):
    db_session  = SessionLocal()
    try:
        item = db_session.query(Photo).filter_by(item_id=item_id).first()
        if item:
            return

        photo = Photo(
            item_id=item_id,
            filename=filename,
            album_id=album_id,
            takentime=takentime,
            saved_path=saved_path
        )
        db_session.add(photo)
        db_session.commit()
        print(f"已儲存：{filename}")
    except Exception as e:
        db_session.rollback()
        print(f"錯誤：{e}")
    finally:
        db_session.close()


if __name__ == '__main__':
    # Example usage
    auth = login(ACCOUNT, PASSWORD, FID, TIMEZONE)

    token = auth.get('data', {}).get('synotoken')
    albums = list_albums(auth)
    # print('Albums:', albums)
    # # Get the first album ID
    # for album in albums['data']['list']:
    #     print(album['name'], album['id'])

    # List photos in the first album
    photos = list_photos(auth, album_id=albums['data']['list'][2]['id'])
    print('Photos:', photos)
    for photo in photos['data']['list']:
        print(photo)
        print(photo_id := photo['id'])
        print(photo['filename'])

    for i in range(len(photos['data']['list'])):
        save_photo_to_db(
            item_id=photos['data']['list'][i]['id'],
            filename=photos['data']['list'][i]['filename'],
            album_id=albums['data']['list'][2]['id'],
            takentime=datetime.fromtimestamp(photos['data']['list'][i]['time']),
            saved_path=f"/app/downloaded_albums/{photos['data']['list'][i]['filename']}"
        )

    db_session  = SessionLocal()
    try:
        for photo in photos['data']['list']:
            item = db_session.query(Photo).filter_by(item_id=photo['id']).first()

            if not item:
                print(f"❗ 找不到資料庫記錄：{photo['filename']}")
                continue
            if not item.saved_path:
                print(f"⚠️ 無 saved_path：{photo['filename']}")
                continue
            download_photo(auth, photo, save_path=item.saved_path)
    finally:
        db_session.close()
