"""Helper utilities for testing."""


from database import db_session, init_db, drop_db
from sqlalchemy.orm.session import close_all_sessions


class BaseTestCase:
    def setup_method(self):
        init_db()
        self.session = db_session

    def teardown_method(self):
        self.session.rollback()
        close_all_sessions()
        drop_db()
