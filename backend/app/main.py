import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints import adaptive, admin, auth, candidate, eligibility, notifications, user_data, users
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter
from app.core.tasks import exam_deadline_expiry_loop, session_cleanup_loop

configure_logging()
logger = logging.getLogger("app")

# Error reporting is optional and off unless configured.
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("sentry initialized (environment=%s)", settings.ENVIRONMENT)

# Interactive docs are development-only; production serves no API schema.
# Keep ENVIRONMENT=production in the deploy env and /docs, /redoc and
# /openapi.json all respond 404.
enable_docs = settings.ENVIRONMENT != "production"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Idempotent seed: insert any missing SEED_EXAMS rows at startup (never
    # overwrites). The API tests still call _ensure_seed_exams as a safety
    # net because ASGITransport does not run the lifespan hook.
    try:
        from sqlalchemy import select as _select

        from app.core.database import AsyncSessionLocal
        from app.core.seed import upsert_seed_exams

        async with AsyncSessionLocal() as db:
            inserted = await upsert_seed_exams(db)
        if inserted:
            logger.info("seeded %d exam notifications (idempotent upsert)", inserted)
    except Exception:
        logger.exception("startup seed failed — continuing without it")

    # Prune expired sessions hourly in-process; the DELETE is idempotent, so
    # multiple workers doing it is fine. Also hide closed job notifications
    # twice a day (idempotent flag flip; the query-time filter in
    # eligibility covers a missed run).
    cleanup_task = asyncio.create_task(session_cleanup_loop())
    expiry_task = asyncio.create_task(exam_deadline_expiry_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        expiry_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
            await expiry_task


# Keep only origins from env. Dev defaults must not follow the build to prod:
# the deployment supplies exact HTTPS origins through CORS_ORIGINS there.
_cors_origins = list(dict.fromkeys(settings.cors_origins_list))

app = FastAPI(
    title="GovJob Matcher & AI Roadmap API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if enable_docs else None,
    redoc_url="/redoc" if enable_docs else None,
    openapi_url="/openapi.json" if enable_docs else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline hardening headers on every response.

    The API serves JSON, so its CSP is a deny-all box. HSTS is only set when
    the deployment is actually HTTPS (ENVIRONMENT=production).
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    # Per-user JSON must never be served from caches (shared or browser).
    # Also prevents a client from reusing a stale response after it changed.
    response.headers["Cache-Control"] = "no-store"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Last-resort JSON 500. Without a handler here the exception escapes the
    # middleware stack entirely and the client gets a connection-level
    # failure with no CORS headers (browser: "Failed to fetch").
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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
app.include_router(user_data.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(adaptive.router, prefix="/api/v1/adaptive", tags=["Adaptive Preparation"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}