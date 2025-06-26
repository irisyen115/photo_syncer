from flask import Blueprint, request, jsonify, session, redirect
from service.upload_service import handle_upload, update_people_list
from service.user_service import get_user_info_service
from lib.google import authenticate
from lib.synology import login
from config.config import Config
ACCOUNT = Config.SYNO_ACCOUNT
PASSWORD = Config.SYNO_PASSWORD
FID = Config.SYNO_FID
TIMEZONE = Config.SYNO_TIMEZONE
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload_photos', methods=['GET', 'POST'])
def upload_photos():
    creds = authenticate()
    return handle_upload(request, creds, session)


@upload_bp.route('/update_people', methods=['GET'])
def update_people_list_controller():
    try:
        auth = login(ACCOUNT, PASSWORD, FID, TIMEZONE)
        if not auth:
            logging.error("❌ Synology 登入失敗")
            return jsonify({"error": "Synology 登入失敗"}), 401

        session['auth'] = auth
        user_id = request.args.get("user_id")
        logging.error(f"Synology 登入成功，SID: {auth['data']['sid']}, SynoToken: {auth['data']['synotoken']}")
        logging.error(f"{session['auth']}")
        if not auth:
            logging.error("⚠️ 使用者未登入，無法更新人員列表")
            return jsonify({"error": "使用者未登入"}), 401
        people = update_people_list(auth=auth, user_id=user_id)
        if not isinstance(people, list):
            logging.error(f"⚠️ update_people_list() 回傳非 list：{type(people)}，內容為：{people}")
            return jsonify({"error": "內部錯誤：非預期格式"}), 500
        return jsonify(people)
    except Exception as e:
        logging.exception("⚠️ 更新人員列表時發生例外錯誤")
        return jsonify({"error": str(e)}), 500
