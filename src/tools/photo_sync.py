from lib.synology import list_people, login
from service.synology_service import list_all_photos_by_person, list_all_photos_by_album, save_photos_to_db_with_person, save_photos_to_db_with_album
from models.database import SessionLocal
from models.photo import Photo
from models.person import Person
from models.album import Album
import os

def get_latest_photo(person_id):
    all_photos = list_all_photos_by_person(auth, person_id)
    save_photos_to_db_with_person(all_photos, person_id)


auth = login(os.getenv("SYNO_ACCOUNT"), os.getenv("SYNO_PASSWORD"), os.getenv("SYNO_FID"), os.getenv("SYNO_TIMEZONE"))
persons = list_people(auth, 8)
person_ids = [person['id'] for person in persons]
for person in persons:
    get_latest_photo(person_id=person['id'])