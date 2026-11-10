import uuid
from typing import List, Dict, Any
from app.schemas.adaptive import MistakeReport

def apply_micro_adjustments(
    diagnostics: List[MistakeReport],
    overall_accuracy: float
) -> Dict[str, Any]:
    added_tasks = []
    seen_subtopics = set()

    for diag in diagnostics:
        if diag.sub_topic in seen_subtopics:
            continue
        seen_subtopics.add(diag.sub_topic)

        # Isolated error with strong overall score -> lightweight 3-Q booster
        if overall_accuracy >= 70.0 and not diag.is_repeated:
            added_tasks.append({
                "task_id": f"boost_{uuid.uuid4().hex[:6]}",
                "parent_topic": diag.topic,
                "sub_topic": diag.sub_topic,
                "task_type": "micro_booster",
                "question_count": 3,
                "reason": f"1 isolated error in {diag.sub_topic} ({diag.mistake_type})"
            })
        elif diag.is_repeated:
            added_tasks.append({
                "task_id": f"rev_{uuid.uuid4().hex[:6]}",
                "parent_topic": diag.topic,
                "sub_topic": diag.sub_topic,
                "task_type": "weekend_revision",
                "question_count": 5,
                "reason": f"Recurring mistake in {diag.sub_topic}"
            })

    return {
        "added_micro_tasks": added_tasks,
        "roadmap_structure_changed": False  # Keeps base timetable intact
    }