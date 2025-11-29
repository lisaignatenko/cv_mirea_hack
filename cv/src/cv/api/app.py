from fastapi import FastAPI

from cv.api.routes.health import router as health_router
from cv.api.routes.segment import router as segment_router
from cv.api.routes.workflow import router as workflow_router

app = FastAPI(title="ml service")

# /ping
app.include_router(health_router)

# /something
app.include_router(workflow_router)

# /segment
app.include_router(segment_router)


def create_app() -> FastAPI:
    return app
