import time
import json
from config.config import Config
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def do_upload(person_id, album_name, num_photos, user_id, session, session_data, user_states):
    try:
        payload = {
            "personID": person_id,
            "albumID": None,
            "albumName": album_name,
            "numPhotos": num_photos
        }


        for attempt in range(5):
            response = session.post(f"{Config.IRIS_DS_SERVER_URL}/api/upload/sync_photos", json=payload)

            logging.error("Session data: %s", dict(session))

            if response.status_code == 429:
                wait_time = 2 ** attempt
                logging.error(f"⚠️ 遇到 429，等待 {wait_time} 秒再重試...")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                logging.error(f"❌ sync_photos 回傳非 200：{response.status_code}, {response.text}")
                break

            response2 = session.get(f"{Config.IRIS_DS_SERVER_URL}/api/upload/upload_records", verify=False)

            if response2.status_code != 200:
                logging.error(f"❌ upload_records 失敗！Status: {response2.status_code}, Response: {response2.text}")
                break

            print("✅ 成功取得上傳紀錄！", response2.json())
            break

        try:
            resp_json = response.json()
        except Exception:
            logging.error("無法解析 POST 回應 JSON")
            return

        user_states.pop(user_id, None)
        session_data["last_action"] = None
        session_path = f"sessions/{user_id}.json"
        with open(session_path, "w") as f:
            json.dump(session_data, f)
        logging.error(f"✅ User {user_id} has completed the upload process.")

    except Exception as e:
        logging.error(f"❌ Upload failed: {e}")

