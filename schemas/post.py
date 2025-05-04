from pydantic import BaseModel

class PostBase(BaseModel):
    title : str 
    content : str 
    username : str
    is_anonymous : bool

class CommentBase(BaseModel):
    content : str
    username : str
    post_id : str 

class PostUpdate(BaseModel):
    title : str 
    content : str 
