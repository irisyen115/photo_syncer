from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from models.database import Base
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship

class Photo(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer)
    filename = Column(String, nullable=False)
    shooting_time = Column(DateTime)
    saved_path = Column(Text)
    album_id = Column(Integer, ForeignKey('album_photos.id'))
    person_id = Column(Integer, ForeignKey('person_photos.id'))

    album = relationship("Album", back_populates="photos")
    person = relationship("Person", back_populates="photos")
