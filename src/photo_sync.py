from src.lib.synlogy import list_all_photos_by_person
from main import auth, PERSON_ID

photo_list = list_all_photos_by_person(auth, person_id=PERSON_ID)
for photo in photo_list:
    print(photo['filename'])
