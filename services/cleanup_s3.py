from database import init_engine, session_scope
from datetime import datetime, timedelta
from server.models.job_models import Job

from utils.s3 import get_all_files_in_bucket, delete_file

from config import settings


def cleanup_s3_handler(event, context):
    """Cleanup old files from S3."""
    init_engine()

    with session_scope() as db_session:
        # delete files older than 72 hours in the processed files bucket
        files = get_all_files_in_bucket(settings.PROCESSED_FILES_BUCKET)
        for file in files:
            last_modified = file["LastModified"]
            last_modified_datetime = last_modified.replace(tzinfo=None)
            if last_modified_datetime < datetime.now() - timedelta(hours=72):
                delete_file(settings.PROCESSED_FILES_BUCKET, file["Key"])
                job_id = file["Key"].split("/")[0]  # Assuming the job ID is the first part of the key
                Job.update_upload_removed(db_session, job_id, True)

        # delete files older than 24 hours in the file drop bucket
        files = get_all_files_in_bucket(settings.FILE_DROP_BUCKET)
        for file in files:
            last_modified = file["LastModified"]
            last_modified_datetime = last_modified.replace(tzinfo=None)
            if last_modified_datetime < datetime.now() - timedelta(hours=24):
                delete_file(settings.FILE_DROP_BUCKET, file["Key"])
                # Update the job record to mark upload as removed
                job = Job.query_by_s3_key(db_session, settings.PROCESSED_FILES_BUCKET, file["Key"])
                if job:
                    Job.update_response_removed(db_session, job.id, True)

        db_session.commit()
