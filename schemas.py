from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from .schemas import UserCreate

app = FastAPI(title="Corporate File Manager", description="Фейс-контроль регистрации")

@app.post("/registration")
async def register(user_data: UserCreate):
    return {"msg": "User created", "user": user_data.username}
