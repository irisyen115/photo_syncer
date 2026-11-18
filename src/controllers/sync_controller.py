from flask import Blueprint, request, jsonify, current_app
import threading
from service.sync_service import sync_photos_for_person
import logging
import requests
from config.config import Config
from service.sync_service import autonomy_get_interval_time_person
from models.database import SessionLocal
from datetime import datetime

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

sync_bp = Blueprint('sync_bp', __name__)

@sync_bp.route("/sync_latest_photo/<int:person_id>", methods=["GET"])
def get_latest_photo_status_for_person(person_id):
    token = request.args.get('token')
    db = SessionLocal()
    sync_date = sync_photos_for_person(person_id, db)
    latest_photo = sync_date.get('latest_photo')
    if latest_photo:
        message = f"同步完成，最新照片拍攝時間{latest_photo['shooting_time']}"
    else:
        message = f"同步完成，但找不到 person_id={person_id} 的照片"
    requests.post(
        f"{Config.SERVER_URL}/api/line/notify",
        json={
            "message": message,
            "token": token
        }
    )
    status_code = 200 if latest_photo else 404
    return jsonify({'latest_photo': sync_date}), status_code

@sync_bp.route("/sync_interval_time_photos", methods=['POST'])
def get_interval_time_photos():
    token = request.args.get('token')
    data = request.get_json()
    person_id = data['personID']
    start_time = data['start_time']
    end_time = data['end_time']
    try:
        start_time = datetime.strptime(start_time, "%Y-%m-%d")
        # 結束日包含當天整天
        end_time = datetime.combine(datetime.strptime(end_time, "%Y-%m-%d").date(), datetime.max.time())
    except (TypeError, ValueError):
        return jsonify({"error": "start_time / end_time 需為 YYYY-MM-DD"}), 400

    # 同步要跑 1 分鐘以上，超過 nginx 的 60 秒 proxy timeout（會回 504），所以改到背景執行
    app = current_app._get_current_object()

    def run():
        with app.app_context():
            try:
                sync_photos_for_person(person_id, SessionLocal())
                photo_time = autonomy_get_interval_time_person(person_id, start_time, end_time)
                logging.error(f"[區間同步] PersonID={person_id} 完成，新增/確認 {len(photo_time)} 張")
            except Exception:
                logging.exception(f"[區間同步] PersonID={person_id} 失敗")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'latest_photo': data, 'message': '區間同步已在背景執行'})
