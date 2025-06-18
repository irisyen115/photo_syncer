from flask import Blueprint, request, jsonify
import logging
from services.webhook_service import handle_webhook
from utils.session_utils import generate_token, user_sessions
import traceback

webhook_bp = Blueprint("webhook_bp", __name__)

@webhook_bp.route("/webhook", methods=["GET", "POST"])
def webhook():
    try:
        logging.error("Received webhook request")
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        uid = data["events"][0]["source"]["userId"]
        token = generate_token()
        if uid:
            user_sessions[token] = uid
        result = handle_webhook(data, token)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in /webhook: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
