from flask import Blueprint, request, jsonify
from utils.flex_message_builder import build_face_bubbles
from config.config import Config
from linebot import LineBotApi

line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

face_bp = Blueprint("face_bp", __name__)

@face_bp.route("/faces", methods=["POST"])
def get_face_list():
    data = request.get_json(force=True)
    user_id = data["user_id"]
    faces = data["faces"]
    try:
        line_bot_api.push_message(user_id, build_face_bubbles(faces=faces))
    except Exception as e:
        return jsonify({"error": "Failed to send LINE message"}), 500
    return jsonify({"faces": faces}), 200
