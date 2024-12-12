from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager

from config import settings
from utils.logger import logger

engine = None
SessionLocal = None


def get_connection_string():
    connection_string = settings.SQLALCHEMY_DATABASE_URI
    # if connection_string.startswith('postgresql://'):
    #     connection_string = connection_string.replace('postgresql://', 'postgresql+psycopg://')
    return connection_string


Base = declarative_base()


def init_engine():
    uri = get_connection_string()
    logger.info(f"Initializing engine: {uri}")

    global engine, SessionLocal
    engine = create_engine(uri)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


def init_db():
    Base.metadata.create_all(bind=engine)


def drop_db():
    Base.metadata.drop_all(bind=engine)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.info("Rolling back session due to error")
        session.rollback()
        raise e
    finally:
        logger.info("Closing session")
        session.close()


def get_db():
    with session_scope() as session:
        yield session
