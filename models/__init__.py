"""
Import all models below as well as Base. Then import Base below into alembic/env.py,
which forces alembic to run through the models code and pick up all children of Base
"""

from .job_models import *
from .user_models import *
from database import Base  # for import into alembic/env.py
