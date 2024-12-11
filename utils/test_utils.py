"""Helper utilities for testing."""

from sqlalchemy.orm.session import close_all_sessions

from database import db_session, drop_db, init_db


class BaseTestCase:
    def setup_method(self):
        init_db()
        self.session = db_session

    def teardown_method(self):
        self.session.rollback()
        close_all_sessions()
        drop_db()
