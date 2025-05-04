from schemas.post import PostBase, CommentBase, PostUpdate
from utils import serializer
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from database import insert_post, get_all_posts, get_post_by_id, get_user_id
from uuid import UUID
from database import add_upvote, remove_upvote, has_upvoted
from database import insert_comment, get_comments 
from database import delete_post as db_delete_post, update_post as db_update_post

router = APIRouter()

@router.post("/api/new-post")
def new_post(post : PostBase):
    add_to_db = insert_post(post.username, post.title, post.content, post.is_anonymous)
    if add_to_db:
        return JSONResponse(
            status_code = 201,
            content = {"message" : "Successfully posted your issue"}
        )
    else :
        return JSONResponse(
            status_code = 400,
            content = {"message" : "Failed to post"}
        )
    
@router.get("/api/posts")
def get_posts(status : str, sort : str):
    if status == "":
        status = None
    posts = get_all_posts(status, sort)
    
    if len(posts) == 0:
        return JSONResponse(
            status_code = 400,
            content = {"message" : "No posts found"}
        )
    
    if posts:
        return JSONResponse(
            status_code = 200,
            content = {"posts" : posts}
        )
    else :
        return JSONResponse(
            status_code = 400,
            content = {"message" : "Failed to get posts"}
        )

@router.get("/api/posts/{post_id}")
def get_post(post_id: str):
    try:
        post = get_post_by_id(post_id)
        if post:
            return JSONResponse(status_code=200, content={"post": post})
        return JSONResponse(status_code=404, content={"message": "Post not found"})
    except Exception as e:
        print(" API error:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/api/upvote/check/{post_id}")
def check_upvote(post_id: str, username: str = Query(...)):
    try:
        post_id = UUID(post_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"message": "Invalid post ID"})

    user_id = get_user_id(username)
    if not user_id:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    upvoted = has_upvoted(post_id, user_id)
    return JSONResponse(status_code=200, content={"upvoted": upvoted})

@router.post("/api/upvote/{post_id}")
def upvote_toggle(post_id: str, username: str = Query(...)):
    try:
        post_id = UUID(post_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"message": "Invalid post ID"})

    user_id = get_user_id(username)
    if not user_id:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    if has_upvoted(post_id, user_id):
        removed = remove_upvote(post_id, user_id)
        return JSONResponse(status_code=200, content={"message": "Removed"})
    else:
        added = add_upvote(post_id, user_id)
        return JSONResponse(status_code=200, content={"message": "Upvoted"})

                           
@router.post("/api/comment/{post_id}")
def comment(comment : CommentBase):
    post_id = UUID(comment.post_id)
    user_id = get_user_id(comment.username)
    if not user_id:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    if post_id and user_id:
        add_comment = insert_comment(comment.content, post_id, user_id)
        if add_comment:
            return JSONResponse(
                status_code = 201,
                content = {"message" : "Successfully posted your comment"}
            )
        else :
            return JSONResponse(
                status_code = 400,
                content = {"message" : "Failed to post"}
            )
    else:
        return JSONResponse(
            status_code = 400,
            content = {"message" : "Failed to post"}
        )  

@router.get("/api/comments/{post_id}")
def get_comments_by_post_id(post_id: str):
    try:
        post_id = UUID(post_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"message": "Invalid post ID"})

    comments = get_comments(post_id)
    if comments:
        return JSONResponse(status_code=200, content={"comments": comments})
    #It's possible that there are no comments for the post
    return JSONResponse(status_code=200, content={"comments": []})
    

@router.delete("/api/post/{post_id}")
def delete_post_route(post_id: str):
    try:
        post_id = UUID(post_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"message": "Invalid post ID"})

    # Use the imported database function, not the route function
    delete_result = db_delete_post(post_id)
    if delete_result:
        return JSONResponse(status_code=200, content={"message": "Post deleted successfully"})
    else:
        return JSONResponse(status_code=400, content={"message": "Failed to delete post"})
    
@router.put("/api/post/{post_id}")
def update_post_route(post_id: str, post: PostUpdate):
    try:
        post_id = UUID(post_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"message": "Invalid post ID"})
    
    # Use the imported database function, not the route function
    update_result = db_update_post(post_id, post.title, post.content)
    if update_result:
        return JSONResponse(status_code=200, content={"message": "Post updated successfully"})
    else:
        return JSONResponse(status_code=400, content={"message": "Failed to update post"})

