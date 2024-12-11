import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Default(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    ENV: str = ""
    REGION: str = "us-east-1"
    SQLALCHEMY_DATABASE_URI: str = ""
    CUSTOM_DOMAIN: str = ""
    ROOT_PATH: str = ""
    AWS_PROFILE: str = ""
    ADMIN_EMAILS: List[str] = os.environ["ADMIN_EMAILS"]
    COGNITO_CLIENT_ID: str = os.environ["COGNITO_CLIENT_ID"]
    COGNITO_USER_POOL: str = os.environ["COGNITO_USER_POOL"]
    COGNITO_USER_POOL_ID: str = os.environ["COGNITO_USER_POOL_ID"]
    COGNITO_USER_POOL_REGION: str = "us-east-1"
    COGNITO_WEB_CLIENT_ID: str = "tasknode-dev-client"
    API_KEY: str = os.environ["API_KEY"]
    CACHE_DISABLED: bool = False

    AWS_ACCOUNT_ID: str = os.environ["AWS_ACCOUNT_ID"]

    ECS_CLUSTER: str = "TASKNODE-CLUSTER-DEV"
    ECS_TASK_EXECUTION_ROLE: str = "TASKNODE-TASK-EXECUTION-ROLE-DEV"

    # s3
    FILE_DROP_BUCKET: str = "tasknode-file-drop-dev"
    PROCESSED_FILES_BUCKET: str = "tasknode-processed-files-dev"

    # secret names
    RESEND_KEY: str = os.environ["RESEND_KEY"]

    # VPC Configuration
    VPC_SECURITY_GROUP_IDS: List[str] = os.environ["VPC_SECURITY_GROUP_IDS"]
    VPC_SUBNET_IDS: List[str] = os.environ["VPC_SUBNET_IDS"]
