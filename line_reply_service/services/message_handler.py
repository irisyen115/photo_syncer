# services/message_handler.py
import os
import json
import threading
from linebot.models import FlexSendMessage
from utils.flex_message_builder import build_face_bubbles, get_album_name_input_options
from services.upload_service import do_upload
from config.config import Config
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

session = requests.Session()

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

user_states = {}

def get_people_list(session):
    faces = []
    try:
        response = session.get(f"{Config.SERVER_URL}/api/upload/update_people", verify=False, timeout=10)
        if response.status_code == 200:
            try:
                faces = response.json()
                logging.info(f"成功從遠端服務獲取 {len(faces)} 人物資料")
            except Exception as e:
                logging.error(f"解析 JSON 時發生錯誤: {e}")
                return []

            if not isinstance(faces, list):
                logging.error(f"⚠️ 回傳格式錯誤，預期為 list，但實際為 {type(faces)}，內容為: {faces}")

                return []
        else:
            logging.warning(f"請求 update_people 失敗，HTTP {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"連接遠端服務時發生錯誤: {e}")

    return faces

people_cache = []
cache_lock = threading.Lock()

def preload_faces():
    global people_cache
    new_faces = get_people_list(session)
    with cache_lock:
        people_cache = new_faces

threading.Thread(target=preload_faces).start()

def get_cached_faces():
    global people_cache
    with cache_lock:
        cache_empty = not people_cache
    if cache_empty:
        new_faces = get_people_list(session)
        with cache_lock:
            people_cache = new_faces
    with cache_lock:
        return people_cache.copy()

def get_album_list(token, user_id):
    requests.post(
        f"{Config.SERVER_URL}/api/upload/list_albums",
        params={"token": token},
        json={"user_id": user_id}
    )

def handle_message(user_id, message_text, session, session_data, token):
    try:
        state = user_states.get(user_id, {})
        faces = get_cached_faces()

        if not faces:
            return "⚠️ 無法取得人物列表，請稍後再試。"

        if message_text == "使用自訂參數":
            return handle_custom_parameters(user_id, faces)

        elif message_text == "我要上傳照片":
            return handle_start_upload(user_id, faces)

        if message_text == "列出我的相簿":
            return handle_list_albums(user_id, token)

        elif message_text == "手動輸入相簿名":
            return "🔤 請輸入相簿名稱："

        if state.get("step") == "ask_person":
            return handle_person_selection(user_id, message_text, state, session, session_data, token)

        elif state.get("step") == "ask_google_album_name":
            return handle_album_name_input(user_id, message_text, state)

        elif state.get("step") == "ask_count":
            return handle_photo_count_input(user_id, message_text, state, session, session_data, token)

        return "請輸入「我要上傳照片」來開始相簿上傳流程。"

    except Exception as e:
        logging.error(e)
        return "⚠️ 發生錯誤，請稍後再試。"

def handle_list_albums(user_id, token):
    threading.Thread(target=get_album_list, args=(token, user_id)).start()
    return "📂 正在列出所有相簿，請稍候..."

def handle_custom_parameters(user_id, faces):
    user_states[user_id] = {"step": "ask_person"}
    carousel = {"type": "carousel", "contents": build_face_bubbles(faces)}
    return FlexSendMessage(alt_text="請選擇人物上傳照片", contents=carousel)


def handle_start_upload(user_id, faces):
    if not isinstance(faces, list):
        logging.error(f"⚠️ faces is not a list, type: {type(faces)}")
        return "⚠️ 無法取得人物列表，請稍後再試。"

    user_states[user_id] = {
        "step": "ask_person",
        "album_name": "",
        "num_photos": 5
    }

    carousel = {"type": "carousel", "contents": build_face_bubbles(faces)}

    for i, bubble in enumerate(carousel.get("contents", [])):
        contents = bubble.get("body", {}).get("contents", [])
        for j, content in enumerate(contents):
            if content is None:
                logging.error(f"Null element found in contents[{i}].body.contents[{j}]")

    return FlexSendMessage(alt_text="請選擇人物上傳照片", contents=carousel)


def handle_person_selection(user_id, message_text, state, session, session_data, token):
    if message_text.startswith("上傳 "):
        person_id = message_text.split("上傳 ")[1].strip()
        if not person_id.isdigit():
            return "❌ 請提供有效的人物 ID，例如：22492"

        state["person_id"] = person_id
        if "album_name" in state and "num_photos" in state:
            state["step"] = "uploading"
            user_states[user_id] = state
            threading.Thread(
                target=do_upload,
                args=(state["person_id"], state["album_name"], state["num_photos"], user_id, session, session_data, user_states, token)
            ).start()
            return f"✅ 收到資訊！正在上傳 {state['num_photos']} 張照片到相簿，請稍候..."
        else:
            state["step"] = "ask_google_album_name"
            return get_album_name_input_options()
    else:
        return "請點選選單上的「選擇」按鈕選擇人物。"


def handle_album_name_input(user_id, message_text, state):
    state["album_name"] = message_text
    state["step"] = "ask_count"
    user_states[user_id] = state
    return "🔢 請提供要上傳的照片數量（例如：10）："


def handle_photo_count_input(user_id, message_text, state, session, session_data, token):
    if not message_text.isdigit():
        return "❌ 請輸入正確的數字"
    num_photos = int(message_text)

    state["num_photos"] = num_photos
    state["step"] = "uploading"
    user_states[user_id] = state

    threading.Thread(
        target=do_upload,
        args=(state["person_id"], state["album_name"], state["num_photos"], user_id, session, session_data, user_states, token)
    ).start()
    return f"✅ 收到資訊！正在上傳 {state['num_photos']} 張照片到相簿，請稍候..."
