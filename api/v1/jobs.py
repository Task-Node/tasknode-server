import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from constants import FileType
from database import get_db
from models.job_models import Job, JobFiles
from models.user_models import User
from utils.auth import VerifyToken
from utils.s3 import get_signed_upload_url, get_signed_url

auth = VerifyToken()


# Update the router to include the database session dependency
router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs API v1"])


class SignedUrlResponse(BaseModel):
    signedUrl: str
    s3Key: str
    filename: Optional[str]
    description: Optional[str]
    fileSize: Optional[int]


class FileLinkResponse(BaseModel):
    files: list[SignedUrlResponse]


class JobFileItem(BaseModel):
    file_name: str
    file_size: int
    file_timestamp: datetime


class JobResponseItem(BaseModel):
    id: uuid.UUID
    status: str
    runtime: Optional[int]
    created_at: datetime
    updated_at: datetime
    files: list[JobFileItem] = []
    output_log_tail: list[str] = []
    error_log_tail: list[str] = []


class JobResponse(BaseModel):
    jobs: list[JobResponseItem]
    total_count: int


@router.get("/status")
async def status() -> dict:
    return {"status": "ok"}


@router.get("/get_zip_upload_url", response_model=SignedUrlResponse)
async def get_zip_upload_url(
    session: Session = Depends(get_db),
    current_user: dict = Security(auth.get_current_user),
) -> SignedUrlResponse:
    cognito_id = current_user["sub"]

    filename = f"{uuid.uuid4()}.zip"
    signed_url = get_signed_upload_url(
        settings.FILE_DROP_BUCKET,
        filename,
        "application/zip",
        30,
        cognito_id=cognito_id,
    )
    return SignedUrlResponse(signedUrl=signed_url, s3Key=filename)


@router.get("/list", response_model=JobResponse)
async def list_jobs(
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    session: Session = Depends(get_db),
    current_user: dict = Security(auth.get_current_user),
) -> JobResponse:
    cognito_id = current_user["sub"]
    user: User = User.get_by_cognito_id(session, cognito_id)
    jobs: list[Job] = Job.get_jobs_by_user_id(session, user.id, limit=limit, offset=offset)
    total_count = Job.get_total_count_by_user_id(session, user.id)
    response_items = [
        JobResponseItem(
            id=str(job.id),
            status=job.status.value,
            runtime=job.runtime,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        for job in jobs
    ]
    return JobResponse(jobs=response_items, total_count=total_count)


@router.get("/get/{job_identifier}", response_model=JobResponseItem)
async def get_job(
    job_identifier: str,
    session: Session = Depends(get_db),
    current_user: dict = Security(auth.get_current_user),
    tail_lines: int = 10,
) -> JobResponseItem:
    cognito_id = current_user["sub"]
    user: User = User.get_by_cognito_id(session, cognito_id)

    # Check if the identifier is a valid UUID
    try:
        job_id = uuid.UUID(job_identifier)
        job: Job = Job.get_by_id(session, job_id, user.id)
    except ValueError:
        print(f"Trying to get job by index: {job_identifier}")
        # If not a UUID, treat it as an index
        try:
            index = int(job_identifier)
        except ValueError:
            raise HTTPException(status_code=404, detail="Job not found")

        if index <= 0:
            raise HTTPException(status_code=404, detail="Job not found")

        jobs: list[Job] = Job.get_jobs_by_user_id(session, user.id, limit=1, offset=index - 1)
        if not jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[0]

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get associated files (only GENERATED type)
    job_files = JobFiles.get_by_job_id(session, job.id)
    files = [
        JobFileItem(
            file_name=f.file_name,
            file_size=f.file_size,
            file_timestamp=f.file_timestamp,
        )
        for f in job_files
        if f.file_type == FileType.GENERATED
    ]

    output_log_tail = Job.get_log_tail(job.id, "output", n=tail_lines)
    error_log_tail = Job.get_log_tail(job.id, "error", n=tail_lines)

    return JobResponseItem(
        id=str(job.id),
        status=job.status.value,
        runtime=job.runtime,
        created_at=job.created_at,
        updated_at=job.updated_at,
        files=files,
        output_log_tail=output_log_tail,
        error_log_tail=error_log_tail,
    )


@router.get("/{job_id}/download_urls", response_model=FileLinkResponse)
async def get_job_download_urls(
    job_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: dict = Security(auth.get_current_user),
) -> FileLinkResponse:
    """Get signed URLs to download the job's files (generated files, output log, and error log)."""

    user: User = User.get_by_cognito_id(session, current_user["sub"])

    # Get the job and verify it exists
    job = Job.get_by_id(session, job_id, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all job files
    job_files = JobFiles.get_by_job_id(session, job_id)

    # Find specific file types
    generated_files = next((f for f in job_files if f.file_type == FileType.ZIPPED_GENERATED), None)
    output_log = next((f for f in job_files if f.file_type == FileType.OUTPUT_LOG), None)
    error_log = next((f for f in job_files if f.file_type == FileType.ERROR_LOG), None)

    # Generate signed URLs with 72 hour expiry
    files = []

    if generated_files and generated_files.file_size > 0:
        files.append(
            SignedUrlResponse(
                filename="tasknode_generated_files.zip",
                description="The generated files for this job.",
                signedUrl=get_signed_url(
                    settings.PROCESSED_FILES_BUCKET,
                    generated_files.s3_key,
                    expiration=60 * 60 * 2,
                    filename="tasknode_generated_files.zip",
                ),
                s3Key=generated_files.s3_key,
                fileSize=generated_files.file_size,
            )
        )

    if output_log and output_log.file_size > 0:
        files.append(
            SignedUrlResponse(
                filename="output.log",
                description="The output logs for this job.",
                signedUrl=get_signed_url(
                    settings.PROCESSED_FILES_BUCKET,
                    output_log.s3_key,
                    expiration=60 * 60 * 2,
                    filename="output.log",
                ),
                s3Key=output_log.s3_key,
                fileSize=output_log.file_size,
            )
        )

    if error_log and error_log.file_size > 0:
        files.append(
            SignedUrlResponse(
                filename="error.log",
                description="The error logs for this job.",
                signedUrl=get_signed_url(
                    settings.PROCESSED_FILES_BUCKET,
                    error_log.s3_key,
                    expiration=60 * 60 * 2,
                    filename="error.log",
                ),
                s3Key=error_log.s3_key,
                fileSize=error_log.file_size,
            )
        )

    return FileLinkResponse(files=files)
