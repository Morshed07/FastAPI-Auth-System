import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import init_redis, close_redis
from app.api.v1.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis connection pool
    await init_redis()
    
    # Ensure DB tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    
    # Shutdown: Close Redis connection pool
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production Grade FastAPI Auth System with JWT, Redis OTP, and Async Email Queue",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Ensure uploads folder exists
os.makedirs("uploads/avatars", exist_ok=True)

# Serve files inside "uploads" directory at "/uploads" URL route
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)


@app.get('/')
async def root():
    return {
        "message": "FastAPI Auth System API is running",
        "docs": "/docs"
    }
