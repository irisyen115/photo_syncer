from sqlalchemy import Column, Integer, DateTime
from models.database import Base

class SyncStatus(Base):
    __tablename__ = "sync_status"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, unique=True)
    last_synced_photo_id = Column(Integer)
    last_synced_time = Column(DateTime)
