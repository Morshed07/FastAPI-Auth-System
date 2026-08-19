import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.users import router as users_router

app = FastAPI(
    title="Ecommerce Backend API",
    description="This is a Simple Ecommerce Backend API",
    version="1.0.0",
)

# Ensure uploads folder exists
os.makedirs("uploads/avatars", exist_ok=True)

# Serve files inside "uploads" directory at "/uploads" URL route
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(users_router, prefix="/api/v1")


@app.get('/')
async def root():
    return {"message": "FastAPI Learning"}
