from datetime import datetime
from sqlalchemy import Column, DateTime, String, Enum as SQLAlchemyEnum, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from constants import JobStatus
from utils.utils import get_utc_now
from database import Base


class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    fargate_task_arn = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)
    updated_at = Column(DateTime, nullable=False, default=get_utc_now)

    def __init__(self, user_id: int, s3_bucket: str, s3_key: str, status: str, fargate_task_arn: str = None):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.status = status
        self.fargate_task_arn = fargate_task_arn
        self.created_at = get_utc_now()
        self.updated_at = get_utc_now()

    def __repr__(self):
        return f"<Job {self.id} {self.s3_bucket} {self.s3_key} {self.status}>"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def create(cls, session, user_id: int, s3_bucket: str, s3_key: str, status: str, fargate_task_arn: str = None):
        item = cls(user_id, s3_bucket, s3_key, status, fargate_task_arn)
        session.add(item)
        session.flush()
        return item

    @classmethod
    def get_by_id(cls, session, id: uuid.UUID, user_id: int):
        return session.query(cls).filter(cls.id == id, cls.user_id == user_id).first()

    @classmethod
    def get_by_user_id(cls, session, user_id: int):
        return session.query(cls).filter(cls.user_id == user_id).all()

    @classmethod
    def get_all_in_progress(cls, session):
        return session.query(cls).filter(cls.status == JobStatus.PROCESSING).all()

    @classmethod
    def get_number_of_in_progress(cls, session):
        return session.query(cls).filter(cls.status == JobStatus.PROCESSING).count()

    @classmethod
    def get_next_pending(cls, session):
        return session.query(cls).filter(cls.status == JobStatus.PENDING).order_by(cls.created_at.asc()).first()

    @classmethod
    def update_status(cls, session, id: uuid.UUID, status: JobStatus, fargate_task_arn: str = None):
        update = {"status": status, "updated_at": get_utc_now()}
        if fargate_task_arn:
            update["fargate_task_arn"] = fargate_task_arn
        session.query(cls).filter(cls.id == id).update(update)
        session.flush()

    @classmethod
    def get_jobs_by_user_id(cls, session, user_id: int, limit: int = 10, offset: int = 0):
        return (
            session.query(cls)
            .filter(cls.user_id == user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @classmethod
    def get_total_count_by_user_id(cls, session, user_id: int) -> int:
        return session.query(cls).filter(cls.user_id == user_id).count()


class JobFiles(Base):
    __tablename__ = "job_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    file_timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)

    def __init__(
        self, job_id: uuid.UUID, s3_bucket: str, s3_key: str, file_name: str, file_size: int, file_timestamp: datetime
    ):
        self.job_id = job_id
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.file_name = file_name
        self.file_size = file_size
        self.file_timestamp = file_timestamp
        self.created_at = get_utc_now()

    def __repr__(self):
        return f"<JobFiles {self.id} {self.job_id} {self.s3_bucket} {self.s3_key} {self.file_name} {self.file_size} {self.file_timestamp}>"

    @classmethod
    def create(
        cls,
        session,
        job_id: uuid.UUID,
        s3_bucket: str,
        s3_key: str,
        file_name: str,
        file_size: int,
        file_timestamp: datetime,
    ):
        item = cls(job_id, s3_bucket, s3_key, file_name, file_size, file_timestamp)
        session.add(item)
        session.flush()
        return item
