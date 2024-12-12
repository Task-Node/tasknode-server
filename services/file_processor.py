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
from math import ceil

from config import settings
from constants import MAX_IN_PROGRESS, JobStatus, FileType
from database import session_scope, init_engine
from models.job_models import Job, JobFiles
from models.user_models import User
from utils.email import (
    send_email,
    FAILURE_TEMPLATE,
    SUCCESS_TEMPLATE,
    FILE_GENERATED_TEMPLATE,
    FILE_GENERATED_CONTAINER_TEMPLATE,
    FILE_LINK_TEMPLATE,
)
from utils.logger import logger
from utils.s3 import file_exists, get_signed_url, get_signed_upload_url, delete_file
from utils.utils import format_file_size


def create_task_definition(
    presigned_download_url,
    presigned_zip_upload_url,
    presigned_manifest_upload_url,
    presigned_output_log_upload_url,
    presigned_error_log_upload_url,
    presigned_output_tail_upload_url,
    presigned_error_tail_upload_url,
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
                    {
                        "name": "MANIFEST_UPLOAD_URL",
                        "value": presigned_manifest_upload_url,
                    },
                    {
                        "name": "OUTPUT_LOG_UPLOAD_URL",
                        "value": presigned_output_log_upload_url,
                    },
                    {
                        "name": "ERROR_LOG_UPLOAD_URL",
                        "value": presigned_error_log_upload_url,
                    },
                    {
                        "name": "OUTPUT_TAIL_UPLOAD_URL",
                        "value": presigned_output_tail_upload_url,
                    },
                    {
                        "name": "ERROR_TAIL_UPLOAD_URL",
                        "value": presigned_error_tail_upload_url,
                    },
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

    logger.info(f"Task response: {response}")

    task_arn = response["tasks"][0]["taskArn"]
    task_id = task_arn.split("/")[-1]
    Job.update_status(db_session, job.id, JobStatus.PROCESSING, task_id)


def add_job_file(db_session, job: Job, file_type: FileType):
    s3_client = boto3.client("s3")
    s3_bucket = settings.PROCESSED_FILES_BUCKET

    if file_type == FileType.OUTPUT_LOG:
        s3_key = f"{job.id}/output.log"
        file_name = "output.log"
    elif file_type == FileType.ERROR_LOG:
        s3_key = f"{job.id}/error.log"
        file_name = "error.log"
    elif file_type == FileType.ZIPPED_GENERATED:
        s3_key = f"{job.id}/tasknode_generated_files.zip"
        file_name = "tasknode_generated_files.zip"
    else:
        raise ValueError(f"Invalid file type: {file_type}")

    # check if the file exists in S3
    if not file_exists(s3_bucket, s3_key):
        return None

    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    file_size = response["ContentLength"]
    file_timestamp = response["LastModified"]

    return JobFiles.create(
        db_session,
        job.id,
        s3_bucket,
        s3_key,
        file_name,
        file_size,
        file_timestamp,
        file_type,
    )


def process_manifest_file(db_session, job: Job) -> list[JobFiles]:
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
            jobfile = JobFiles.create(
                db_session,
                job.id,
                s3_bucket,
                s3_key,
                file_name,
                file_size,
                file_timestamp,
                FileType.GENERATED,
            )
            job_files.append(jobfile)
    except s3_client.exceptions.NoSuchKey:
        # If the manifest file doesn't exist, return empty list
        logger.info(f"No manifest file found at {s3_bucket}/{s3_key}")
        return []
    except Exception as e:
        logger.error(f"Error reading manifest file from S3: {str(e)}")
        raise

    if job_files:
        add_job_file(db_session, job, FileType.ZIPPED_GENERATED)
    return job_files


def get_task_details(task: dict) -> tuple[int | None, int | None]:
    """
    Extract exit code and runtime from an ECS task.
    Returns tuple of (exit_code, runtime) where both values may be None.
    """
    exit_code = None
    runtime = None

    if "containers" in task:
        # Get the exit code from the first container
        container = task["containers"][0]
        exit_code = container.get("exitCode")

    # Calculate runtime if start and stop times are available
    if "startedAt" in task and "stoppedAt" in task:
        runtime = int((task["stoppedAt"] - task["startedAt"]).total_seconds())
        logger.info(f"Task runtime: {runtime} seconds")

    return exit_code, runtime


def update_jobs_in_progress(db_session):
    """Update the status of jobs that are in progress."""
    jobs = Job.get_all_in_progress(db_session)
    logger.info(f"Updating {len(jobs)} jobs in progress")
    for job in jobs:
        # Lock the job row before updating
        locked_job = db_session.query(Job).filter(Job.id == job.id).with_for_update().first()
        if not locked_job:
            logger.warning(f"Job {job.id} not found when trying to lock")
            continue

        logger.info(f"Processing job: {locked_job}")
        arn = locked_job.fargate_task_id
        ecs = boto3.client("ecs")
        response = ecs.describe_tasks(cluster=settings.ECS_CLUSTER, tasks=[arn])
        logger.info(response)
        logger.info(response.keys())

        if response["tasks"]:
            logger.info("Task found")
            task = response["tasks"][0]
            task_status = task["lastStatus"]

            # Only process if the task is STOPPED and we haven't processed it before
            if task_status == "STOPPED" and locked_job.status == JobStatus.PROCESSING:
                exit_code, runtime = get_task_details(task)
                script_succeeded = exit_code == 0
                logger.info(f"Task status: {task_status}, exit code: {exit_code}, runtime: {runtime}")

                runtime_minutes = ceil(runtime / 60)

                user = User.get_by_id(db_session, locked_job.user_id)

                job_files = process_manifest_file(db_session, locked_job)

                # Generate signed URLs first
                signed_url_file_zip = (
                    get_signed_url(
                        settings.PROCESSED_FILES_BUCKET,
                        f"{locked_job.id}/tasknode_generated_files.zip",
                        expiration=60 * 60 * 72,
                        filename="tasknode_generated_files.zip",
                    )
                    if job_files
                    else None
                )

                output_logs = add_job_file(db_session, locked_job, FileType.OUTPUT_LOG)
                error_logs = add_job_file(db_session, locked_job, FileType.ERROR_LOG)

                signed_url_output_log = (
                    get_signed_url(
                        settings.PROCESSED_FILES_BUCKET,
                        output_logs.s3_key,
                        expiration=60 * 60 * 72,
                        filename="output.log",
                    )
                    if output_logs and output_logs.file_size > 0
                    else None
                )

                signed_url_error_log = (
                    get_signed_url(
                        settings.PROCESSED_FILES_BUCKET,
                        error_logs.s3_key,
                        expiration=60 * 60 * 72,
                        filename="error.log",
                    )
                    if error_logs and error_logs.file_size > 0
                    else None
                )

                # Now create file list HTML using the templates
                file_list_container = ""
                if job_files:
                    file_list_html = "\n".join(
                        [
                            FILE_GENERATED_TEMPLATE.format(
                                file_name=f"{job_file.file_name} ({format_file_size(float(job_file.file_size))})",
                            )
                            for job_file in job_files
                        ]
                    )
                    file_list_container = FILE_GENERATED_CONTAINER_TEMPLATE.format(file_list=file_list_html)

                # Create output/error log links using the template
                output_log_link = (
                    FILE_LINK_TEMPLATE.format(signed_url=signed_url_output_log, file_name="Output Log")
                    if output_logs and output_logs.file_size > 0
                    else ""
                )

                error_log_link = (
                    FILE_LINK_TEMPLATE.format(signed_url=signed_url_error_log, file_name="Error Log")
                    if error_logs and error_logs.file_size > 0
                    else ""
                )

                generated_files_link = (
                    FILE_LINK_TEMPLATE.format(
                        signed_url=signed_url_file_zip,
                        file_name="Generated Files (ZIP)",
                    )
                    if signed_url_file_zip
                    else ""
                )

                if script_succeeded:
                    send_email(
                        [user.email],
                        "Tasknode task completed",
                        SUCCESS_TEMPLATE.format(
                            task_id=locked_job.id,
                            file_list_container=file_list_container,
                            output_log_link=output_log_link,
                            error_log_link=error_log_link,
                            generated_files_link=generated_files_link,
                            runtime_minutes=runtime_minutes,
                        ),
                    )

                    Job.update_status(db_session, locked_job.id, JobStatus.COMPLETED, runtime=runtime)

                    # Clean up the input file from the file drop bucket
                    logger.info(f"Cleaning up input file for job {locked_job.id} from bucket {locked_job.s3_bucket}")
                    delete_file(locked_job.s3_bucket, locked_job.s3_key)
                    Job.update_upload_removed(db_session, locked_job.id, True)
                else:
                    send_email(
                        [user.email],
                        "Tasknode task failed",
                        FAILURE_TEMPLATE.format(
                            task_id=locked_job.id,
                            runtime_minutes=runtime_minutes,
                            file_list_container=file_list_container,
                            output_log_link=output_log_link,
                            error_log_link=error_log_link,
                            generated_files_link=generated_files_link,
                        ),
                    )
                    Job.update_status(db_session, locked_job.id, JobStatus.FAILED, runtime=runtime)


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
                    f"{job.id}/tasknode_generated_files.zip",
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

                presigned_output_tail_upload_url = get_signed_upload_url(
                    settings.PROCESSED_FILES_BUCKET,
                    f"{job.id}/output.tail",
                    content_type="text/plain",
                    expiration=60 * 60 * 48,
                    cognito_id=cognito_id,
                )

                presigned_error_tail_upload_url = get_signed_upload_url(
                    settings.PROCESSED_FILES_BUCKET,
                    f"{job.id}/error.tail",
                    content_type="text/plain",
                    expiration=60 * 60 * 48,
                    cognito_id=cognito_id,
                )

                assert presigned_download_url, "Presigned download URL is required"
                assert presigned_zip_upload_url, "Presigned zip upload URL is required"
                assert presigned_manifest_upload_url, "Presigned manifest upload URL is required"
                assert presigned_output_log_upload_url, "Presigned output log upload URL is required"
                assert presigned_error_log_upload_url, "Presigned error log upload URL is required"
                assert presigned_output_tail_upload_url, "Presigned output tail upload URL is required"
                assert presigned_error_tail_upload_url, "Presigned error tail upload URL is required"

                task_definition = create_task_definition(
                    presigned_download_url,
                    presigned_zip_upload_url,
                    presigned_manifest_upload_url,
                    presigned_output_log_upload_url,
                    presigned_error_log_upload_url,
                    presigned_output_tail_upload_url,
                    presigned_error_tail_upload_url,
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
