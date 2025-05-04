from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from utils import format_time_ago, helper_query
from uuid import UUID
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# Use MySQL connection string format
# Example: mysql+pymysql://username:password@localhost:3306/univoice

from sqlalchemy.pool import NullPool

engine = create_engine(DATABASE_URL, poolclass=NullPool)





def create_user(name,username,password_hash,email,role):
    with engine.connect() as conn:
        trans = conn.begin()
        try : 
            conn.execute(text("""
                INSERT INTO users (name, username, email, password_hash, role)
                VALUES (:name, :username, :email, :password_hash, :role)
            """), {
                "name": name,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role
            })
            trans.commit()
            return True 
        except:
            trans.rollback()
            return False 
        
def get_user_data(username):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users WHERE username = :username"), 
                              {"username" : username}).mappings().all()
        if len(result) == 0:
            return False 
        return result[0]

def insert_post(username, title, content, is_anonymous=False):
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            user_query = text("SELECT id FROM users WHERE username = :username")
            user_result = conn.execute(user_query, {"username": username}).fetchone()

            if not user_result:
                raise Exception("User not found")

            user_id = user_result[0]  

            insert_query = text("""
                INSERT INTO posts (user_id, title, content, status, is_anonymous, created_at)
                VALUES (:user_id, :title, :content, 'pending', :is_anonymous, NOW())
            """)
            conn.execute(insert_query, {
                "user_id": user_id,
                "title": title,
                "content": content,
                "is_anonymous": is_anonymous
            })

            trans.commit()
            print(" You posted successfully")
            return True
        
        except Exception as e:
            print(" Error inserting post:", e)
            trans.rollback()
            return False

        
def get_all_posts(status=None, sort="latest"):
    query = helper_query(status, sort)
    with engine.connect() as conn:
        results = conn.execute(text(query)).mappings().all()
    
    posts = []

    for row in results:
        post_dict = dict(row)

        # Convert UUIDs to strings
        for key, value in post_dict.items():
            if isinstance(value, UUID):
                post_dict[key] = str(value)

        # Add time_ago using created_at, then remove created_at
        post_dict["time_ago"] = format_time_ago(row["created_at"])
        post_dict.pop("created_at", None)  # Safely remove created_at

        posts.append(post_dict)

    return posts


def get_post_by_id(post_id):
    try:
        post_id = UUID(post_id)
    except ValueError:
        print("Invalid UUID format:", post_id)
        return False

    with engine.connect() as conn:
        query = text("""
            SELECT 
                posts.id,
                posts.title,
                posts.content,
                posts.status,
                posts.is_anonymous,
                posts.created_at,
                users.username,
                COALESCE(COUNT(DISTINCT upvotes.id), 0) AS upvotes,
                COALESCE(COUNT(DISTINCT comments.id), 0) AS comments
            FROM posts
            JOIN users ON posts.user_id = users.id
            LEFT JOIN upvotes ON upvotes.post_id = posts.id
            LEFT JOIN comments ON comments.post_id = posts.id
            WHERE posts.id = :post_id
            GROUP BY posts.id, posts.title, posts.content, posts.status, posts.is_anonymous, posts.created_at, users.username
        """)
        result = conn.execute(query, {"post_id": post_id}).mappings().all()

    if len(result) == 0:
        return False

    post_dict = dict(result[0])

    # Convert UUID to string
    post_dict["id"] = str(post_dict["id"])

    # Format time and remove created_at
    if "created_at" in post_dict:
        post_dict["time_ago"] = format_time_ago(post_dict["created_at"])
        post_dict.pop("created_at", None)
    else:
        post_dict["time_ago"] = "Unknown"

    return post_dict


def get_user_id(username):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM users WHERE username = :username"), 
                              {"username" : username}).mappings().all()
        if len(result) == 0:
            return False 
        return result[0]["id"]
    
def add_upvote(post_id, user_id):
    with engine.connect() as conn:
        with conn.begin():  # Ensure transaction
            result = conn.execute(text("""
                INSERT IGNORE INTO upvotes (post_id, user_id)
                VALUES (:post_id, :user_id)
            """), {"post_id": post_id, "user_id": user_id})
            return result.rowcount > 0  # True if inserted, False if skipped

def has_upvoted(post_id, user_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM upvotes
            WHERE post_id = :post_id AND user_id = :user_id
        """), {
            "post_id": post_id,
            "user_id": user_id
        }).scalar()

        return result > 0
    
def remove_upvote(post_id,user_id):
    with engine.connect() as conn:
        trans = conn.begin()
        result = conn.execute(text("""
            DELETE FROM upvotes
            WHERE post_id = :post_id AND user_id = :user_id
        """), {
            "post_id": post_id,
            "user_id": user_id
        })
        trans.commit()
        return result.rowcount > 0

# Add this function to database.py
def has_user_upvoted(post_id, username):
    user_id = get_user_id(username)
    if not user_id:
        return False
    
    return has_upvoted(post_id, user_id)

def insert_comment(content, post_id, user_id):
    with engine.connect() as conn:
        trans = conn.begin()
        try : 
            result = conn.execute(text("""
                INSERT INTO comments (content, post_id, user_id)
                VALUES (:content, :post_id, :user_id)
            """), { "content" : content,
                "user_id" : user_id,
                "post_id" : post_id})
            trans.commit()
            return True 
        except Exception as e:
            trans.rollback()
            print("Error inserting comment:", e)
            return False 
        
def get_comments(post_id):
    #complete this function
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT comments.content, comments.created_at, users.username
            FROM comments
            JOIN users ON comments.user_id = users.id
            WHERE comments.post_id = :post_id
        """), {"post_id": post_id}).mappings().all()
        comments = []
        for row in result:
            comment_dict = dict(row)
            comment_dict["time_ago"] = format_time_ago(row["created_at"])
            comment_dict.pop("created_at", None)
            comments.append(comment_dict)

        return comments
    

def update_post(post_id, new_title, new_content):
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            query = text("""
                UPDATE posts
                SET title = :title,
                    content = :content
                WHERE id = :post_id
            """)
            conn.execute(query, {
                "title": new_title,
                "content": new_content,
                "post_id": post_id
            })
            trans.commit()
            print("Post updated successfully")
            return True
        except Exception as e:
            trans.rollback()
            print(" Failed to update post:", e)
            return False


def delete_post(post_id):
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            query = text("DELETE FROM posts WHERE id = :post_id")
            conn.execute(query, {"post_id": post_id})
            trans.commit()
            print("Post deleted successfully")
            return True
        except Exception as e:
            trans.rollback()
            print("Failed to delete post:", e)
            return False   
        
####TAWSEEF####       
def get_user_profile(username):
    with engine.connect() as conn:
        # 1. Get user information
        user_result = conn.execute(text("""
            SELECT id, name, username, email, role
            FROM users
            WHERE username = :username
        """), {"username": username}).mappings().all()

        if not user_result:
            return False

        user = user_result[0]
        user_id = user["id"]

        # 2. Get all posts by the user with upvote count
        posts_result = conn.execute(text("""
            SELECT 
                p.id,
                p.title,
                p.content,
                p.is_anonymous,
                p.created_at,
                COUNT(u.id) as upvotes
            FROM posts p
            LEFT JOIN upvotes u ON p.id = u.post_id
            WHERE p.user_id = :user_id
            GROUP BY p.id, p.title, p.content, p.is_anonymous, p.created_at
        """), {"user_id": user_id}).mappings().all()

        posts = []
        for post in posts_result:
            post_dict = dict(post)
            post_id = post_dict["id"]

            # 3. Get comments for this post
            comments_result = conn.execute(text("""
                SELECT 
                    c.id,
                    c.content,
                    c.created_at,
                    u.username as author
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = :post_id
                ORDER BY c.created_at DESC
            """), {"post_id": post_id}).mappings().all()

            comments = [
                {
                    "id": str(comment["id"]),
                    "content": comment["content"],
                    "author": comment["author"],
                    "time_ago": format_time_ago(comment["created_at"])
                }
                for comment in comments_result
            ]

            # Format post data
            post_dict["post_id"] = str(post_dict.pop("id"))  # Rename id -> post_id
            post_dict["time_ago"] = format_time_ago(post["created_at"])
            post_dict["upvotes"] = int(post_dict["upvotes"])  # Ensure integer
            post_dict["comments"] = comments
            post_dict.pop("created_at", None)
            posts.append(post_dict)

        # 4. Return final data
        return {
            "user_info": {
                "name": user["name"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            },
            "posts": posts
        }