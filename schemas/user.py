from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    name : str
    username : str
    email : EmailStr
    password : str
    role : str #student or admin 

class UserCreate(UserBase):
    role : str = "student"

class UserLogin(BaseModel):
    username : str
    password : str 