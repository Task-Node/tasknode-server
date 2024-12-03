import os
import sys
from database import init_db

import uvicorn

from utils.logger import logger
from utils.manager import Manager

manager = Manager()


@manager.command
def runserver():
    os.environ["RUNNING_LOCALLY"] = "true"

    # Visual Studio uses an older debug method that does not work with uvicorn hot reload
    if os.getenv("DISABLE_HOT_RELOAD", "").lower() == "true":
        from app import app

        uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")

    uvicorn.run("app:app", host="127.0.0.1", port=5000, log_level="info", reload=True)


@manager.command
def db():
    if sys.argv[2] == "init":
        logger.info("Initializing database")
        upgrade()
    elif sys.argv[2] == "migrate":
        logger.info(sys.argv, len(sys.argv))
        if len(sys.argv) < 4:
            logger.error("ERROR: Must include a message for the top of the migration file")
        elif len(sys.argv) > 4:
            logger.error("ERROR: Message must be surrounded with double quotes")
        else:
            message = " ".join(sys.argv[3:])
            migrate(message)
    elif sys.argv[2] == "upgrade":
        upgrade()
    elif sys.argv[2] == "downgrade":
        downgrade()
    else:
        logger.error("ERROR: Command must be 'db downgrade', 'db migrate' or 'db upgrade'")


def migrate(message):
    logger.info("Migrating database")
    command = f'alembic revision --autogenerate -m " {message}"'
    return os.system(command)


def upgrade():
    logger.info("Upgrading database")
    command = "alembic upgrade head"
    return os.system(command)


def downgrade():
    logger.info("Downgrading database")
    command = "alembic downgrade -1"
    return os.system(command)


if __name__ == "__main__":
    logger.info("Command: %s", sys.argv)
    sys.stdout.flush()
    manager.run()
