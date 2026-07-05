from lib.synology import list_photos_by_album, list_photos_by_person, list_photos_by_person_and_interval_time
from models.photo import Photo
from models.album import Album
from models.person import Person
from models.exist_album import ExistAlbum
from models.exist_person import ExistPerson
from models.photo_blacklist import PhotoBlacklist
from models.database import SessionLocal
from datetime import datetime
from sqlalchemy import func, inspect, select
from sqlalchemy.dialects.postgresql import insert
from config.config import Config
import os
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
DOWNLOAD_DIR = Config.SYNO_DOWNLOAD_DIR

def list_all_photos_by_album(auth, album_id):
    all_photos = []
    offset = 0
    limit = 100

    while True:
        photos = list_photos_by_album(auth, album_id, offset, limit)
        if not photos:
            break
        all_photos.extend(photos)
        offset += limit

    return all_photos

def list_all_photos_by_person(auth, person_id):
    all_photos = []
    offset = 0
    limit = 100

    while True:
        photos = list_photos_by_person(auth, person_id, offset, limit)
        if not photos:
            break
        all_photos.extend(photos)
        offset += limit

    return all_photos

def list_all_photos_by_person_with_internal_time(auth, person_id, start_time, end_time):
    all_photos = []
    offset = 0
    limit = 100

    while True:
        photos = list_photos_by_person_and_interval_time(auth, person_id, start_time, end_time, offset, limit)
        if not photos:
            break
        all_photos.extend(photos)
        offset += limit

    return all_photos

def save_photos_to_db_with_album(photo_list, album_id):
    db = SessionLocal()
    existing_ids = {
        p.item_id for p in db.query(Photo.item_id).filter(
            Photo.item_id.in_([p['id'] for p in photo_list])
        )
    }

    new_photos = []
    new_album = []

    for p in photo_list:
        if p['id'] not in existing_ids:
            photo = Photo(
                item_id=p['id'],
                filename=p['filename'],
                shooting_time=datetime.fromtimestamp(p['time']),
                saved_path=DOWNLOAD_DIR + p['filename'],
            )
            new_photos.append(photo)
        existing_pair = db.query(Album).filter_by(
            album_id=album_id,
            photo_id=p['id']
        ).first()

        if existing_pair is None:
            album = Album(album_id=album_id, photo_id=p['id'])
            new_album.append(album)
        else:
            album = existing_pair

        print(f"album: {album.album_photo_pair}")

    if new_album:
        db.bulk_save_objects(new_album)
        db.commit()

    if new_photos:
        db.bulk_save_objects(new_photos)
        db.commit()
    else:
        print("⚠️ 沒有新照片需要儲存")

def _find_unique_constraint_name_for_person_photo_pair(engine) -> str | None:
    insp = inspect(engine)
    uqs = insp.get_unique_constraints(Person.__tablename__)
    target_cols = {"person_id", "photo_id"}
    for uq in uqs:
        cols = set(uq.get("column_names") or [])
        if cols == target_cols and uq.get("name"):
            return uq["name"]
    return None


def fetch_scalar_list(db, stmt):
    return db.execute(stmt).scalars().all()

def save_photos_to_db_with_person(photo_list, person_id):
    db = SessionLocal()
    try:
        person_id_int = int(person_id)

        dedup = {}
        for p in photo_list:
            raw_id = p.get("id")
            if raw_id is None:
                continue
            pid = int(raw_id)
            dedup[pid] = p
        photo_list = list(dedup.values())

        if not photo_list:
            return

        photo_ids = [int(p["id"]) for p in photo_list]

        existing_photo_ids = set(fetch_scalar_list(
            db,
            select(Photo.item_id)
            .where(Photo.item_id.in_(photo_ids))
        ))

        existing_person_photo_ids = set(fetch_scalar_list(
            db,
            select(Person.photo_id)
            .where(
                Person.person_id == person_id_int,
                Person.photo_id.in_(photo_ids)
            )
        ))

        # existing_photo_ids = set(
        #     db.execute(select(Photo.item_id))
        #         .where(
        #             Photo.item_id.in_(photo_ids)
        #         ).scalars().all()
        #     )

        # existing_person_photo_ids = set(
        #     db.execute(
        #         select(Person.photo_id)
        #         .where(
        #             Person.person_id == person_id_int,
        #             Person.photo_id.in_(photo_ids)
        #         )
        #     ).scalars().all()
        # )

        photo_rows = []
        relation_rows = []

        for p in photo_list:
            photo_id = int(p["id"])

            if photo_id not in existing_photo_ids:
                photo_rows.append({
                    "item_id": photo_id,
                    "filename": p["filename"],
                    "shooting_time": datetime.fromtimestamp(p["time"]),
                    "saved_path": os.path.join(DOWNLOAD_DIR, p["filename"]),
                })

            if photo_id not in existing_person_photo_ids:
                relation_rows.append({
                    "person_id": person_id_int,
                    "photo_id": photo_id,
                })

        if not photo_rows and not relation_rows:
            print("⚠️ 所有資料皆已存在，略過儲存")
            return

        if photo_rows:
            stmt = insert(Photo).values(photo_rows).on_conflict_do_nothing(
                index_elements=["item_id"]
            )
            db.execute(stmt)
            print(f"✅ Photo 嘗試新增 {len(photo_rows)} 筆（重複自動略過）")

        if relation_rows:
            uq_name = _find_unique_constraint_name_for_person_photo_pair(db.get_bind())

            stmt = insert(Person).values(relation_rows)
            if uq_name:
                stmt = stmt.on_conflict_do_nothing(constraint=uq_name)
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=["person_id", "photo_id"])

            db.execute(stmt)
            print(f"✅ person-photo 嘗試新增 {len(relation_rows)} 筆（重複自動略過）")

        db.commit()

    finally:
        db.close()

def random_pick_from_person_database(person_id=None, start_time=None, end_time=None, limit=30):
    db = SessionLocal()
    query = db.query(Photo)

    if person_id:
        query = (
            query.join(Person, Person.photo_id == Photo.item_id)
            .filter(Person.person_id == person_id)
        )

    if start_time:
        query = query.filter(Photo.shooting_time >= start_time)
    if end_time:
        query = query.filter(Photo.shooting_time <= end_time)

    photos = (
        query.order_by(func.random())
        .limit(limit)
        .all()
    )

    return [
        {"filename": photo.filename, "id": photo.item_id, "shooting_time": photo.shooting_time}
        for photo in photos
    ]

def randam_pick_from_album_database(album_id=None, limit=30):
    db = SessionLocal()
    if album_id:
        photos = (
            db.query(Photo)
            .join(Album, Album.photo_id == Photo.item_id)
            .filter(Album.album_id == album_id)
            .order_by(func.random())
            .limit(limit)
            .all()
        )
    else:
        photos = db.query(Photo).order_by(func.random()).limit(limit).all()
    return [{"filename": photo.filename, "id": photo.item_id} for photo in photos]

def save_exist_db_with_person(photos, person_id):
    db = SessionLocal()
    try:
        person_id_int = int(person_id)

        # blacklist（建議也轉 int）
        blacklisted_ids = set(
            int(pid) for (pid,) in db.query(PhotoBlacklist.photo_id).all()
        )

        # 同批去重 + 過濾 blacklist + int 化
        seen = set()
        filtered_ids = []
        for p in photos:
            pid = p.get("id")
            if pid is None:
                continue
            pid = int(pid)
            if pid in blacklisted_ids:
                continue
            if pid in seen:
                continue
            seen.add(pid)
            filtered_ids.append(pid)

        # 只刪這個 person 的，避免全表清空
        db.query(ExistPerson).filter(ExistPerson.person_id == person_id_int).delete(
            synchronize_session=False
        )

        if filtered_ids:
            rows = [{"person_id": person_id_int, "photo_id": pid} for pid in filtered_ids]

            stmt = (
                insert(ExistPerson.__table__)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["person_id", "photo_id"])
            )
            db.execute(stmt)

        db.commit()

        exit_photos = (
            db.query(Photo)
              .join(ExistPerson, ExistPerson.photo_id == Photo.item_id)
              .filter(ExistPerson.person_id == person_id_int)
              .all()
        )
        return exit_photos

    finally:
        db.close()

def save_exit_db_with_album(photos, album_id):
    db = SessionLocal()
    db.query(ExistAlbum).delete()
    exit_album_entries = []
    for photo in photos:
        print(photo["id"])
        ep = ExistAlbum(album_id=album_id, photo_id=photo["id"])
        exit_album_entries.append(ep)
    db.bulk_save_objects(exit_album_entries)
    db.commit()

    exit_photos = (
        db.query(Photo)
        .join(ExistAlbum, ExistAlbum.photo_id == Photo.item_id)
        .filter(ExistAlbum.album_id == album_id)
        .all()
    )
    return exit_photos