from fastapi import APIRouter, HTTPException
from .models import UserSignup, UserLogin
from .database import users_collection
from .utils import hash_password, verify_password, create_access_token
import re

auth_router = APIRouter()


def validate_password(password: str):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character"
    return True, None


@auth_router.post("/signup")
def signup(user: UserSignup):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    valid, msg = validate_password(user.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pw = hash_password(user.password)
    users_collection.insert_one({
        "username": user.username,
        "password": hashed_pw
    })
    return {"msg": "User created successfully"}


@auth_router.post("/login")
def login(user: UserLogin):
    db_user = users_collection.find_one({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
