import os

from .default import Default


class Test(Default):
    ENV: str = "Test"
    SQLALCHEMY_DATABASE_URI: str = (
        os.environ.get("SQLALCHEMY_DATABASE_URI") or "postgresql://localhost:5432/tasknode_test"
    )
