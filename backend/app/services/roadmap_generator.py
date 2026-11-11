import json
import logging

from groq import AsyncGroq

from app.core.config import settings
from app.schemas.roadmap import StudyRoadmapResponse

logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

DEFAULT_REVISION_STRATEGY = (
    "Reserve the final 20% of the schedule for full-length mock tests and error analysis. "
    "Maintain a mistake log and review it every week."
)


async def generate_study_roadmap_groq(
    exam_title: str,
    syllabus_topics: list[str],
    target_weeks: int
) -> StudyRoadmapResponse:

    system_prompt = f"""
    You are a premier civil service and government competitive exam strategist.
    Generate a rigorous, week-by-week study roadmap in valid JSON matching this schema:
    {json.dumps(StudyRoadmapResponse.model_json_schema(), indent=2)}

    REQUIREMENTS:
    - Target: {exam_title}
    - Total Duration: {target_weeks} weeks
    - Topics to distribute: {', '.join(syllabus_topics)}
    - Reserve the final 20% of the weeks strictly for full-length mocks and error analysis.
    - Output ONLY JSON.
    """

    chat_completion = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a {target_weeks}-week roadmap for {exam_title}."}
        ],
        model=settings.GROQ_MODEL,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = chat_completion.choices[0].message.content or "{}"

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.error("Groq returned invalid JSON for roadmap: %s", raw_content[:500])
        raise ValueError("The AI model returned an unreadable roadmap. Please try again.") from exc

    if not isinstance(data, dict):
        raise ValueError("The AI model returned an unexpected roadmap format.")

    # The model occasionally omits required keys (notably `revision_strategy`),
    # which used to turn into an HTTP 500. Fill safe defaults instead.
    data.setdefault("exam_name", exam_title)
    data.setdefault("total_duration_weeks", target_weeks)
    data.setdefault("revision_strategy", DEFAULT_REVISION_STRATEGY)
    data.setdefault("weekly_breakdown", [])

    return StudyRoadmapResponse(**data)
