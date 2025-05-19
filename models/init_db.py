from models.database import Base, engine
from models.photo import Photo

Base.metadata.create_all(bind=engine)
