import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints import adaptive, auth, candidate, eligibility, notifications, users
from app.core.config import settings
from app.core.rate_limit import limiter


# Keep explicit origins from env and include origins added on main.
_cors_origins = list(
    dict.fromkeys(
        settings.cors_origins_list
        + [
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ]
    )
)

app = FastAPI(
    title="GovJob Matcher & AI Roadmap API",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Default FastAPI 422 bodies echo the submitted value in "input"; never
    # return passwords (or anything else sensitive) back to the client.
    errors = []
    for err in exc.errors():
        cleaned = {k: v for k, v in err.items() if k != "input"}
        if "password" in [str(part) for part in err.get("loc", ())]:
            cleaned["msg"] = "Invalid password format"
        errors.append(cleaned)
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": errors}))


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,  # exact origins only, never "*" with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidate.router, prefix="/api/v1")
app.include_router(eligibility.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(adaptive.router, prefix="/api/v1/adaptive", tags=["Adaptive Preparation"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}