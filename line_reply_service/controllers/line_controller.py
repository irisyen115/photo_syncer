from flask import Blueprint, request, jsonify
import requests
from services.line_service import handle_webhook
import traceback
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

line_bp = Blueprint("line_bp", __name__)
session = requests.session()


@line_bp.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)  # 強制解析 json，避免拿到字串
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        result = handle_webhook(data, session)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in /api/webhook: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
