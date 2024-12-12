import traceback

import boto3
from fastapi import APIRouter, Depends, HTTPException, Security
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
    message: str


class UserVerification(BaseModel):
    email: EmailStr
    verification_code: str


class ConfirmForgotPassword(BaseModel):
    email: EmailStr
    new_password: str
    confirmation_code: str


class EmailRequest(BaseModel):
    email: EmailStr


class AccountInfo(BaseModel):
    email: EmailStr


# Update the router to include the database session dependency
router = APIRouter(prefix="/api/v1/users", tags=["Users API v1"])


@router.post("/signup", response_model=UserResponse)
async def create_user(user_data: UserCreate, session: Session = Depends(get_db)) -> UserResponse:
    try:
        logger.info(f"Creating user: {user_data.email}")

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
        user = User.create(
            session=session,
            cognito_id=cognito_response["UserSub"],
            email=user_data.email,
        )

        session.commit()

        return UserResponse(
            email=user.email,
            cognito_id=user.cognito_id,
            message="Please check your email for verification instructions",
        )
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}\n{traceback.format_exc()}")
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
            AuthParameters={
                "USERNAME": user_data.email,
                "PASSWORD": user_data.password,
            },
        )

        return {
            "email": user_data.email,
            "access_token": auth_response["AuthenticationResult"]["AccessToken"],
            "id_token": auth_response["AuthenticationResult"]["IdToken"],
            "refresh_token": auth_response["AuthenticationResult"]["RefreshToken"],
            "expires_in": auth_response["AuthenticationResult"]["ExpiresIn"],
        }
    except cognito_client.exceptions.UserNotConfirmedException:
        raise HTTPException(
            status_code=403,
            detail="User is not verified. Please check your email for verification instructions",
        )
    except (
        cognito_client.exceptions.NotAuthorizedException,
        cognito_client.exceptions.UserNotFoundException,
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        logger.error(f"Error during login: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during login")


@router.post("/verify")
async def verify_user(verification_data: UserVerification):
    try:
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        cognito_client.confirm_sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=verification_data.email,
            ConfirmationCode=verification_data.verification_code,
        )

        return {"message": "Email verified successfully"}
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-verification")
async def resend_verification(email_data: EmailRequest):
    try:
        # Create Cognito client
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        # Resend verification code
        cognito_client.resend_confirmation_code(ClientId=settings.COGNITO_CLIENT_ID, Username=email_data.email)

        return {"message": "Verification code resent successfully"}
    except Exception as e:
        logger.error(f"Error resending verification code: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forgot-password")
async def forgot_password(email_data: EmailRequest):
    try:
        # Create Cognito client
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        # Initiate forgot password flow
        cognito_client.forgot_password(ClientId=settings.COGNITO_CLIENT_ID, Username=email_data.email)

        return {"message": "If your email exists in our system, you will receive a password reset code"}
    except Exception as e:
        # Log the error but don't expose it to the user
        logger.error(f"Error initiating password reset: {str(e)}\n{traceback.format_exc()}")
        # Return the same message even if there's an error
        return {"message": "If your email exists in our system, you will receive a password reset code"}


@router.post("/confirm-forgot-password")
async def confirm_forgot_password(reset_data: ConfirmForgotPassword):
    try:
        # Create Cognito client
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        # Confirm forgot password
        cognito_client.confirm_forgot_password(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=reset_data.email,
            Password=reset_data.new_password,
            ConfirmationCode=reset_data.confirmation_code,
        )

        return {"message": "Password reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token")
async def refresh_token(refresh_token: str):
    try:
        boto_session = boto3.Session(profile_name=settings.AWS_PROFILE)
        cognito_client = boto_session.client("cognito-idp")

        auth_response = cognito_client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )

        return {
            "access_token": auth_response["AuthenticationResult"]["AccessToken"],
            "id_token": auth_response["AuthenticationResult"]["IdToken"],
            "expires_in": auth_response["AuthenticationResult"]["ExpiresIn"],
        }
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get("/verify-token")
async def verify_token(current_user=Security(auth.get_current_user)):
    """
    Endpoint to verify if a token is still valid.
    The Security dependency will raise a 401 if the token is invalid.
    """
    return {"message": "Token is valid"}


@router.get("/account/info", response_model=AccountInfo)
async def get_account_info(session: Session = Depends(get_db), current_user=Security(auth.get_current_user)):
    cognito_id = current_user["sub"]
    user = User.get_by_cognito_id(session, cognito_id)
    return {"email": user.email}
