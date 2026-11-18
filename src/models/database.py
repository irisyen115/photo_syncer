from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import os
from urllib.parse import quote_plus


def _database_url():
    """DATABASE_URL > PG_* 環境變數 > 舊的預設值（NAS docker-compose 環境）。"""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.getenv("PG_HOST"):
        user = quote_plus(os.getenv("PG_USER", "postgres"))
        password = quote_plus(os.getenv("PG_PASSWORD", ""))
        host = os.environ["PG_HOST"]
        port = os.getenv("PG_PORT", "5432")
        db = os.getenv("PG_DB", "photodatabase")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return 'postgresql+psycopg2://user:password@pgsql_photos:5432/photodatabase'


DATABASE_URL = _database_url()

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
