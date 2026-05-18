from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import secrets

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

# База пользователей
users_db = {
    "alice": {"username": "alice", "role": "user", "password": "alice123"},
    "bob":   {"username": "bob",   "role": "user", "password": "bob123"},
    "admin": {"username": "admin", "role": "admin", "password": "admin123"},
}

# База файлов
files_db = [
    {"id": 1, "filename": "report_alice.pdf", "owner": "alice", "size": 1024},
    {"id": 2, "filename": "photo_bob.jpg",    "owner": "bob",   "size": 2048},
    {"id": 3, "filename": "admin_keys.txt",   "owner": "admin", "size": 12},
]

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def check_file_permissions(file_id: int, current_user: dict = Depends(get_current_user)):
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    is_owner = (file["owner"] == current_user["username"])
    is_admin = (current_user["role"] == "admin")
    if not (is_owner or is_admin):
        raise HTTPException(status_code=404, detail="File not found")
    return file

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), request: Request):
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["user"] = {"username": user["username"], "role": user["role"]}
    return RedirectResponse(url="/", status_code=303)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

@app.get("/files/{file_id}")
def get_file_info(file: dict = Depends(check_file_permissions)):
    return {"id": file["id"], "filename": file["filename"], "owner": file["owner"], "size": file["size"]}

@app.delete("/files/{file_id}")
def delete_file(file: dict = Depends(check_file_permissions)):
    global files_db
    files_db = [f for f in files_db if f["id"] != file["id"]]
    return {"msg": "File deleted"}

@app.get("/files/my")
def get_my_files(current_user: dict = Depends(get_current_user)):
    my_files = [f for f in files_db if f["owner"] == current_user["username"]]
    return my_files

@app.get("/files/all")
def get_all_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return files_db

@app.get("/")
def root():
    return {"message": "Welcome. Use POST /login to authenticate."}
