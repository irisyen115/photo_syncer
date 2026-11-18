from sqlalchemy import Column, Integer
from sqlalchemy.orm import composite
from models.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, select
from models.photo import Photo

class PersonPhotoPair:
    def __init__(self, person_id, photo_id):
        self.person_id = person_id
        self.photo_id = photo_id

    def __composite_values__(self):
        return self.person_id, self.photo_id

    def __eq__(self, other):
        return isinstance(other, PersonPhotoPair) and \
               self.person_id == other.person_id and \
               self.photo_id == other.photo_id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"PersonPhotoPair(person_id={self.person_id}, photo_id={self.photo_id})"

class Person(Base):
    __tablename__ = 'person_photos'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer)
    photo_id = Column(Integer)
    person_photo_pair = composite(PersonPhotoPair, person_id, photo_id)

    photos = relationship("Photo", back_populates="person")

    __table_args__ = (
        UniqueConstraint('person_id', 'photo_id', name='uq_person_photo_pair'),
    )

    def get_latest_photo_by_person_id(self, db):
        """回傳該 person 拍攝時間最新的照片（與這筆 Person 紀錄本身無關，只看 person_id）。

        呼叫端（sync_photos_for_person、tools/photo_sync_from_*.py）會對同一個 person 的
        「每一筆」person_photos 都呼叫一次；人物有 39,441 張照片時就是 39,441 次相同的查詢（約 2 小時）。
        因此在同一個 DB session 內依 person_id 快取結果，同一個 person 只真的查一次。
        """
        cache = db.info.setdefault("latest_photo_by_person_id", {})
        if self.person_id in cache:
            return cache[self.person_id]

        photo_ids = select(Person.photo_id).where(Person.person_id == self.person_id)
        latest_photo = (
            db.query(Photo)
            .filter(Photo.item_id.in_(photo_ids))
            .filter(Photo.shooting_time != None)
            .order_by(Photo.shooting_time.desc())
            .first()
        )

        cache[self.person_id] = latest_photo
        return latest_photo
