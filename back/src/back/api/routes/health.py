from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"message": "pong"}


@router.get("/health/ping")
async def health_ping() -> dict[str, str]:
    return {"status": "ok"}
