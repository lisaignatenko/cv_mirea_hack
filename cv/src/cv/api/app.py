from fastapi import FastAPI

from cv.api.routes.health import router as health_router
from cv.api.routes.workflow import router as workflow_router


def app() -> FastAPI:
    app = FastAPI(title="ml service")

    # /ping
    app.include_router(health_router)

    # /something
    app.include_router(workflow_router)

    return app
