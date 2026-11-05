# app/api/v1/endpoints/candidate.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.schemas.candidate import ResumeParseResponse
from app.services.parser import extract_raw_text_from_pdf, parse_resume_with_groq

router = APIRouter(prefix="/candidate", tags=["Candidate"])

@router.post("/parse-resume", response_model=ResumeParseResponse)
async def upload_and_parse_resume(file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf", "application/octet-stream"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume uploads are currently supported."
        )

    try:
        pdf_bytes = await file.read()
        raw_text = extract_raw_text_from_pdf(pdf_bytes)

        if not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from PDF. It may be scanned or image-only."
            )

        return await parse_resume_with_groq(raw_text)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume extraction failed: {str(exc)}"
        )