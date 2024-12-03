import os

from .default import Default


class Development(Default):
    class Config:
        env_file = '.env.dev'
        env_file_encoding = 'utf-8'

    ENV: str = "Development"

    # Note: Serverless adds /dev to the root path when you deploy to dev, so you need to set that here
    # unless using a custom domain.
    # ROOT_PATH: str = "/dev"

    CUSTOM_DOMAIN: str = "api-dev.tasknode.dev"
