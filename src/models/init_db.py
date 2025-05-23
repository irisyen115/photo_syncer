from models.database import Base, engine
from models.photo import Photo
from models.album import Album
from models.person import Person

Base.metadata.create_all(bind=engine)
