import os
import secrets
import uuid
import filetype
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

MAX_FILE_SIZE = 2 * 1024 * 1024
STORAGE_DIR = "storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

users_db = {
    "alice": {"username": "alice", "role": "user", "password": "alice123"},
    "bob":   {"username": "bob",   "role": "user", "password": "bob123"},
    "admin": {"username": "admin", "role": "admin", "password": "admin123"},
}

files_db = [
    {"id": 1, "original_name": "report_alice.pdf", "owner": "alice", "size": 1024, "path": None, "uploaded_at": None},
    {"id": 2, "original_name": "photo_bob.jpg",    "owner": "bob",   "size": 2048, "path": None, "uploaded_at": None},
    {"id": 3, "original_name": "admin_keys.txt",   "owner": "admin", "size": 12,   "path": None, "uploaded_at": None},
]
next_file_id = 4

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def check_file_permissions(file_id: int, current_user: dict = Depends(get_current_user)):
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if not (file["owner"] == current_user["username"] or current_user["role"] == "admin"):
        raise HTTPException(status_code=404, detail="File not found")
    return file

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["user"] = {"username": user["username"], "role": user["role"]}
    return JSONResponse(content={"msg": "Login successful"})

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"msg": "Logged out"}

@app.get("/files/my")
def get_my_files(current_user: dict = Depends(get_current_user)):
    my_files = [f for f in files_db if f["owner"] == current_user["username"]]
    return my_files

@app.get("/files/all")
def get_all_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return files_db

@app.get("/files/{file_id}")
def get_file_info(file: dict = Depends(check_file_permissions)):
    return file

@app.delete("/files/{file_id}")
def delete_file(file: dict = Depends(check_file_permissions)):
    global files_db
    if file["path"]:
        file_path = os.path.join(STORAGE_DIR, file["path"])
        if os.path.exists(file_path):
            os.remove(file_path)
    files_db = [f for f in files_db if f["id"] != file["id"]]
    return {"msg": "File deleted"}

@app.post("/files/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    total_size = 0
    chunk_size = 1024 * 1024
    file_uuid = str(uuid.uuid4())
    temp_path = os.path.join(STORAGE_DIR, file_uuid)

    try:
        with open(temp_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    os.remove(temp_path)
                    raise HTTPException(status_code=413, detail="File too large (max 2 MB)")
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail="Upload failed")

    with open(temp_path, "rb") as f:
        head = f.read(2048)
    kind = filetype.guess(head)
    allowed_mimes = ["image/jpeg", "image/png"]
    if kind is None or kind.mime not in allowed_mimes:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed")

    global next_file_id
    new_id = next_file_id
    next_file_id += 1

    new_file_record = {
        "id": new_id,
        "original_name": file.filename,
        "owner": current_user["username"],
        "size": total_size,
        "path": file_uuid,
        "uploaded_at": None,
    }
    files_db.append(new_file_record)

    return {"msg": "File uploaded", "file_id": new_id, "original_name": file.filename}

@app.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    file_record: dict = Depends(check_file_permissions)
):
    if not file_record["path"]:
        raise HTTPException(status_code=404, detail="File not found on disk")
    file_path = os.path.join(STORAGE_DIR, file_record["path"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=file_path,
        filename=file_record["original_name"],
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{file_record['original_name']}\""}
    )

@app.get("/")
def root():
    return {"message": "Welcome to Secure File Storage"}
