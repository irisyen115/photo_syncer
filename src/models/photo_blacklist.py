from sqlalchemy import Column, Integer, Text, DateTime, func
from models.database import Base

class PhotoBlacklist(Base):
    __tablename__ = 'photo_blacklist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(Integer, nullable=False, unique=True)
    reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<PhotoBlacklist(id={self.id}, photo_id={self.photo_id}, reason='{self.reason}')>"
