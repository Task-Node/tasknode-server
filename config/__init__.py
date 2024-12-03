"""
To override settings locally, create a file in this directory called local_overrides.py with the following format

from .local import Local as LocalDefault
from .development import Development as DevelopmentDefault
from .production import Production as ProductionDefault

class Local(LocalDefault):
    # overrides go here

class Development(DevelopmentDefault):
    # overrides go here

class Production(ProductionDefault):
    # overrides go here
"""

import os

try:
    from .local_overrides import Local  # type: ignore
except ImportError:
    from .local import Local
try:
    from .local_overrides import Test  # type: ignore
except ImportError:
    from .test import Test
try:
    from .local_overrides import Development  # type: ignore
except ImportError:
    from .development import Development
try:
    from .local_overrides import Production  # type: ignore
except ImportError:
    from .production import Production


def get_settings(env=None):
    env = env or os.environ.get("env", "local").lower()
    if env in ("development", "dev"):
        return Development()
    elif env in ("production", "prd"):
        return Production()
    elif env.lower() == "test":
        return Test()
    else:
        return Local()


settings = get_settings()
