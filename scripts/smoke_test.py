"""Run against a running Compose stack: python3 scripts/smoke_test.py.
Creates one uniquely named user, post, comment, and vote; retains them for inspection.
"""
import argparse
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

base = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
cookies = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def request(method, path, data=None, expected=200):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        response = client.open(req, timeout=15)
    except urllib.error.HTTPError as exc:
        raise AssertionError(f"{method} {path}: {exc.code}: {exc.read().decode()}") from exc
    with response:
        payload = response.read().decode()
        assert response.status == expected, (path, response.status, payload)
        return json.loads(payload) if payload and response.headers.get_content_type() == "application/json" else payload


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--save-state", type=Path, help="Save test credentials for a later persistence check")
parser.add_argument("--verify-state", type=Path, help="Verify previously saved data without creating new data")
args = parser.parse_args()
if args.save_state and args.verify_state:
    parser.error("Choose either --save-state or --verify-state")

if args.verify_state:
    state = json.loads(args.verify_state.read_text())
    username, password, post_id = (state[key] for key in ("username", "password", "post_id"))
    request("GET", "/health")
    request("POST", "/api/login", {"username": username, "password": password})
    assert username in request("GET", "/home"), "Restored user could not access home"
    post = request("GET", f"/api/posts/{post_id}")["post"]
    assert post["title"] == username and post["content"] == "Docker smoke test post"
    assert post["upvotes"] == 1 and post["comments"] == 1, post
    comments = request("GET", f"/api/comments/{post_id}")["comments"]
    assert any(c["content"] == "Docker smoke test comment" and c["username"] == username for c in comments)
    query = urllib.parse.urlencode({"username": username})
    assert request("GET", f"/api/upvote/check/{post_id}?{query}")["upvoted"] is True
    profile = request("GET", f"/api/profile/{username}")
    assert profile["user_info"]["username"] == username
    assert any(p["post_id"] == post_id and p["upvotes"] == 1 and len(p["comments"]) == 1 for p in profile["posts"])
    print("PASS persistence: existing user login, post, comment, upvote, counts, and profile")
    raise SystemExit(0)

username = "smoke_" + uuid.uuid4().hex[:12]
password = uuid.uuid4().hex
request("GET", "/health")
request("POST", "/api/register", {"name": "Compose smoke test", "username": username,
        "email": username + "@example.com", "password": password}, expected=201)
print("PASS registration")
request("POST", "/api/login", {"username": username, "password": password})
assert any(cookie.name == "session" for cookie in cookies), "Login did not set a session"
home = request("GET", "/home")
assert username in home, "Session was not accepted by /home (check cookie HTTPS setting)"
print("PASS login and authenticated home")
request("POST", "/api/new-post", {"username": username, "title": username,
        "content": "Docker smoke test post", "is_anonymous": False}, expected=201)
posts = request("GET", "/api/posts?status=&sort=latest")["posts"]
post = next(post for post in posts if post["title"] == username)
post_id = post["id"]
assert request("GET", f"/api/posts/{post_id}")["post"]["content"] == "Docker smoke test post"
print("PASS posting, list, and detail")
request("POST", f"/api/comment/{post_id}", {"username": username, "post_id": post_id,
        "content": "Docker smoke test comment"}, expected=201)
comments = request("GET", f"/api/comments/{post_id}")["comments"]
assert any(c["content"] == "Docker smoke test comment" for c in comments)
print("PASS comments")
query = urllib.parse.urlencode({"username": username})
for expected in (True, False, True):
    request("POST", f"/api/upvote/{post_id}?{query}")
    assert request("GET", f"/api/upvote/check/{post_id}?{query}")["upvoted"] is expected
post = request("GET", f"/api/posts/{post_id}")["post"]
assert post["upvotes"] == 1 and post["comments"] == 1, post
profile = request("GET", f"/api/profile/{username}")
assert any(p["post_id"] == post_id for p in profile["posts"])
print("PASS upvote toggle, counts, and profile")
print(f"Retained verification data: username={username}, post_id={post_id}")

if args.save_state:
    # Contains a disposable user's password; keep it private and outside the repo.
    with open(args.save_state, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
        json.dump({"username": username, "password": password, "post_id": post_id}, output)
    print(f"Saved persistence-check state to {args.save_state}")
