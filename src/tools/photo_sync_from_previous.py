from lib.synology import list_people, login
import os
from service.sync_service import sync_photos_since_last_time, update_sync_status
from models.database import SessionLocal
from models.person import Person

auth = login(os.getenv("SYNO_ACCOUNT"), os.getenv("SYNO_PASSWORD"), os.getenv("SYNO_FID"), os.getenv("SYNO_TIMEZONE"))
persons = list_people(auth, 8)
person_ids = [person['id'] for person in persons]
db = SessionLocal()
latest_photo = None
for person in persons:
    person_records = db.query(Person).filter_by(person_id=person['id']).all()
    for person_record in person_records:
        photo = person_record.get_latest_photo_by_person_id(db)
        if photo and (not latest_photo or photo.shooting_time > latest_photo.shooting_time):
            latest_photo = photo
    update_sync_status(db, person['id'], latest_photo)
    print(sync_photos_since_last_time(person_id=person['id']))