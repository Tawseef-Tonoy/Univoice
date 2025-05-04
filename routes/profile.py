from database import get_user_profile
from fastapi.responses import JSONResponse
from fastapi import APIRouter
router = APIRouter()
@router.get("/api/profile/{username}")
def get_profile(username: str):
    profile = get_user_profile(username)
    if not profile:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    return JSONResponse(status_code=200, content=profile)
