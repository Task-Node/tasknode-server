from typing import Optional
from fastapi import APIRouter, Security, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from config import settings
from database import get_session
from models.user_models import User
from utils.auth import VerifyToken
from utils.s3 import get_signed_upload_url


auth = VerifyToken()


# Update the router to include the database session dependency
router = APIRouter(dependencies=[Depends(get_session)], prefix="/api/v1/jobs", tags=["Jobs API v1"])


class SignedUrlResponse(BaseModel):
    signedUrl: str
    s3Key: str


@router.get("/status")
async def status() -> dict:
    return {"status": "ok"}


@router.get("/get_zip_upload_url", response_model=SignedUrlResponse)
async def get_zip_upload_url() -> SignedUrlResponse:
    filename = f"{uuid.uuid4()}.zip"
    signed_url = get_signed_upload_url(settings.FILE_DROP_BUCKET, filename, "application/zip", 30)
    return SignedUrlResponse(signedUrl=signed_url, s3Key=filename)
