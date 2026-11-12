# app/api/v1/endpoints/candidate.py
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.v1.deps import optional_current_user, user_or_ip_key
from app.core.rate_limit import limiter
from app.models.auth import User
from app.schemas.candidate import ResumeParseResponse
from app.services.parser import extract_raw_text_from_pdf, parse_resume_with_groq

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate", tags=["Candidate"])

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB
PDF_MAGIC = b"%PDF-"
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


def _resume_upload_limit(key: str) -> str:
    """Per-account quota for signed-in users, tighter per-IP quota for guests."""
    return "20/day" if key.startswith("user:") else "3/day"


@router.post("/parse-resume", response_model=ResumeParseResponse)
@limiter.limit(_resume_upload_limit, key_func=user_or_ip_key)
async def upload_and_parse_resume(
    request: Request,
    file: UploadFile = File(...),
    _user: User | None = Depends(optional_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume uploads are currently supported.",
        )

    # Read at most one byte past the cap, so an oversized upload is rejected
    # without buffering the whole body.
    pdf_bytes = await file.read(MAX_RESUME_BYTES + 1)
    if len(pdf_bytes) > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Resume file must be 5 MB or smaller.",
        )

    # Content-Type is client supplied; the PDF signature is not.
    if not pdf_bytes.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume uploads are currently supported.",
        )

    try:
        raw_text = extract_raw_text_from_pdf(pdf_bytes)
    except Exception:
        logger.exception("Failed to extract text from uploaded resume")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read the PDF file.",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from PDF. It may be scanned or image-only.",
        )

    try:
        return await parse_resume_with_groq(raw_text)
    except HTTPException:
        raise
    except Exception:
        # Never echo exception text: it can leak prompts, keys or internal paths.
        logger.exception("Resume parsing failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resume parsing failed. Please try again later.",
        )
