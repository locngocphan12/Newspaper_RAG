from fastapi import FastAPI
from .auth import auth_router

app = FastAPI()

app.include_router(auth_router, prefix="/auth")

@app.get("/")
def root():
    return {"msg": "Backend running!"}
