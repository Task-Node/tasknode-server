import boto3
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Enum as SQLAlchemyEnum, BigInteger, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid


from constants import JobStatus, FileType
from utils.utils import get_utc_now
from database import Base
from config import settings


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
            .order_by(cls.created_at.desc())  # most recent first (other functionality depends on this!!!)
            .limit(limit)
            .offset(offset)
            .all()
        )

    @classmethod
    def get_total_count_by_user_id(cls, session, user_id: int) -> int:
        return session.query(cls).filter(cls.user_id == user_id).count()

    @staticmethod
    def get_log_tail(job_id: uuid.UUID, log_type: str = "output"):
        """
        Retrieve the tail log file from S3 for a given job ID.
        Returns the contents as a list of strings, or an empty list if file doesn't exist.

        :param job_id: UUID of the job
        :param log_type: Type of log file to retrieve ('output' or 'error')
        """
        assert log_type in ["output", "error"]
        try:
            s3_client = boto3.client("s3")
            bucket = settings.PROCESSED_FILES_BUCKET
            key = f"{str(job_id)}/{log_type}.tail"

            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")

            # Split content into lines and remove empty lines
            return [line for line in content.splitlines() if line]

        except s3_client.exceptions.NoSuchKey:
            # File doesn't exist in S3
            return []
        except Exception as e:
            print(f"Error fetching {log_type} tail log for job {job_id}: {str(e)}")
            return []


class JobFiles(Base):
    __tablename__ = "job_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    file_timestamp = Column(DateTime, nullable=False)
    file_type = Column(SQLAlchemyEnum(FileType), nullable=False)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)

    def __init__(
        self,
        job_id: uuid.UUID,
        s3_bucket: str,
        s3_key: str,
        file_name: str,
        file_size: int,
        file_timestamp: datetime,
        file_type: str,
    ):
        self.job_id = job_id
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.file_name = file_name
        self.file_size = file_size
        self.file_timestamp = file_timestamp
        self.file_type = file_type
        self.created_at = get_utc_now()

    def __repr__(self):
        return f"<JobFiles {self.id} {self.job_id} {self.s3_bucket} {self.s3_key} {self.file_name} {self.file_size} {self.file_timestamp} {self.file_type}>"

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
        file_type: str,
    ):
        item = cls(job_id, s3_bucket, s3_key, file_name, file_size, file_timestamp, file_type)
        session.add(item)
        session.flush()
        return item

    @classmethod
    def get_by_job_id(cls, session, job_id: uuid.UUID, file_type: str = None):
        query = session.query(cls).filter(cls.job_id == job_id)
        if file_type:
            query = query.filter(cls.file_type == file_type)
        return query.all()
