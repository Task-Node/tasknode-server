# https://www.serverless.com/plugins/serverless-python-requirements#dealing-with-lambdas-size-limitations
# sourcery skip: use-contextlib-suppress
try:
    import unzip_requirements  # type: ignore # noqa: F401
except ImportError:
    pass


import boto3
from datetime import datetime
from sqlalchemy import text
from zoneinfo import ZoneInfo

from config import settings
from constants import MAX_IN_PROGRESS, JobStatus
from database import session_scope, init_engine
from models.job_models import Job, JobFiles
from models.user_models import User
from utils.email import send_email, FAILURE_TEMPLATE, SUCCESS_TEMPLATE
from utils.logger import logger
from utils.s3 import get_signed_url, get_signed_upload_url
from utils.utils import format_file_size


def create_task_definition(
    presigned_download_url,
    presigned_zip_upload_url,
    presigned_manifest_upload_url,
    presigned_output_log_upload_url,
    presigned_error_log_upload_url,
):
    return {
        "family": "tasknode-processor",
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": "256",
        "memory": "512",
        "executionRoleArn": f"arn:aws:iam::{settings.AWS_ACCOUNT_ID}:role/{settings.ECS_TASK_EXECUTION_ROLE}",
        "containerDefinitions": [
            {
                "name": "tasknode-container",
                "image": f"{settings.AWS_ACCOUNT_ID}.dkr.ecr.{settings.REGION}.amazonaws.com/tasknode-processor-{settings.ENV}:latest",
                "essential": True,
                "environment": [
                    {"name": "DOWNLOAD_URL", "value": presigned_download_url},
                    {"name": "ZIP_UPLOAD_URL", "value": presigned_zip_upload_url},
                    {"name": "MANIFEST_UPLOAD_URL", "value": presigned_manifest_upload_url},
                    {"name": "OUTPUT_LOG_UPLOAD_URL", "value": presigned_output_log_upload_url},
                    {"name": "ERROR_LOG_UPLOAD_URL", "value": presigned_error_log_upload_url},
                    {"name": "AWS_DEFAULT_REGION", "value": settings.REGION},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/tasknode-processor",
                        "awslogs-region": settings.REGION,
                        "awslogs-stream-prefix": "ecs",
                    },
                },
            }
        ],
    }


def register_and_run_task(task_definition):
    ecs = boto3.client("ecs")

    response = ecs.register_task_definition(**task_definition)
    task_definition_arn = response["taskDefinition"]["taskDefinitionArn"]

    return ecs.run_task(
        cluster=settings.ECS_CLUSTER,
        taskDefinition=task_definition_arn,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": settings.VPC_SUBNET_IDS,
                "securityGroups": settings.VPC_SECURITY_GROUP_IDS,
                "assignPublicIp": "ENABLED",
            }
        },
    )


def process_task_response(db_session, response: dict, job: Job):
    """Process the ECS task response."""
    if not response.get("tasks"):
        failures = response.get("failures", [])
        for failure in failures:
            logger.error(f"Task launch failure: {failure.get('reason', 'Unknown reason')}")
            logger.error(f"Failure details: {failure}")
        return

    task_arn = response["tasks"][0]["taskArn"]
    Job.update_status(db_session, job.id, JobStatus.PROCESSING, task_arn)


def process_manifest_file(db_session, job: Job):
    # Read the manifest file directly from S3
    s3_client = boto3.client("s3")
    s3_bucket = settings.PROCESSED_FILES_BUCKET
    s3_key = f"{job.id}/manifest.txt"

    job_files: list[JobFiles] = []

    print(f"Reading manifest file from S3: {s3_bucket}/{s3_key}")

    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        manifest_content = response["Body"].read().decode("utf-8")

        # for each line in the manifest file, create a job file record
        for line in manifest_content.split("\n"):
            if not line:
                continue
            file_name, file_size, file_unix_timestamp = line.split(",")
            file_timestamp = datetime.fromtimestamp(int(file_unix_timestamp), tz=ZoneInfo("UTC"))
            jobfile = JobFiles.create(db_session, job.id, s3_bucket, s3_key, file_name, file_size, file_timestamp)
            job_files.append(jobfile)
    except Exception as e:
        logger.error(f"Error reading manifest file from S3: {str(e)}")
        raise

    return job_files


def update_jobs_in_progress(db_session):
    """Update the status of jobs that are in progress."""
    jobs = Job.get_all_in_progress(db_session)
    logger.info(f"Updating {len(jobs)} jobs in progress")
    for job in jobs:
        logger.info(job)
        arn = job.fargate_task_arn
        ecs = boto3.client("ecs")
        response = ecs.describe_tasks(cluster=settings.ECS_CLUSTER, tasks=[arn])
        logger.info(response)
        logger.info(response.keys())

        if response["tasks"]:
            logger.info("Task found")
            task = response["tasks"][0]
            task_status = task["lastStatus"]

            # Get exit code if container has stopped
            exit_code = None
            if task_status == "STOPPED" and "containers" in task:
                # Get the exit code from the first container
                container = task["containers"][0]
                exit_code = container.get("exitCode")

            logger.info(f"Task status: {task_status}, exit code: {exit_code}")

            # Update job status based on task status and exit code
            if task_status == "STOPPED":
                user = User.get_by_id(db_session, job.user_id)
                if exit_code == 0:
                    job_files = process_manifest_file(db_session, job)

                    # Create file list HTML
                    file_list_html = "\n".join(
                        [
                            f"<li>{job_file.file_name} ({format_file_size(float(job_file.file_size))})</li>"
                            for job_file in job_files
                        ]
                    )

                    signed_url_file_zip = get_signed_url(
                        settings.PROCESSED_FILES_BUCKET, 
                        f"{job.id}/files.zip", 
                        expiration=60 * 60 * 24,
                        filename="processed_files.zip"
                    )
                    signed_url_output_log = get_signed_url(
                        settings.PROCESSED_FILES_BUCKET, 
                        f"{job.id}/output.log", 
                        expiration=60 * 60 * 24,
                        filename="output.log"
                    )
                    signed_url_error_log = get_signed_url(
                        settings.PROCESSED_FILES_BUCKET, 
                        f"{job.id}/error.log", 
                        expiration=60 * 60 * 24,
                        filename="error.log"
                    )

                    send_email(
                        [user.email],
                        "Tasknode task completed",
                        SUCCESS_TEMPLATE.format(
                            task_id=job.id,
                            file_list=file_list_html,
                            signed_url_file_zip=signed_url_file_zip,
                            signed_url_output_log=signed_url_output_log,
                            signed_url_error_log=signed_url_error_log,
                        ),
                    )
                    Job.update_status(db_session, job.id, JobStatus.COMPLETED)
                else:
                    send_email([user.email], "Tasknode task failed", FAILURE_TEMPLATE.format(task_id=job.id))
                    Job.update_status(db_session, job.id, JobStatus.FAILED)


def handle_files(event, context):
    """Main handler function."""
    init_engine()

    with session_scope() as db_session:
        try:
            # Start transaction with serializable isolation level
            db_session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

            update_jobs_in_progress(db_session)
            in_progress_count = Job.get_number_of_in_progress(db_session)

            if in_progress_count >= MAX_IN_PROGRESS:
                logger.info(f"Max in progress jobs reached: {in_progress_count}")
                return

            # Add FOR UPDATE to lock the row
            job = (
                db_session.query(Job)
                .filter(Job.status == JobStatus.PENDING)
                .order_by(Job.created_at.asc())
                .with_for_update(skip_locked=True)
                .first()
            )

            if not job:
                logger.info("No pending jobs found")
            else:
                logger.info(f"Processing job: {job}")
                cognito_id = User.get_by_id(db_session, job.user_id).cognito_id
                presigned_download_url = get_signed_url(job.s3_bucket, job.s3_key, expiration=180)
                presigned_zip_upload_url = get_signed_upload_url(
                    settings.PROCESSED_FILES_BUCKET,
                    f"{job.id}/files.zip",
                    content_type="application/zip",
                    expiration=60 * 60 * 48,
                    cognito_id=cognito_id,
                )
                presigned_manifest_upload_url = get_signed_upload_url(
                    settings.PROCESSED_FILES_BUCKET,
                    f"{job.id}/manifest.txt",
                    content_type="text/plain",
                    expiration=60 * 60 * 48,
                    cognito_id=cognito_id,
                )

                presigned_output_log_upload_url = get_signed_upload_url(
                    settings.PROCESSED_FILES_BUCKET,
                    f"{job.id}/output.log",
                    content_type="text/plain",
                    expiration=60 * 60 * 48,
                    cognito_id=cognito_id,
                )

                presigned_error_log_upload_url = get_signed_upload_url(
                    settings.PROCESSED_FILES_BUCKET,
                    f"{job.id}/error.log",
                    content_type="text/plain",
                    expiration=60 * 60 * 48,
                    cognito_id=cognito_id,
                )

                assert presigned_download_url, "Presigned download URL is required"
                assert presigned_zip_upload_url, "Presigned zip upload URL is required"
                assert presigned_manifest_upload_url, "Presigned manifest upload URL is required"
                assert presigned_output_log_upload_url, "Presigned output log upload URL is required"
                assert presigned_error_log_upload_url, "Presigned error log upload URL is required"

                task_definition = create_task_definition(
                    presigned_download_url,
                    presigned_zip_upload_url,
                    presigned_manifest_upload_url,
                    presigned_output_log_upload_url,
                    presigned_error_log_upload_url,
                )

                try:
                    response = register_and_run_task(task_definition)
                    process_task_response(db_session, response, job)
                except Exception as e:
                    logger.error(f"Error launching task: {str(e)}")
                    Job.update_status(db_session, job.id, JobStatus.FAILED)

            db_session.commit()
        except Exception as e:
            logger.error(f"Error processing job: {str(e)}")
            db_session.rollback()
