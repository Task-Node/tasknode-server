# https://www.serverless.com/plugins/serverless-python-requirements#dealing-with-lambdas-size-limitations
# sourcery skip: use-contextlib-suppress
try:
    import unzip_requirements  # type: ignore # noqa: F401
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from mangum import Mangum


from database import init_engine
from exceptions import TaskNodeException
from config import settings
from api.v1 import jobs, users
from utils.logger import logger


def create_app():
    if settings.SQLALCHEMY_DATABASE_URI:
        logger.info(f"Initializing database engine with URI: {settings.SQLALCHEMY_DATABASE_URI}")
        init_engine()
        logger.info("Database engine initialized")

    logger.info("Creating FastAPI app")
    app = FastAPI(
        root_path=settings.ROOT_PATH if not settings.CUSTOM_DOMAIN else None,
    )

    logger.info("Adding middleware")
    app.add_middleware(
        CORSMiddleware,  # For handling CORS (https://fastapi.tiangolo.com/tutorial/cors/)
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=86400,  # Bump for browsers that support > 600 seconds like firefox
    )

    # Handles GZip responses for any request that includes "gzip" in the `Accept-Encoding`` header.
    # (https://fastapi.tiangolo.com/advanced/middleware/#gzipmiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    logger.info("Including routers")
    app.include_router(jobs.router)
    app.include_router(users.router)

    @app.get("/", include_in_schema=False)
    async def home():
        return RedirectResponse("/docs")

    @app.get("/status")
    async def status():
        return {"status": "ok"}

    @app.exception_handler(TaskNodeException)
    async def app_exception_handler(req, exc: TaskNodeException):
        return JSONResponse(status_code=exc.status_code, content=dict(message=exc.message))

    return app


app = create_app()
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    logger.info("Lambda handler called")
    return handler(event, context)
