from flask import Blueprint, request, jsonify
from utils.session_utils import user_sessions
from utils.flex_message_builder import send_flex_album
from config.config import Config
from linebot import LineBotApi
import requests
from services.message_handler import user_states

album_bp = Blueprint("album_bp", __name__)
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

@album_bp.route("/album", methods=["POST"])
def get_albums():
    data = request.get_json(force=True)
    if not data or "token" not in data:
        return jsonify({"error": "Invalid JSON or missing 'token'"}), 400

    token = data["token"]
    album_titles = data.get("album_titles", [])
    covers = data.get("covers", [])
    user_id = user_sessions.get(token)

    if not user_id:
        return jsonify({"error": "User ID not found in session"}), 400

    try:
        if not album_titles:
            return jsonify({"error": "No albums found"}), 400
        if not covers:
            return jsonify({"error": "No covers found"}), 400
        line_bot_api.push_message(user_id, send_flex_album(album_titles, covers))
        user_states[user_id]["step"] = "ask_google_album_name"
    except requests.RequestException as e:
        return jsonify({"error": "Failed to send LINE message"}), 500
    except Exception as e:
        return jsonify({"error": "Failed to send LINE message"}), 500

    return jsonify({"albums": album_titles}), 200