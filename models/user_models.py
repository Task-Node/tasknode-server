from sqlalchemy import BigInteger, Column, DateTime, String, Boolean
from sqlalchemy.orm import relationship
from utils.utils import get_utc_now
from database import Base
from datetime import datetime
import boto3
from config import settings

from exceptions import TaskNodeException
from utils.logger import logger


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cognito_id = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=get_utc_now)
    jobs = relationship("Job", backref="user")

    def __init__(
        self,
        cognito_id: str,
        email: str,
        timestamp: datetime = None,
    ):
        self.cognito_id = cognito_id
        self.email = email
        self.timestamp = timestamp or get_utc_now()

    def __repr__(self):
        return f"<User {self.id} {self.email}>"

    @classmethod
    def create(cls, session, cognito_id: str, email: str):
        item = cls(cognito_id=cognito_id, email=email)
        try:
            session.add(item)
            session.flush()
        except Exception as e:
            session.rollback()
            raise TaskNodeException(f"Failed to create user: {e}")
        return item

    @classmethod
    def get_all(cls, session):
        return session.query(cls).all()

    @classmethod
    def get_by_cognito_id(cls, session, cognito_id: str):
        item = session.query(cls).filter(cls.cognito_id == cognito_id).first()
        if not item:
            # search for the user in cognito
            logger.info("Searching for user in cognito")
            boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
            cognito_client = boto_session.client("cognito-idp")
            try:
                cognito_user = cognito_client.admin_get_user(
                    UserPoolId=settings.COGNITO_USER_POOL_ID, Username=cognito_id
                )
                if not cognito_user:
                    raise TaskNodeException(f"User not found: {cognito_id}")
                logger.info(cognito_user)

                email = next(
                    (attr["Value"] for attr in cognito_user["UserAttributes"] if attr["Name"] == "email"), None
                )
                if not email:
                    raise TaskNodeException(f"User not found: {cognito_id}")
                item = cls(cognito_id=cognito_id, email=email)
                session.add(item)
                session.flush()
            except Exception as e:
                logger.error(e)
                raise TaskNodeException(f"User not found: {e}")
        return item
