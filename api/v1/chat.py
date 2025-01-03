from fastapi import APIRouter

from config import settings



# Update the router to include the database session dependency
router = APIRouter(prefix="/api/v1/chat", tags=["Chat API v1"])



@router.get("/status")
async def status() -> dict:
    return {"status": "ok"}

