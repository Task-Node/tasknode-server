from datetime import datetime
from fastapi import APIRouter, HTTPException, Security, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from config import settings
from database import get_db
from models.job_models import Job, JobFiles
from models.user_models import User
from utils.auth import VerifyToken
from utils.s3 import get_signed_upload_url


auth = VerifyToken()


# Update the router to include the database session dependency
router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs API v1"])


class SignedUrlResponse(BaseModel):
    signedUrl: str
    s3Key: str


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
        settings.FILE_DROP_BUCKET, filename, "application/zip", 30, cognito_id=cognito_id
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
        JobResponseItem(id=str(job.id), status=job.status.value, runtime=job.runtime, created_at=job.created_at, updated_at=job.updated_at)
        for job in jobs
    ]
    return JobResponse(jobs=response_items, total_count=total_count)


@router.get("/get/{job_id}", response_model=JobResponseItem)
async def get_job(
    job_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: dict = Security(auth.get_current_user),
) -> JobResponseItem:
    cognito_id = current_user["sub"]
    user: User = User.get_by_cognito_id(session, cognito_id)
    job: Job = Job.get_by_id(session, job_id, user.id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get associated files
    job_files = JobFiles.get_by_job_id(session, job_id)
    files = [
        JobFileItem(
            file_name=f.file_name,
            file_size=f.file_size,
            file_timestamp=f.file_timestamp,
        )
        for f in job_files
    ]
    
    return JobResponseItem(
        id=str(job.id),
        status=job.status.value,
        runtime=job.runtime,
        created_at=job.created_at,
        updated_at=job.updated_at,
        files=files
    )
