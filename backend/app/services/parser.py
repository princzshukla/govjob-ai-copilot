# app/services/parser.py
import json
import logging
from datetime import date

import pymupdf  # PyMuPDF
from groq import AsyncGroq
from app.core.config import settings
from app.schemas.candidate import (
    ParsedResumeProfile,
    MissingFieldPrompt,
    ResumeParseResponse
)

logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

# Statutory fields required for accurate Government Exam matching
REQUIRED_GOV_FIELDS = {
    "dob": {
        "label": "Date of Birth",
        "question": "What is your exact Date of Birth? (Required to calculate age cutoffs as on notification dates)",
        "input_type": "date",
        "options": None
    },
    "category": {
        "label": "Reservation Category",
        "question": "Which reservation category do you belong to? (Used for upper-age relaxation & cutoff calculation)",
        "input_type": "select",
        "options": ["General", "OBC-NCL", "EWS", "SC", "ST"]
    },
    "domicile_state": {
        "label": "Domicile State",
        "question": "Which Indian State/UT is your permanent domicile?",
        "input_type": "select",
        "options": [
            "Delhi", "Uttar Pradesh", "Maharashtra", "Bihar", "Rajasthan",
            "Madhya Pradesh", "Haryana", "Karnataka", "Tamil Nadu", "West Bengal", "Other"
        ]
    },
    "highest_degree": {
        "label": "Highest Qualification",
        "question": "What is your highest educational degree?",
        "input_type": "select",
        "options": ["B.Tech", "BE", "BCA", "MCA", "B.Sc", "M.Sc", "B.Com", "BA", "BBA", "MBA", "Diploma", "12th"]
    },
    "stream": {
        "label": "Specialization / Stream",
        "question": "What was your main stream or branch in graduation? (Crucial for Specialist/Technical posts)",
        "input_type": "select",
        "options": [
            "Computer Science", "Information Technology", "Computer Applications",
            "Electronics", "Mechanical", "Civil", "Electrical", "Commerce", "Arts", "Science (PCM/PCB)", "General"
        ]
    },
    "percentage_cgpa": {
        "label": "Graduation Percentage (%)",
        "question": "What is your aggregate graduation percentage? (If CGPA, multiply by 9.5—needed for PSUs/NIC/RBI 60% criteria)",
        "input_type": "number",
        "options": None
    },
    "is_pwd": {
        "label": "PwBD (Person with Benchmark Disability)",
        "question": "Are you eligible for PwBD relaxation (40% or more disability)?",
        "input_type": "select",
        "options": ["No", "Yes"]
    }
}

def extract_raw_text_from_pdf(pdf_bytes: bytes) -> str:
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n".join([page.get_text() for page in doc])

def inspect_missing_gov_fields(profile: ParsedResumeProfile) -> list[MissingFieldPrompt]:
    missing: list[MissingFieldPrompt] = []
    profile_dict = profile.model_dump()

    for field_key, meta in REQUIRED_GOV_FIELDS.items():
        val = profile_dict.get(field_key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(
                MissingFieldPrompt(
                    field_name=field_key,
                    label=meta["label"],
                    question=meta["question"],
                    input_type=meta["input_type"],
                    options=meta["options"]
                )
            )
    return missing

async def parse_resume_with_groq(raw_text: str) -> ResumeParseResponse:
    system_prompt = f"""
    You are an expert government job resume parser.
    Extract ONLY the details explicitly written in the resume text and return valid JSON matching this schema:
    {json.dumps(ParsedResumeProfile.model_json_schema(), indent=2)}

    STRICT RULES:
    1. DO NOT guess or invent values. If a field (like 'dob', 'category', 'is_pwd', or 'percentage_cgpa') is NOT explicitly stated in the resume, you MUST set it to null.
    2. If CGPA is mentioned (e.g. 8.2 CGPA) instead of percentage, convert it to percentage (CGPA * 9.5 = 77.9) and store as a float in 'percentage_cgpa'.
    3. Standardize 'highest_degree' to one of: 'B.Tech', 'BE', 'BCA', 'MCA', 'B.Sc', 'M.Sc', 'B.Com', 'BA', 'Diploma', '12th' if found.
    4. Return ONLY valid JSON.
    """

    chat_completion = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Resume Text:\n{raw_text[:5000]}"}
        ],
        model=settings.GROQ_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    parsed_dict = json.loads(chat_completion.choices[0].message.content or "{}")

    # A malformed date from the model would otherwise fail the whole upload.
    dob_value = parsed_dict.get("dob")
    if dob_value:
        try:
            date.fromisoformat(str(dob_value))
        except ValueError:
            logger.warning("Discarding unparseable resume DOB")
            parsed_dict["dob"] = None

    extracted_profile = ParsedResumeProfile(**parsed_dict)

    # Inspect the fields BEFORE defaulting is_pwd, otherwise the PwBD question
    # can never be reported as missing.
    missing_prompts = inspect_missing_gov_fields(extracted_profile)

    if extracted_profile.is_pwd is None:
        extracted_profile.is_pwd = False

    is_complete = len(missing_prompts) == 0

    if is_complete:
        msg = "All government job eligibility parameters were found in your resume!"
    else:
        missing_labels = ", ".join([m.label for m in missing_prompts])
        msg = f"Resume parsed! Please provide {len(missing_prompts)} missing detail(s) required for government exams: {missing_labels}."

    return ResumeParseResponse(
        extracted_profile=extracted_profile,
        is_complete_for_gov_jobs=is_complete,
        missing_fields=missing_prompts,
        message=msg
    )