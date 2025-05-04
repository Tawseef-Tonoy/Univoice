from fastapi import APIRouter
from schemas.user import UserCreate, UserLogin
from fastapi.responses import JSONResponse, RedirectResponse

from utils import create_password_hash, serializer, verify_password
from database import create_user,get_user_data
router = APIRouter()

@router.post("/api/register")
def register_user(user: UserCreate):
    password_hash = create_password_hash(user.password)
    user_creation = create_user(user.name,user.username,password_hash,user.email,user.role)
    if user_creation:
        return JSONResponse(
            status_code = 201,
            content = {'message' : "User Registration has completed successfully"}
        )
    else:
        return JSONResponse(
            status_code = 400,
            content = {'message' : "Username or Email already exists. Try a different one"}
        )
    
@router.post("/api/login")
def login_user(user: UserLogin):
    user_data = get_user_data(user.username)
    if user_data: 
        if verify_password(user.password, user_data["password_hash"]): 
            token = serializer.dumps({"username" : user_data["username"], "role": user_data["role"]})
            response = JSONResponse(
                status_code=200,
                content= {"message": "Login successful. Directing to home page...",
                        "redirect_to": "/home"}
                )
            response.set_cookie(
                key="session",
                value=token,
                httponly=True,
                secure=True,
                samesite="Lax",
                path="/",
                max_age=60 * 60 * 24  
            )

            return response
        else: 
            return JSONResponse(
            status_code = 400,
            content = {'message' : "Wrong Password"}
        )
    else:
        return JSONResponse(
        status_code = 400,
        content = {'message' : "Username doesn't exist"}
    )

@router.post('/api/logout')
def logout_user():
    response = JSONResponse(
    content={"message": "Logged out successfully"},
    status_code=200)
    response.delete_cookie("session")
    return response





