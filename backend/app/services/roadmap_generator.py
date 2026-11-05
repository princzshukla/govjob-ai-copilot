import json
from groq import AsyncGroq
from app.core.config import settings
from app.schemas.roadmap import StudyRoadmapResponse

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

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

    data = json.loads(chat_completion.choices[0].message.content)
    return StudyRoadmapResponse(**data)