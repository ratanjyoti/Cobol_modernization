# JWT Implementation
from fastapi import APIRouter, HTTPException, Depends
from app.models.project import UserAuth
from app.database.sqlite_db import db
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()

@router.post("/register")
async def register(user: UserAuth):
    try:
        hashed = hash_password(user.password)
        db.create_user(user.username, hashed)
        return {"message": "User created successfully"}
    except Exception:
        raise HTTPException(status_code=400, detail="Username already exists")

@router.post("/login")
async def login(user: UserAuth):
    user_data = db.authenticate_user(user.username)
    if not user_data or not verify_password(user.password, user_data[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"user_id": user_data[0], "username": user.username})
    return {"access_token": token, "token_type": "bearer"}
