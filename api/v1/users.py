import traceback
import boto3
from fastapi import APIRouter, Security, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user_models import User
from utils.auth import VerifyToken
from utils.logger import logger


auth = VerifyToken()


# Define request/response models
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    email: str
    cognito_id: str


# Update the router to include the database session dependency
router = APIRouter(prefix="/api/v1/users", tags=["Users API v1"])


@router.post("/signup", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_db)
) -> UserResponse:
    try:
        logger.info(f"Creating user: {user_data.email}")
        print(f"Creating user: {user_data.email}")
        # Create user in Cognito
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        cognito_response = cognito_client.sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=user_data.email,
            Password=user_data.password,
            UserAttributes=[
                {"Name": "email", "Value": user_data.email},
            ],
        )

        # Create user in database
        print("session", session)
        print("cognito_response", cognito_response)
        print("usersub", cognito_response["UserSub"])
        print("email", user_data.email)
        user = User.create(session=session, cognito_id=cognito_response["UserSub"], email=user_data.email)
        session.commit()

        return UserResponse(email=user.email, cognito_id=user.cognito_id)
    except Exception as e:
        print(e)
        # print stack trace
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(user_data: UserCreate, session: Session = Depends(get_db)):
    try:
        # Authenticate with Cognito
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        auth_response = cognito_client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": user_data.email, "PASSWORD": user_data.password},
        )

        return {
            "access_token": auth_response["AuthenticationResult"]["AccessToken"],
            "id_token": auth_response["AuthenticationResult"]["IdToken"],
            "refresh_token": auth_response["AuthenticationResult"]["RefreshToken"],
            "expires_in": auth_response["AuthenticationResult"]["ExpiresIn"],
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
