from fastapi import APIRouter
from api.endpoints.user import router as user_router

router = APIRouter()

router.include_router(user_router, prefix="/users", tags=["users"])
