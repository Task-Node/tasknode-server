from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import os
from typing import List

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
    AWS_PROFILE: str | None = None
    ADMIN_EMAILS: List[str] = []

    API_KEY: str = os.environ["API_KEY"]
    API_URL: str = os.environ["API_URL"]

    CACHE_DISABLED: bool = False

    # VPC Configuration
    VPC_SECURITY_GROUP_IDS: List[str] = os.environ["VPC_SECURITY_GROUP_IDS"]
    VPC_SUBNET_IDS: List[str] = os.environ["VPC_SUBNET_IDS"]
