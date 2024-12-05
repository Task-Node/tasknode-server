from datetime import datetime
from sqlalchemy import Column, DateTime, String, Enum as SQLAlchemyEnum, BigInteger, ForeignKey, Boolean
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
    fargate_task_id = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    upload_removed = Column(Boolean, nullable=False, default=False)
    response_removed = Column(Boolean, nullable=False, default=False)
    runtime = Column(BigInteger, nullable=True)  # in seconds
    created_at = Column(DateTime, nullable=False, default=get_utc_now)
    updated_at = Column(DateTime, nullable=False, default=get_utc_now)

    def __init__(self, user_id: int, s3_bucket: str, s3_key: str, status: str, fargate_task_id: str = None):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.status = status
        self.fargate_task_id = fargate_task_id
        self.upload_removed = False
        self.response_removed = False
        self.runtime = None
        self.created_at = get_utc_now()
        self.updated_at = get_utc_now()

    def __repr__(self):
        return f"<Job {self.id} {self.s3_bucket} {self.s3_key} {self.status}>"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def create(cls, session, user_id: int, s3_bucket: str, s3_key: str, status: str, fargate_task_id: str = None):
        item = cls(user_id, s3_bucket, s3_key, status, fargate_task_id)
        session.add(item)
        session.flush()
        return item

    @classmethod
    def query_by_s3_key(cls, session, s3_bucket: str, s3_key: str):
        return session.query(cls).filter(cls.s3_bucket == s3_bucket, cls.s3_key == s3_key).first()

    @classmethod
    def update_upload_removed(cls, session, id: uuid.UUID, upload_removed: bool):
        session.query(cls).filter(cls.id == id).update({"upload_removed": upload_removed})
        session.flush()

    @classmethod
    def update_response_removed(cls, session, id: uuid.UUID, response_removed: bool):
        session.query(cls).filter(cls.id == id).update({"response_removed": response_removed})
        session.flush()

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
    def update_status(cls, session, id: uuid.UUID, status: JobStatus, fargate_task_id: str = None, runtime: int = None):
        update = {"status": status, "updated_at": get_utc_now()}
        if fargate_task_id:
            update["fargate_task_id"] = fargate_task_id
        if runtime:
            update["runtime"] = runtime
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

    @classmethod
    def get_by_job_id(cls, session, job_id: uuid.UUID):
        return session.query(cls).filter(cls.job_id == job_id).all()
