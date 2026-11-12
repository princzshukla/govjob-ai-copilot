import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

<<<<<<< HEAD
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.api.v1.endpoints import (
    candidate,
    eligibility,
    notifications,
    adaptive,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
=======
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import candidate, eligibility, notifications
>>>>>>> 48eff3084592803c8a6cf3556c304aa6936a3a3d


app = FastAPI(
    title="GovJob Matcher & AI Roadmap API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidate.router, prefix="/api/v1")
app.include_router(eligibility.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
<<<<<<< HEAD
app.include_router(adaptive.router, prefix="/api/v1/adaptive", tags=["Adaptive Preparation"])
=======
>>>>>>> 48eff3084592803c8a6cf3556c304aa6936a3a3d


@app.get("/health")
async def health_check():
    return {"status": "ok"}
