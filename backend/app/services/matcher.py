import re
from datetime import date
from typing import Dict, List, Optional
from app.models.exam import ExamNotification
from app.schemas.candidate import CandidateProfileCreate
from app.schemas.exam import EligibilityCheckResponse, ExamMatchResult

DEGREE_RANK = {
    "10th": 1,
    "12th": 2,
    "Diploma": 2,
    "B.Tech": 3,
    "BE": 3,
    "BCA": 3,
    "B.Sc": 3,
    "B.Com": 3,
    "BA": 3,
    "BBA": 3,
    "Any Graduate": 3,
    "MCA": 4,
    "M.Tech": 4,
    "M.E": 4,
    "M.Sc": 4,
    "MBA": 4,
}

_DEGREE_ALIASES = {
    "10th": "10th",
    "10th pass": "10th",
    "matric": "10th",
    "matriculation": "10th",
    "high school": "10th",
    "12th": "12th",
    "12th pass": "12th",
    "intermediate": "12th",
    "senior secondary": "12th",
    "hsc": "12th",
    "plus two": "12th",
    "diploma": "Diploma",
    "polytechnic diploma": "Diploma",
    "btech": "B.Tech",
    "b.tech": "B.Tech",
    "bachelor of technology": "B.Tech",
    "be": "BE",
    "b.e": "BE",
    "b.e.": "BE",
    "bachelor of engineering": "BE",
    "bca": "BCA",
    "bachelor of computer applications": "BCA",
    "bsc": "B.Sc",
    "b.sc": "B.Sc",
    "bachelor of science": "B.Sc",
    "bcom": "B.Com",
    "b.com": "B.Com",
    "bachelor of commerce": "B.Com",
    "ba": "BA",
    "b.a": "BA",
    "b.a.": "BA",
    "bachelor of arts": "BA",
    "bba": "BBA",
    "bachelor of business administration": "BBA",
    "mca": "MCA",
    "master of computer applications": "MCA",
    "mtech": "M.Tech",
    "m.tech": "M.Tech",
    "master of technology": "M.Tech",
    "me": "M.E",
    "m.e": "M.E",
    "m.e.": "M.E",
    "msc": "M.Sc",
    "m.sc": "M.Sc",
    "master of science": "M.Sc",
    "mba": "MBA",
    "master of business administration": "MBA",
    "any graduate": "Any Graduate",
    "graduate": "Any Graduate",
    "graduation": "Any Graduate",
    "post graduate": "Any Graduate",
    "postgraduate": "Any Graduate",
}

_DEGREE_GROUPS = [
    {"B.Tech", "BE"},
    {"M.Tech", "M.E"},
]

_STREAM_ALIASES = {
    "cs": "computer science",
    "cse": "computer science",
    "computer science & engineering": "computer science",
    "computer science and engineering": "computer science",
    "computer applications": "computer science",
    "it": "information technology",
    "ece": "electronics and communication",
    "eee": "electrical and electronics",
    "ee": "electrical",
    "me": "mechanical",
    "ce": "civil",
}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_degree(degree_str: str) -> str:
    key = _clean_text(degree_str)
    if key in _DEGREE_ALIASES:
        return _DEGREE_ALIASES[key]

    for alias, canonical in _DEGREE_ALIASES.items():
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", key):
            return canonical

    return degree_str.strip()


def normalize_stream(stream_str: str) -> str:
    key = _clean_text(stream_str)
    return _STREAM_ALIASES.get(key, key)


def normalize_percentage(score: Optional[float]) -> float:
    """Converts 10-point CGPA (<= 10.0) to approximate percentage (CBSE/UGC 9.5x)."""
    if score is None:
        return 0.0
    val = float(score)
    if 0 < val <= 10.0:
        return round(val * 9.5, 2)
    return val


def _degrees_equivalent(candidate_degree: str, required_degree: str) -> bool:
    if candidate_degree.lower() == required_degree.lower():
        return True
    for group in _DEGREE_GROUPS:
        if candidate_degree in group and required_degree in group:
            return True
    return False


def degree_satisfies(required_degree: str, candidate_degree: str) -> bool:
    required = normalize_degree(required_degree)
    candidate = normalize_degree(candidate_degree)

    if required in ("10th", "12th"):
        return DEGREE_RANK.get(candidate, 1) >= DEGREE_RANK.get(required, 1)
    if required == "Any Graduate":
        return DEGREE_RANK.get(candidate, 1) >= 3
    return _degrees_equivalent(candidate, required)


def calculate_exact_age(dob: date, cutoff_date: date) -> int:
    return cutoff_date.year - dob.year - (
        (cutoff_date.month, cutoff_date.day) < (dob.month, dob.day)
    )


def get_statutory_relaxation(category: str, is_pwd: bool) -> int:
    cat = category.upper().strip()
    relaxation = 0
    if cat in ["SC", "ST"]:
        relaxation = 5
    elif cat in ["OBC", "OBC-NCL"]:
        relaxation = 3

    if is_pwd:
        relaxation += 10  # PwBD adds 10 yrs (total 10 Gen/EWS, 13 OBC, 15 SC/ST)
    return relaxation


def check_single_exam_eligibility(
    candidate: CandidateProfileCreate,
    exam: ExamNotification,
    exam_topics_map: Dict[str, set],
    primary_exam_id: Optional[str] = None,
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

    # 2. Degree & Education Level Hierarchy Verification
    if not any(degree_satisfies(allowed, candidate.highest_degree) for allowed in exam.allowed_degrees):
        reasons_failed.append(
            f"Degree mismatch: '{candidate.highest_degree}' does not satisfy required {exam.allowed_degrees}"
        )

    # 3. Technical / Specialist Stream Verification
    if exam.allowed_streams and "Any" not in exam.allowed_streams:
        raw_stream = (candidate.stream or "").strip()
        if not raw_stream or raw_stream.lower() == "any":
            reasons_failed.append(
                f"Stream unspecified: requires one of {exam.allowed_streams}"
            )
        else:
            norm_cand_stream = normalize_stream(raw_stream)
            stream_matched = any(
                normalize_stream(s) in norm_cand_stream or norm_cand_stream in normalize_stream(s)
                for s in exam.allowed_streams
            )
            if not stream_matched:
                reasons_failed.append(
                    f"Stream mismatch: Requires {exam.allowed_streams}, found '{raw_stream}'"
                )

    # 4. Percentage / CGPA Threshold Check
    if exam.min_percentage and float(exam.min_percentage) > 0:
        effective_pct = normalize_percentage(candidate.percentage_cgpa)
        if effective_pct < float(exam.min_percentage):
            reasons_failed.append(
                f"Minimum marks required: {exam.min_percentage}%, found {effective_pct}%"
            )

    # 5. State Domicile Check
    if exam.state_restriction:
        if candidate.domicile_state.strip().lower() != exam.state_restriction.strip().lower():
            reasons_failed.append(f"Domicile restricted to {exam.state_restriction}")

    is_eligible = len(reasons_failed) == 0
    is_last_attempt = is_eligible and (max_allowed_age - candidate_age <= 1)

    # 6. Calculate Syllabus Overlap Percentage
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
        syllabus_overlap_pct=overlap_pct,
    )


def evaluate_all_exams(
    candidate: CandidateProfileCreate,
    exams: List[ExamNotification],
    exam_topics_map: Dict[str, set],
    primary_exam_id: Optional[str] = None,
) -> EligibilityCheckResponse:
    eligible_now: List[ExamMatchResult] = []
    borderline: List[ExamMatchResult] = []
    ineligible: List[ExamMatchResult] = []

    for exam in exams:
        if not getattr(exam, "is_active", True):
            continue
        res = check_single_exam_eligibility(candidate, exam, exam_topics_map, primary_exam_id)
        if res.is_eligible:
            eligible_now.append(res)
            if res.is_last_attempt_age:
                borderline.append(res)
        else:
            ineligible.append(res)

    # Rank eligible exams by highest syllabus overlap first, then earliest deadline
    eligible_now.sort(
        key=lambda x: (-(x.syllabus_overlap_pct or 0.0), x.application_deadline)
    )
    borderline.sort(key=lambda x: x.application_deadline)

    return EligibilityCheckResponse(
        candidate_name=candidate.full_name,
        eligible_now=eligible_now,
        borderline_last_chance=borderline,
        ineligible=ineligible,
    )