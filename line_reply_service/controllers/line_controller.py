from flask import Blueprint, request, jsonify
import requests
from services.line_service import handle_webhook
import traceback
import logging
from config.config import Config
from linebot import LineBotApi
from utils.flex_message_builder import send_flex_album, build_face_bubbles
from cachetools import TTLCache
import secrets
from services.message_handler import user_states

# 設定 Line Bot API
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

line_bp = Blueprint("line_bp", __name__)
user_sessions = TTLCache(maxsize=1000, ttl=1800)


def generate_token(length=32):
    """產生指定長度的安全隨機 token"""
    return secrets.token_hex(length // 2)

@line_bp.route("/webhook", methods=["GET", "POST"])
def webhook():
    try:
        logging.error("Received webhook request")
        data = request.get_json(force=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        logging.error(f"Webhook result: {data}")
        event = data["events"][0]
        uid = event["source"]["userId"]
        token = generate_token()
        if uid:
            user_sessions[token] = uid

        result = handle_webhook(data, token)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in /api/webhook: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@line_bp.route("/notify", methods=["POST"])
def notify():
    try:
        data = request.get_json(force=True)
        message = data["message"]
        token = data["token"]
        user_id = user_sessions.get(token)
        logging.error(f"User ID from token {token}: {user_id}")
        if not user_id:
            logging.error("User ID not found in session")
            return jsonify({"error": "User ID not found in session"}), 400

        payload = {
            "to": user_id,
            "messages": [{"type": "text", "text": message}]
        }
        headers = {
            "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.post("https://api.line.me/v2/bot/message/push", json=payload, headers=headers)
        logging.error(f"Notify response: {response.status_code}, {response.text}")
        if response.status_code != 200:
            logging.error(f"Failed to send message: {response.status_code}, {response.text}")
            return jsonify({"error": "Failed to send message"}), 500
        response.raise_for_status()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Error in /notify: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@line_bp.route("/album", methods=["POST"])
def get_albums():
    data = request.get_json(force=True)
    if not data or "token" not in data:
        return jsonify({"error": "Invalid JSON or missing 'token'"}), 400

    token = data["token"]
    album_titles = data.get("album_titles", [])
    covers = data.get("covers", [])
    user_id = user_sessions.get(token)
    logging.error(f"album_titles: {album_titles}, covers: {covers}, user_id: {user_id}")

    if not user_id:
        logging.error("User ID not found in session")
        return jsonify({"error": "User ID not found in session"}), 400

    try:
        if not album_titles:
            logging.error("No albums found to send")
            return jsonify({"error": "No albums found"}), 400
        if not covers:
            logging.error("No covers found to send")
            return jsonify({"error": "No covers found"}), 400
        line_bot_api.push_message(user_id, send_flex_album(album_titles, covers))
        user_states[user_id]["step"] = "ask_google_album_name"
    except requests.RequestException as e:
        logging.exception(f"Failed to send LINE message: {e}")
        return jsonify({"error": "Failed to send LINE message"}), 500
    except Exception as e:
        logging.exception(f"Failed to send LINE message: {e}")
        return jsonify({"error": "Failed to send LINE message"}), 500

    return jsonify({"albums": album_titles}), 200

@line_bp.route("/faces", methods=["POST"])
def get_face_list():
    data = request.get_json(force=True)
    user_id = data["user_id"]
    faces = data["faces"]
    try:
        line_bot_api.push_message(user_id, build_face_bubbles(faces=faces))
    except Exception as e:
        logging.error(f"Failed to send LINE message: {e}")
        return jsonify({"error": "Failed to send LINE message"}), 500
    return jsonify({"faces": faces}), 200