# https://www.serverless.com/plugins/serverless-python-requirements#dealing-with-lambdas-size-limitations
# sourcery skip: use-contextlib-suppress
try:
    import unzip_requirements  # type: ignore # noqa: F401
except ImportError:
    pass

from database import session_scope, init_engine
from constants import JobStatus
from utils.logger import logger
from utils.s3 import get_file_metadata

from models.job_models import Job
from models.user_models import User


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

    # Get metadata using the utility function
    metadata_response = get_file_metadata(s3_bucket, s3_key)
    print(metadata_response)
    print("-" * 100)

    metadata = metadata_response.get("Metadata", {})
    print(metadata)
    cognito_id = metadata.get("cognito_id")

    assert cognito_id, "Cognito ID is required"

    with session_scope() as db_session:
        user = User.get_by_cognito_id(db_session, cognito_id)
        job = Job.create(db_session, user.id, s3_bucket, s3_key, JobStatus.PENDING)
        logger.info(f"Created job: {job}")
        db_session.commit()
