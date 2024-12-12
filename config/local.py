import os

from .default import Default


class Local(Default):
    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"

    ENV: str = "Local"
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("SQLALCHEMY_DATABASE_URI") or "postgresql://localhost:5432/tasknode"
