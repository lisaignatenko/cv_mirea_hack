from fastapi import FastAPI

from back.api.routes.health import router as health_router


def app() -> FastAPI:
    fastapi_app = FastAPI(title="back service")

    fastapi_app.include_router(health_router)

    return fastapi_app
