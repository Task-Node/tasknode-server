# https://www.serverless.com/plugins/serverless-python-requirements#dealing-with-lambdas-size-limitations
# sourcery skip: use-contextlib-suppress
try:
    import unzip_requirements  # type: ignore # noqa: F401
except ImportError:
    pass

import json
from database import init_engine, db_session
from models.user_models import User
from utils.logger import logger

def handle_user_signup(event, context):
    init_engine()  # Initialize the database engine

    # Get the email from the event
    try:
        email = event.get("request", {}).get("userAttributes", {}).get("email")
        cognito_id = event.get("userName")
        User.create(db_session, email=email, cognito_id=cognito_id)
        db_session.commit()
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        db_session.rollback()
        return {"statusCode": 500, "body": json.dumps("An error occurred while creating the user record")}
    finally:
        db_session.close()
        db_session.remove()
    return event
