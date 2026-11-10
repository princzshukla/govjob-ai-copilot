from typing import List, Dict, Any
from app.schemas.adaptive import MistakeReport, UserAnswerSubmission

def classify_mistakes(
    db_questions: list,
    user_submissions: List[UserAnswerSubmission],
    past_fails: int
) -> Dict[str, Any]:
    q_map = {q.id: q for q in db_questions}
    correct_count = 0
    total_time = 0
    diagnostics: List[MistakeReport] = []

    for sub in user_submissions:
        q = q_map.get(sub.question_id)
        if not q:
            continue

        total_time += sub.time_taken_sec
        q_data = q.question_data if isinstance(q.question_data, dict) else {}
        correct_opt = q_data.get("correct_option", "").strip().upper()
        selected_opt = sub.selected_option.strip().upper()

        if selected_opt == correct_opt:
            correct_count += 1
        else:
            expected_time = q_data.get("expected_time_sec", 45)
            is_repeated = past_fails > 0

            if sub.time_taken_sec < (expected_time * 0.4) and not is_repeated:
                mistake_type = "Calculation / Rush Error"
            elif sub.time_taken_sec > (expected_time * 1.5):
                mistake_type = "Conceptual Gap (Time Struggle)"
            elif is_repeated:
                mistake_type = "Recurring Conceptual Gap"
            else:
                mistake_type = "Application Slip"

            diagnostics.append(
                MistakeReport(
                    question_id=q.id,
                    topic=q.topic,
                    sub_topic=q.sub_topic or q.topic,
                    mistake_type=mistake_type,
                    is_repeated=is_repeated
                )
            )

    total_count = len(user_submissions)
    accuracy_pct = round((correct_count / total_count * 100), 1) if total_count > 0 else 0.0

    return {
        "total_count": total_count,
        "correct_count": correct_count,
        "accuracy_percentage": accuracy_pct,
        "total_time_sec": total_time,
        "diagnostics": diagnostics
    }