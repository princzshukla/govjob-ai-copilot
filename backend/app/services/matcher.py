from datetime import date
from typing import List, Dict, Optional
from app.schemas.candidate import CandidateProfileCreate
from app.schemas.exam import ExamMatchResult, EligibilityCheckResponse
from app.models.exam import ExamNotification

# Degree Normalization Equivalency Map
DEGREE_EQUIVALENTS = {
    "Any Graduate": ["B.Tech", "BE", "BCA", "B.Sc", "B.Com", "BA", "BBA", "MCA", "M.Tech", "M.Sc", "MBA"],
    "Engineering/IT Graduate": ["B.Tech", "BE", "BCA", "MCA", "M.Tech", "M.Sc"]
}

def calculate_exact_age(dob: date, cutoff_date: date) -> int:
    """Calculates completed years of age as on the statutory cutoff date."""
    return cutoff_date.year - dob.year - (
        (cutoff_date.month, cutoff_date.day) < (dob.month, dob.day)
    )

def get_statutory_relaxation(category: str, is_pwd: bool) -> int:
    """Returns statutory upper-age relaxation in years per Government of India norms."""
    cat = category.upper().strip()
    relaxation = 0
    if cat in ["SC", "ST"]:
        relaxation = 5
    elif cat in ["OBC", "OBC-NCL"]:
        relaxation = 3
    
    if is_pwd:
        relaxation += 10  # PwBD adds 10 yrs (total 10 Gen, 13 OBC, 15 SC/ST)
    return relaxation

def check_single_exam_eligibility(
    candidate: CandidateProfileCreate,
    exam: ExamNotification,
    exam_topics_map: Dict[str, set],
    primary_exam_id: Optional[str] = None
) -> ExamMatchResult:
    reasons_failed = []

    # 1. Exact Age Verification on Exam's Cutoff Date
    candidate_age = calculate_exact_age(candidate.dob, exam.age_cutoff_date)
    relaxation = get_statutory_relaxation(candidate.category, candidate.is_pwd)
    max_allowed_age = exam.max_age_general + relaxation

    if candidate_age < exam.min_age:
        reasons_failed.append(
            f"Underage: {candidate_age} yrs on {exam.age_cutoff_date} (Min required: {exam.min_age})"
        )
    elif candidate_age > max_allowed_age:
        reasons_failed.append(
            f"Overage: {candidate_age} yrs on {exam.age_cutoff_date} (Max allowed for {candidate.category}: {max_allowed_age})"
        )

    # 2. Degree Equivalence Verification
    cand_degree = candidate.highest_degree.strip()
    degree_matched = False
    for allowed in exam.allowed_degrees:
        if allowed in DEGREE_EQUIVALENTS and cand_degree in DEGREE_EQUIVALENTS[allowed]:
            degree_matched = True
            break
        if cand_degree.lower() == allowed.lower():
            degree_matched = True
            break

    if not degree_matched:
        reasons_failed.append(
            f"Degree mismatch: '{cand_degree}' not in required {exam.allowed_degrees}"
        )

    # 3. Technical / Specialist Stream Verification
    if exam.allowed_streams and "Any" not in exam.allowed_streams:
        cand_stream = (candidate.stream or "").strip()
        stream_matched = any(
            s.lower() in cand_stream.lower() or cand_stream.lower() in s.lower()
            for s in exam.allowed_streams
        )
        if not stream_matched:
            reasons_failed.append(
                f"Stream mismatch: Requires {exam.allowed_streams}, found '{cand_stream or 'Unspecified'}'"
            )

    # 4. Percentage Threshold Check
    if exam.min_percentage and candidate.percentage_cgpa:
        if float(candidate.percentage_cgpa) < float(exam.min_percentage):
            reasons_failed.append(
                f"Minimum marks required: {exam.min_percentage}%, found {candidate.percentage_cgpa}%"
            )

    # 5. State Domicile Check
    if exam.state_restriction:
        if candidate.domicile_state.strip().lower() != exam.state_restriction.strip().lower():
            reasons_failed.append(f"Domicile restricted to {exam.state_restriction}")

    is_eligible = len(reasons_failed) == 0
    is_last_attempt = is_eligible and (max_allowed_age - candidate_age <= 1)

    # 6. Calculate Syllabus Overlap Percentage (if a target exam is specified)
    overlap_pct = None
    if primary_exam_id and primary_exam_id in exam_topics_map and exam.id in exam_topics_map:
        base_topics = exam_topics_map[primary_exam_id]
        target_topics = exam_topics_map[exam.id]
        if target_topics:
            shared = base_topics.intersection(target_topics)
            overlap_pct = round((len(shared) / len(target_topics)) * 100, 1)

    return ExamMatchResult(
        exam_id=exam.id,
        title=exam.title,
        organizing_body=exam.organizing_body,
        post_type=exam.post_type,
        application_deadline=exam.application_deadline,
        exam_date=exam.exam_date,
        official_pdf_url=exam.official_pdf_url,
        is_eligible=is_eligible,
        candidate_age_at_cutoff=candidate_age,
        max_allowed_age=max_allowed_age,
        is_last_attempt_age=is_last_attempt,
        reasons_failed=reasons_failed,
        syllabus_overlap_pct=overlap_pct
    )

def evaluate_all_exams(
    candidate: CandidateProfileCreate,
    exams: List[ExamNotification],
    exam_topics_map: Dict[str, set],
    primary_exam_id: Optional[str] = None
) -> EligibilityCheckResponse:
    eligible_now = []
    borderline = []
    ineligible = []

    for exam in exams:
        res = check_single_exam_eligibility(candidate, exam, exam_topics_map, primary_exam_id)
        if res.is_eligible:
            eligible_now.append(res)
            if res.is_last_attempt_age:
                borderline.append(res)
        else:
            ineligible.append(res)

    return EligibilityCheckResponse(
        candidate_name=candidate.full_name,
        eligible_now=eligible_now,
        borderline_last_chance=borderline,
        ineligible=ineligible
    )