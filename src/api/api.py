from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter()

@router.get("/check_startup/")
async def check_startup() -> JSONResponse:
    return JSONResponse(status_code=204, content=None)

