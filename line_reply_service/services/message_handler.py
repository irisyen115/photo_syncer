# services/message_handler.py
import os
import json
import threading
from linebot.models import FlexSendMessage
from utils.flex_message_builder import build_face_bubbles, get_album_name_input_options, build_payload
from services.upload_service import do_upload
from config.config import Config
import logging
import requests
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction

load_dotenv()

session = requests.Session()

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

user_states = {}

def notify_user(user_id, message):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except Exception as e:
        logging.error(f"推送訊息給 {user_id} 時失敗: {e}")

def get_faces(session, user_id):
    try:
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

def handle_message(user_id, message_text, session, session_data, token):
    try:
        state = user_states.get(user_id, {})

        if message_text == "使用自訂參數":
            return handle_custom_parameters(user_id)

        elif message_text == "我要上傳照片":
            return handle_start_upload(user_id)

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

def handle_custom_parameters(user_id):
    state = user_states.get(user_id, {})
    faces = state.get("faces", [])
    faces_loading = state.get("faces_loading", False)

    if not faces:
        if not faces_loading:
            state.update({
                "step": "ask_person",
                "faces_loading": True
            })
            threading.Thread(target=get_faces, args=(session, user_id)).start()
            user_states[user_id] = state
            logging.error(f"user_states:{user_states[user_id]}")
            return "⚠️ 正在取得人物列表，完成後會通知您。"
        else:
            return "⚠️ 人物列表仍在載入中，請稍候..."

    state["step"] = "ask_person"
    user_states[user_id] = state

    carousel = {"type": "carousel", "contents": build_face_bubbles(faces)}
    return FlexSendMessage(alt_text="請選擇人物上傳照片", contents=carousel)

def handle_start_upload(user_id):
    state = user_states.setdefault(user_id, {})
    faces = state.get("faces", [])
    faces_loading = state.get("faces_loading", False)

    if not faces:
        if not faces_loading:
            state.update({
                "step": "ask_person",
                "faces_loading": True
            })
            threading.Thread(target=get_faces, args=(session, user_id)).start()
            user_states[user_id] = state
            return "⚠️ 正在取得人物列表，完成後會通知您。"
        else:
            return "⚠️ 人物列表仍在載入中，請稍候..."

    # ✅ 正確保留原本 state
    state["step"] = "ask_person"
    user_states[user_id] = state

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
            logging.error(f"user_states {state['step']}")
            return get_album_name_input_options()
    else:
        return "請點選選單上的「選擇」按鈕選擇人物。"

def handle_album_name_input(user_id, message_text, state):
    state["album_name"] = message_text
    state["step"] = "ask_count"
    user_states[user_id] = state
    message = TextSendMessage(
        text="請選擇要上傳的照片張數：",
        quick_reply=QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="5 張", text="5")),
            QuickReplyButton(action=MessageAction(label="50 張", text="50")),
            QuickReplyButton(action=MessageAction(label="100 張", text="100")),
            QuickReplyButton(action=MessageAction(label="200 張", text="200")),
        ])
    )
    try:
        return [message.as_json_dict()]
    except requests.RequestException as e:
        logging.error(f"回覆使用者時發生錯誤: {e}")

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
