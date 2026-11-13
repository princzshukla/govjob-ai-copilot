import json
import httpx
from bs4 import BeautifulSoup
from datetime import date
from groq import AsyncGroq
from app.core.config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

async def fetch_raw_job_listings() -> list[dict]:
    url = "https://www.freejobalert.com/latest-notifications/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http_client:
        resp = await http_client.get(url, headers=headers)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    raw_jobs = []

    for row in soup.select("table tr")[:12]:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        link_tag = row.find("a", href=True)
        if len(cols) >= 4 and link_tag:
            raw_jobs.append({
                "raw_text": " | ".join(cols),
                "link": link_tag["href"]
            })

    return raw_jobs

async def structure_jobs_with_groq(raw_jobs: list[dict]) -> list[dict]:
    if not raw_jobs:
        return []

    prompt = f"""
    Convert these raw Indian government job notifications into a JSON object with a key "exams" containing a list of structured job objects.
    Today's date is {date.today().isoformat()}.

    Each object inside "exams" MUST have these exact keys:
    - "id": slugified unique string (e.g., "sbi-clerk-2026")
    - "title": string (Post/Exam name)
    - "organizing_body": string (Board/Ministry name)
    - "post_type": string ("General Graduate", "Technical / Specialist", "Banking / Finance", or "Defense")
    - "application_deadline": "YYYY-MM-DD" (estimate 25 days from today)
    - "exam_date": "YYYY-MM-DD" or null
    - "official_pdf_url": string (use the provided link)
    - "source_url": string (use the provided link; never leave empty)
    - "last_checked_at": "YYYY-MM-DD" (today's date)
    - "min_age": integer (usually 18 or 21)
    - "max_age_general": integer (usually 27, 30, or 32)
    - "age_cutoff_date": "YYYY-MM-DD" (use today's date)
    - "allowed_degrees": list of strings (e.g., ["Any Graduate"] or ["B.Tech", "BE", "BCA", "MCA"])
    - "allowed_streams": list of strings (e.g., ["Any"] or ["Computer Science", "Information Technology"])
    - "min_percentage": float (default 0.0)
    - "state_restriction": string or null
    - "allows_final_year": true, false, or null (null if the notification does not say)
    - "max_attempts": integer or null (null if the notification does not say)
    - "topics": list of 6-10 standard syllabus topics for this exam

    Raw Scraped Data:
    {json.dumps(raw_jobs[:12], indent=2)}
    """

    chat_completion = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You output only valid JSON objects."},
            {"role": "user", "content": prompt}
        ],
        model=settings.GROQ_MODEL,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    parsed = json.loads(chat_completion.choices[0].message.content or "{}")
    exams = parsed.get("exams", [])
    return exams if isinstance(exams, list) else []