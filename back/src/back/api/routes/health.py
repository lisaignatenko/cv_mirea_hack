from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"message": "pong"}
