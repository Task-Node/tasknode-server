# https://www.serverless.com/plugins/serverless-python-requirements#dealing-with-lambdas-size-limitations
# sourcery skip: use-contextlib-suppress
try:
    import unzip_requirements  # type: ignore # noqa: F401
except ImportError:
    pass

from database import get_session, init_engine
from constants import JobStatus
from utils.logger import logger

from models.job_models import Job


def handler(event, context, s3_bucket=None, s3_key=None):
    logger.info("File drop handler called")
    init_engine()  # Initialize the database engine

    # get from variable or event (when called from another function or invoked locally)
    s3_bucket = s3_bucket or event.get("Records", [{}])[0].get("s3", {}).get("bucket", {}).get("name")
    assert s3_bucket, "S3 bucket is required"

    s3_key = s3_key or event.get("Records", [{}])[0].get("s3", {}).get("object", {}).get("key")
    assert s3_key, "S3 key is required"

    logger.info(f"S3 bucket: {s3_bucket}")
    logger.info(f"S3 key: {s3_key}")

    with get_session() as db_session:
        job = Job.create(db_session, s3_bucket, s3_key, JobStatus.PENDING)
        logger.info(f"Created job: {job}")
        db_session.commit()
