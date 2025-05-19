from sqlalchemy import Column, Integer, String, Boolean, Text
from models.database import Base
from sqlalchemy import DateTime

class Photo(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer)
    filename = Column(String, nullable=False)
    album_id = Column(Integer)
    shooting_time = Column(DateTime)
    saved_path = Column(Text)
