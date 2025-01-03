import os

from .default import Default


class Production(Default):
    class Config:
        env_file = ".env.production"
        env_file_encoding = "utf-8"

    ENV: str = "Production"

    # # Note: Serverless adds /prd to the root path when you deploy to prd, so you need to set that here
    # # unless using a custom domain.
    # ROOT_PATH: str = "/prd"

    CUSTOM_DOMAIN: str = "chai-chat-api-prd.foobar.dev"
