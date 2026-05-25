import os
import secrets
import uuid
import filetype
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from logger_config import setup_logger

load_dotenv()

logger = setup_logger("safe_deploy")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

MAX_FILE_SIZE = 2 * 1024 * 1024
STORAGE_DIR = "storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    logger.critical("ENCRYPTION_KEY not set in .env")
    raise RuntimeError("ENCRYPTION_KEY not set in .env")
cipher = Fernet(ENCRYPTION_KEY.encode())

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "We are sorry, something went wrong."}
    )

@app.get("/cause_error")
def cause_error():
    logger.info("Test endpoint /cause_error called")
    return 1 / 0

users_db = {
    "alice": {"username": "alice", "role": "user", "password": "alice123"},
    "bob":   {"username": "bob",   "role": "user", "password": "bob123"},
    "admin": {"username": "admin", "role": "admin", "password": "admin123"},
}

files_db = [
    {"id": 1, "original_name": "report_alice.pdf", "owner": "alice", "size": 1024, "path": None, "uploaded_at": None, "is_encrypted": False},
    {"id": 2, "original_name": "photo_bob.jpg",    "owner": "bob",   "size": 2048, "path": None, "uploaded_at": None, "is_encrypted": False},
    {"id": 3, "original_name": "admin_keys.txt",   "owner": "admin", "size": 12,   "path": None, "uploaded_at": None, "is_encrypted": False},
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
        logger.warning(f"Access denied: User '{current_user['username']}' tried to access file {file_id} (owner: {file['owner']})")
        raise HTTPException(status_code=404, detail="File not found")
    return file

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = users_db.get(username)
    if not user or user["password"] != password:
        logger.warning(f"Failed login attempt for username: {username} from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["user"] = {"username": user["username"], "role": user["role"]}
    logger.info(f"User '{username}' logged in successfully from {request.client.host}")
    return JSONResponse(content={"msg": "Login successful"})

@app.post("/logout")
def logout(request: Request):
    user = request.session.get("user")
    if user:
        logger.info(f"User '{user['username']}' logged out")
    request.session.clear()
    return {"msg": "Logged out"}

@app.get("/files/my")
def get_my_files(current_user: dict = Depends(get_current_user)):
    my_files = [f for f in files_db if f["owner"] == current_user["username"]]
    logger.info(f"User '{current_user['username']}' listed their files ({len(my_files)} items)")
    return my_files

@app.get("/files/all")
def get_all_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logger.info(f"Admin '{current_user['username']}' listed all files")
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
    logger.info(f"File deleted: id={file['id']}, name={file['original_name']}, owner={file['owner']}")
    return {"msg": "File deleted"}

@app.post("/files/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    encrypt: bool = False,
    current_user: dict = Depends(get_current_user)
):
    file_content = await file.read()
    total_size = len(file_content)
    if total_size > MAX_FILE_SIZE:
        logger.warning(f"User '{current_user['username']}' tried to upload file larger than limit: {total_size} bytes")
        raise HTTPException(status_code=413, detail="File too large (max 2 MB)")

    if encrypt:
        data_to_save = cipher.encrypt(file_content)
        logger.info(f"Encrypting file '{file.filename}' (size: {total_size})")
    else:
        data_to_save = file_content

    file_uuid = str(uuid.uuid4())
    temp_path = os.path.join(STORAGE_DIR, file_uuid)
    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(data_to_save)
    except Exception as e:
        logger.error(f"Failed to save file '{file.filename}': {e}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail="Upload failed")

    if not encrypt:
        with open(temp_path, "rb") as f:
            head = f.read(2048)
        kind = filetype.guess(head)
        allowed_mimes = ["image/jpeg", "image/png"]
        if kind is None or kind.mime not in allowed_mimes:
            os.remove(temp_path)
            logger.warning(f"User '{current_user['username']}' tried to upload invalid file type: {file.filename}")
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
        "is_encrypted": encrypt,
    }
    files_db.append(new_file_record)

    logger.info(f"File uploaded: id={new_id}, name={file.filename}, owner={current_user['username']}, encrypted={encrypt}")
    return {"msg": "File uploaded", "file_id": new_id, "original_name": file.filename, "encrypted": encrypt}

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

    with open(file_path, "rb") as f:
        stored_data = f.read()

    if file_record.get("is_encrypted", False):
        try:
            decrypted_data = cipher.decrypt(stored_data)
        except Exception as e:
            logger.error(f"Decryption failed for file {file_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Decryption failed")
        return_data = decrypted_data
    else:
        return_data = stored_data

    logger.info(f"File downloaded: id={file_id}, name={file_record['original_name']}, owner={file_record['owner']}, user={current_user['username']}")
    return Response(
        content=return_data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{file_record['original_name']}\""}
    )

@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Secure Encrypted File Storage"}
