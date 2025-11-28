from fastapi import APIRouter

router = APIRouter(tags=["workflow"])


@router.post("/do_something")
async def do_something():
    raise NotImplementedError()
