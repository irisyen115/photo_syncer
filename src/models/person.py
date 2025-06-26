from sqlalchemy import Column, Integer
from sqlalchemy.orm import composite
from models.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
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
        subquery = (
            db.query(Person.photo_id)
            .filter(Person.person_id == self.person_id)
            .subquery()
        )

        latest_photo = (
            db.query(Photo)
            .filter(Photo.item_id.in_(subquery))
            .filter(Photo.shooting_time != None)
            .order_by(Photo.shooting_time.desc())
            .first()
        )

        return latest_photo
