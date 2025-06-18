from flask import Blueprint, request, jsonify
from utils.session_utils import get_user_id_from_token
from config.config import Config
from linebot import LineBotApi
from linebot.models import TextSendMessage

notify_bp = Blueprint("notify_bp", __name__)
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

@notify_bp.route("/notify", methods=["POST"])
def notify():
    try:
        data = request.get_json(force=True)
        message = data["message"]
        token = data["token"]
        user_id = get_user_id_from_token(token)
        if not user_id:
            return jsonify({"error": "User ID not found in session"}), 400
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except Exception as e:
        return jsonify({"error": str(e)}), 500