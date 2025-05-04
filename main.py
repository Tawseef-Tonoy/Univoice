from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from utils import serializer
from routes import auth, posts, profile

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(profile.router)


@app.get("/")
def main_page(request: Request):
    session = request.cookies.get("session")
    if session:
        return RedirectResponse("/home")
    else :
        return RedirectResponse("/login")



@app.get("/register")
def display_registration_page(request : Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login")
def display_login_page(request : Request):
    return templates.TemplateResponse("login.html",{"request": request})

@app.get("/home")
def display_home(request: Request):
    session = request.cookies.get("session")
    if not session:
        return RedirectResponse("/login")
    
    try:
        data = serializer.loads(session)
        username = data.get("username")
        print(f"Decoded session for user: {username}")
        role = data.get("role")

        return templates.TemplateResponse("home.html",
                {"request": request, 
                 "username": username, 
                 "role": role})
    
    except Exception as e:
        print(f"Session decode error: {e}")
        return RedirectResponse("/login")
    
    
@app.get("/new-post")
def display_post_page(request: Request):
    session = request.cookies.get("session")
    if not session:
        return RedirectResponse("/login")
    
    try :
        data = serializer.loads(session)
        username = data.get("username")
        role = data.get("role")
        return templates.TemplateResponse("new-post.html",{"request" : request, "username": username, "role" : role})
    except Exception as e:
        print("Invalid session:", e)
        return RedirectResponse("/login")
    

@app.get("/profile")
def display_profile_page(request: Request):
    session = request.cookies.get("session")
    if not session:
        return RedirectResponse("/login")
    
    try:
        data = serializer.loads(session)
        username = data.get("username")
        role = data.get("role")
        print(f"Decoded session for user: {username}")
        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "username": username,
                "role": role
            }
        )
    except Exception as e:
        print(f"Session decode error: {e}")
        return RedirectResponse("/login")    
    



    


