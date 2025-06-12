from flask import Blueprint, request, jsonify, session, redirect
from service.sync_service import handle_sync, update_people_list
from service.user_service import get_user_info_service
from lib.google import authenticate
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/sync_photos', methods=['GET', 'POST'])
def sync_photos():
    creds = authenticate()
    return handle_sync(request, creds, session)

@sync_bp.route('/update_people', methods=['GET'])
def update_people_list_controller():
    try:
        people = update_people_list()
        if not isinstance(people, list):
            logging.error(f"⚠️ update_people_list() 回傳非 list：{type(people)}，內容為：{people}")
            return jsonify({"error": "內部錯誤：非預期格式"}), 500
        return jsonify(people)
    except Exception as e:
        logging.exception("⚠️ 更新人員列表時發生例外錯誤")
        return jsonify({"error": str(e)}), 500
