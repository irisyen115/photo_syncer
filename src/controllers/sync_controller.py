from flask import Blueprint, request, jsonify
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
    sync_date = sync_photos_for_person(person_id, db).get_json()
    requests.post(
        f"{Config.SERVER_URL}/api/line/notify",
        json={
            "message": f"同步完成，最新照片拍攝時間{sync_date['latest_photo']['shooting_time']}",
            "token": token
        }
    )
    return jsonify({'latest_photo': sync_date})

@sync_bp.route("/sync_interval_time_photos", methods=['POST'])
def get_interval_time_photos():
    token = request.args.get('token')
    data = request.get_json()
    person_id = data['personID']
    start_time = data['start_time']
    end_time = data['end_time']
    start_time = datetime.strptime(start_time, "%Y-%m-%d")
    end_time = datetime.strptime(end_time, "%Y-%m-%d")
    sync_photos_for_person(person_id, SessionLocal())

    photo_time = autonomy_get_interval_time_person(person_id, start_time, end_time)
    logging.error(f"拍攝照片時間分別為：{photo_time}")
    return jsonify({'latest_photo': data})
