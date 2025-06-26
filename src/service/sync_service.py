from models.database import SessionLocal
from models.person import Person
from models.sync_status import SyncStatus
from flask import jsonify
from lib.synology import login
from service.synology_service import list_all_photos_by_person_with_internal_time, save_photos_to_db_with_person
from models.database import SessionLocal
from models.person import Person
from models.sync_status import SyncStatus
import os
from datetime import datetime

def sync_photos_for_person(person_id, db):
    try:
        sync_photos_since_last_time(person_id)
        person_records = db.query(Person).filter_by(person_id=person_id).all()

        if not person_records:
            return jsonify({
                "person_id": person_id,
                "latest_photo": None,
                "message": "No photo found for this person_id"
            }), 404

        latest_photo = None
        for person in person_records:
            photo = person.get_latest_photo_by_person_id(db)
            if photo and (not latest_photo or photo.shooting_time > latest_photo.shooting_time):
                latest_photo = photo

        if not latest_photo:
            return jsonify({
                "person_id": person_id,
                "latest_photo": None,
                "message": "No photos with valid shooting_time"
            }), 404

        update_sync_status(db, person_id, latest_photo)

        return jsonify({
            "person_id": person_id,
            "latest_photo": {
                "photo_id": latest_photo.id,
                "filename": latest_photo.filename,
                "shooting_time": latest_photo.shooting_time
            },
        })
    finally:
        db.close()

def update_sync_status(db, person_id, photo):
    status = db.query(SyncStatus).filter_by(person_id=person_id).first()
    if not status:
        status = SyncStatus(person_id=person_id)
        db.add(status)

    status.last_synced_photo_id = photo.id
    status.last_synced_time = photo.shooting_time
    db.commit()

def autonomy_get_interval_time_person(person_id, start_dt, end_dt):
    auth = login(os.getenv("SYNO_ACCOUNT"), os.getenv("SYNO_PASSWORD"), os.getenv("SYNO_FID"), os.getenv("SYNO_TIMEZONE"))
    photo_json = list_all_photos_by_person_with_internal_time(auth, person_id, start_dt, end_dt)
    save_photos_to_db_with_person(photo_json, person_id)
    return [photo['time'] for photo in photo_json]


def sync_photos_since_last_time(person_id, end_dt=datetime.now()):
    db = SessionLocal()
    auth = login(os.getenv("SYNO_ACCOUNT"), os.getenv("SYNO_PASSWORD"), os.getenv("SYNO_FID"), os.getenv("SYNO_TIMEZONE"))
    previous_status = db.query(SyncStatus).filter_by(person_id=22492).first()
    start_dt = previous_status.last_synced_time
    photo_json = list_all_photos_by_person_with_internal_time(auth, person_id, start_dt, end_dt)
    save_photos_to_db_with_person(photo_json, person_id)
    return [photo['time'] for photo in photo_json]