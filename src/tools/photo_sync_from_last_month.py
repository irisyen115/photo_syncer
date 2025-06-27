from lib.synology import list_people, login
import os
from service.sync_service import autonomy_get_interval_time_person, update_sync_status
from models.database import SessionLocal
from models.person import Person
from datetime import datetime
from dateutil.relativedelta import relativedelta

one_month_ago = datetime.now() - relativedelta(months=1)

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
    print(autonomy_get_interval_time_person(person_id=person['id'], start_dt=one_month_ago, end_dt=datetime.now()))