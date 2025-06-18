import time
import json
from config.config import Config
import logging
from linebot import LineBotApi
from linebot.models import TextSendMessage
import requests

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

def do_upload(person_id, album_name, num_photos, user_id, session, session_data, user_states, token):
    try:
        payload = {
            "personID": person_id,
            "albumID": None,
            "albumName": album_name,
            "numPhotos": num_photos,
            "token": token
        }

        for attempt in range(5):
            response = session.post(f"{Config.SERVER_URL}/api/upload/sync_photos", params = {"token":token}, json=payload)

            if response.status_code != 200:
                logging.error(f"❌ sync_photos 回傳非 200：{response.status_code}, {response.text}")
                line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ 同步失敗，請稍後再試。錯誤碼: {response.status_code}"))
                break

            if response.status_code == 200:
                data = response.json()
                logging.error(f"已上傳照片數: {data.get('uploaded_photos')}")
                logging.error(f"同步花費時間: {data.get('time_spent')} 秒")
                line_bot_api.push_message(user_id, TextSendMessage(text=f"📄 同步報告：{data.get('message')}"))

            response2 = session.get(f"{Config.SERVER_URL}/api/upload/upload_records", params={"personID": person_id}, verify=False)

            if response2.status_code != 200:
                logging.error(f"❌ upload_records 失敗！Status: {response2.status_code}, Response: {response2.text}")
                break
            break

        user_states.pop(user_id, None)
        session_data["last_action"] = None
        session_path = f"sessions/{user_id}.json"
        with open(session_path, "w") as f:
            json.dump(session_data, f)
        logging.error(f"✅ User {user_id} has completed the upload process.")

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ 請求錯誤: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"❌ JSON 解碼失敗: {e}")
    except Exception as e:
        logging.error(f"❌ 其他錯誤: {e}")

def notify_user(user_id, message):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except Exception as e:
        logging.error(f"推送訊息給 {user_id} 時失敗: {e}")

def get_faces(session, user_id, user_states):
    try:
        logging.error(f"🚨 get_faces 被觸發！目前 state: {user_states.get(user_id)}")

        response = session.get(f"{Config.SERVER_URL}/api/upload/update_people", params={"user_id": user_id})
        if response.status_code == 200:
            faces = response.json()
            state = user_states.setdefault(user_id, {})
            state["faces"] = faces
            notify_user(user_id, f"✅ 人物列表已更新，共 {len(faces)} 位。")
    except Exception as e:
        logging.error(f"取得人物列表時錯誤: {e}")
        notify_user(user_id, "❌ 取得人物列表時發生錯誤。")
    finally:
        user_states.setdefault(user_id, {})["faces_loading"] = False

def get_album_list(token, user_id):
    requests.post(
        f"{Config.SERVER_URL}/api/upload/list_albums",
        params={"token": token},
        json={"user_id": user_id}
    )
