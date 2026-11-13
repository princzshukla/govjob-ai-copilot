import re
from datetime import date
from typing import Dict, List, Optional

from app.models.exam import ExamNotification
from app.schemas.candidate import CandidateProfileCreate
from app.schemas.exam import (
    EligibilityCheckResponse,
    ExamMatchResult,
    RuleExplanation,
)

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

_KNOWN_CATEGORIES = {"GENERAL", "EWS", "OBC", "OBC-NCL", "SC", "ST"}
_COMPLETED_GRADUATION_STATUSES = {
    "completed",
    "complete",
    "graduated",
    "passed",
    "done",
}
_FINAL_YEAR_GRADUATION_STATUSES = {
    "final year",
    "final year / appearing",
    "final year appearing",
    "final-year",
    "appearing",
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


def _format_age(dob: date, cutoff_date: date) -> str:
    """Human-readable completed age, e.g. ``24y 3m``, for rule explanations."""
    if dob > cutoff_date:
        return "not yet born at cutoff"

    years = cutoff_date.year - dob.year
    months = cutoff_date.month - dob.month
    if cutoff_date.day < dob.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return f"{years}y {months}m"


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


def _is_known_degree(degree: str) -> bool:
    return normalize_degree(degree) in DEGREE_RANK


def _rule(
    rule: str,
    candidate_value: str,
    required_value: str,
    status: str,
    message: str,
) -> RuleExplanation:
    return RuleExplanation(
        rule=rule,
        candidate_value=candidate_value,
        required_value=required_value,
        status=status,
        message=message,
    )


def check_single_exam_eligibility(
    candidate: CandidateProfileCreate,
    exam: ExamNotification,
    exam_topics_map: Dict[str, set],
    primary_exam_id: Optional[str] = None,
) -> ExamMatchResult:
    rules: List[RuleExplanation] = []

    # 1. Exact Age Verification on Exam's Cutoff Date
    candidate_age = calculate_exact_age(candidate.dob, exam.age_cutoff_date)
    relaxation = get_statutory_relaxation(candidate.category, candidate.is_pwd)
    max_allowed_age = exam.max_age_general + relaxation
    age_text = _format_age(candidate.dob, exam.age_cutoff_date)
    relaxation_note = (
        f", +{relaxation}y relaxation" if relaxation else ", no relaxation"
    )
    age_required = (
        f"{exam.min_age}y to {max_allowed_age}y on {exam.age_cutoff_date} "
        f"for {candidate.category}{relaxation_note}"
    )
    age_candidate = f"{age_text} (born {candidate.dob})"

    if candidate.dob > exam.age_cutoff_date:
        rules.append(
            _rule(
                "Age on cutoff date",
                age_candidate,
                age_required,
                "needs_check",
                (
                    f"Date of birth {candidate.dob} is after the age cutoff date "
                    f"{exam.age_cutoff_date}; age cannot be verified."
                ),
            )
        )
    elif candidate_age < exam.min_age:
        rules.append(
            _rule(
                "Age on cutoff date",
                age_candidate,
                age_required,
                "failed",
                (
                    f"Underage: {age_text} on {exam.age_cutoff_date} "
                    f"(Min required: {exam.min_age}y)"
                ),
            )
        )
    elif candidate_age > max_allowed_age:
        rules.append(
            _rule(
                "Age on cutoff date",
                age_candidate,
                age_required,
                "failed",
                (
                    f"Overage: {age_text} on {exam.age_cutoff_date} "
                    f"(Max allowed for {candidate.category}: {max_allowed_age}y)"
                ),
            )
        )
    else:
        rules.append(
            _rule(
                "Age on cutoff date",
                age_candidate,
                age_required,
                "passed",
                (
                    f"Age on cutoff date: {age_text}, limit {exam.min_age}y to "
                    f"{max_allowed_age}y for {candidate.category}."
                ),
            )
        )

    # 2. Category recognition (unknown categories silently had 0 relaxation before).
    category_known = candidate.category.upper().strip() in _KNOWN_CATEGORIES
    rules.append(
        _rule(
            "Category relaxation",
            candidate.category,
            "General, EWS, OBC, OBC-NCL, SC, ST",
            "passed" if category_known else "needs_check",
            (
                f"Category {candidate.category} recognized; statutory age "
                f"relaxation is {relaxation}y."
                if category_known
                else (
                    f"Category '{candidate.category}' is not recognized; verify the "
                    "reservation category and its age relaxation manually."
                )
            ),
        )
    )

    # 3. Degree & Education Level Hierarchy Verification
    allowed_degrees_text = ", ".join(str(d) for d in exam.allowed_degrees)
    degree_ok = any(
        degree_satisfies(allowed, candidate.highest_degree)
        for allowed in exam.allowed_degrees
    )
    candidate_degree_known = _is_known_degree(candidate.highest_degree)
    required_degrees_known = all(_is_known_degree(d) for d in exam.allowed_degrees)

    if degree_ok:
        rules.append(
            _rule(
                "Educational qualification",
                candidate.highest_degree,
                allowed_degrees_text,
                "passed",
                (
                    f"Degree: '{candidate.highest_degree}' satisfies required "
                    f"{exam.allowed_degrees}."
                ),
            )
        )
    elif not candidate_degree_known or not required_degrees_known:
        rules.append(
            _rule(
                "Educational qualification",
                candidate.highest_degree,
                allowed_degrees_text,
                "needs_check",
                (
                    f"Degree '{candidate.highest_degree}' is not recognized by the "
                    f"matcher; verify it manually against required "
                    f"{exam.allowed_degrees}."
                ),
            )
        )
    else:
        rules.append(
            _rule(
                "Educational qualification",
                candidate.highest_degree,
                allowed_degrees_text,
                "failed",
                (
                    f"Degree mismatch: '{candidate.highest_degree}' does not satisfy "
                    f"required {exam.allowed_degrees}"
                ),
            )
        )

    # 4. Graduation status / final-year policy
    graduation_status = _clean_text(candidate.graduation_status or "Completed")
    allows_final_year = getattr(exam, "allows_final_year", None)
    if graduation_status in _COMPLETED_GRADUATION_STATUSES:
        rules.append(
            _rule(
                "Graduation status",
                candidate.graduation_status,
                "Completed degree",
                "passed",
                (
                    f"Graduation status '{candidate.graduation_status}' meets the "
                    "completed-degree requirement."
                ),
            )
        )
    elif graduation_status in _FINAL_YEAR_GRADUATION_STATUSES:
        if allows_final_year is True:
            rules.append(
                _rule(
                    "Graduation status",
                    candidate.graduation_status,
                    "Final-year candidates allowed",
                    "passed",
                    (
                        "Final-year candidate accepted: notification allows "
                        "final-year/appearing candidates."
                    ),
                )
            )
        elif allows_final_year is False:
            rules.append(
                _rule(
                    "Graduation status",
                    candidate.graduation_status,
                    "Completed degree required",
                    "failed",
                    (
                        "Final-year candidate not accepted: notification requires a "
                        "completed degree."
                    ),
                )
            )
        else:
            rules.append(
                _rule(
                    "Graduation status",
                    candidate.graduation_status,
                    "Final-year policy not specified",
                    "needs_check",
                    (
                        "Final-year candidate: notification does not state whether "
                        "final-year/appearing candidates are allowed."
                    ),
                )
            )
    else:
        rules.append(
            _rule(
                "Graduation status",
                candidate.graduation_status,
                "Completed or Final Year / Appearing",
                "needs_check",
                (
                    f"Graduation status '{candidate.graduation_status}' is not "
                    "recognized; verify whether the candidate has completed the degree."
                ),
            )
        )

    # 5. Technical / Specialist Stream Verification
    if exam.allowed_streams and "Any" not in exam.allowed_streams:
        raw_stream = (candidate.stream or "").strip()
        allowed_streams_text = ", ".join(str(s) for s in exam.allowed_streams)
        if not raw_stream or raw_stream.lower() == "any":
            rules.append(
                _rule(
                    "Technical stream",
                    raw_stream or "(not provided)",
                    allowed_streams_text,
                    "failed",
                    f"Stream unspecified: requires one of {exam.allowed_streams}",
                )
            )
        else:
            norm_cand_stream = normalize_stream(raw_stream)
            stream_matched = any(
                normalize_stream(s) in norm_cand_stream
                or norm_cand_stream in normalize_stream(s)
                for s in exam.allowed_streams
            )
            if stream_matched:
                rules.append(
                    _rule(
                        "Technical stream",
                        raw_stream,
                        allowed_streams_text,
                        "passed",
                        (
                            f"Stream '{raw_stream}' matches allowed "
                            f"{exam.allowed_streams}."
                        ),
                    )
                )
            else:
                rules.append(
                    _rule(
                        "Technical stream",
                        raw_stream,
                        allowed_streams_text,
                        "failed",
                        (
                            f"Stream mismatch: Requires {exam.allowed_streams}, "
                            f"found '{raw_stream}'"
                        ),
                    )
                )

    # 6. Percentage / CGPA Threshold Check
    min_percentage = (
        float(exam.min_percentage) if exam.min_percentage is not None else 0.0
    )
    effective_pct = normalize_percentage(candidate.percentage_cgpa)
    raw_score = candidate.percentage_cgpa
    if raw_score is not None and 0 < float(raw_score) <= 10.0:
        percentage_candidate = (
            f"{effective_pct}% (from {raw_score} on a 10-point CGPA scale)"
        )
    else:
        percentage_candidate = f"{effective_pct}%"

    if min_percentage > 0:
        percentage_passed = effective_pct >= min_percentage
        rules.append(
            _rule(
                "Minimum percentage",
                percentage_candidate,
                f">= {min_percentage}%",
                "passed" if percentage_passed else "failed",
                (
                    f"Minimum marks required: {exam.min_percentage}%, "
                    f"found {effective_pct}%"
                ),
            )
        )
    else:
        rules.append(
            _rule(
                "Minimum percentage",
                percentage_candidate,
                "No minimum percentage",
                "passed",
                "No minimum percentage requirement for this notification.",
            )
        )

    # 7. State Domicile Check
    if exam.state_restriction:
        domicile_ok = (
            candidate.domicile_state.strip().lower()
            == exam.state_restriction.strip().lower()
        )
        rules.append(
            _rule(
                "State domicile",
                candidate.domicile_state,
                exam.state_restriction,
                "passed" if domicile_ok else "failed",
                (
                    f"Domicile {candidate.domicile_state} matches the restricted "
                    f"state {exam.state_restriction}."
                    if domicile_ok
                    else f"Domicile restricted to {exam.state_restriction}"
                ),
            )
        )
    else:
        rules.append(
            _rule(
                "State domicile",
                candidate.domicile_state,
                "Any Indian state (All India)",
                "passed",
                "No domicile restriction; the notification is open to all states.",
            )
        )

    # 8. Attempt limit
    previous_attempts = candidate.previous_attempts or 0
    max_attempts = getattr(exam, "max_attempts", None)
    if max_attempts is None:
        if previous_attempts == 0:
            rules.append(
                _rule(
                    "Attempt limit",
                    f"{previous_attempts} previous attempt(s)",
                    "No attempt limit recorded",
                    "passed",
                    (
                        "No attempt limit is recorded in the notification and the "
                        "candidate has no previous attempts."
                    ),
                )
            )
        else:
            rules.append(
                _rule(
                    "Attempt limit",
                    f"{previous_attempts} previous attempt(s)",
                    "Attempt limit not specified",
                    "needs_check",
                    (
                        "Notification does not state an attempt limit; verify "
                        f"{previous_attempts} previous attempt(s) manually."
                    ),
                )
            )
    elif previous_attempts < max_attempts:
        rules.append(
            _rule(
                "Attempt limit",
                f"{previous_attempts} previous attempt(s)",
                f"Fewer than {max_attempts} total attempts",
                "passed",
                (
                    f"Attempt {previous_attempts + 1} of {max_attempts} is within "
                    "the limit."
                ),
            )
        )
    else:
        rules.append(
            _rule(
                "Attempt limit",
                f"{previous_attempts} previous attempt(s)",
                f"Fewer than {max_attempts} total attempts",
                "failed",
                (
                    f"Attempt limit exceeded: {previous_attempts} previous "
                    f"attempt(s), max {max_attempts} total allowed."
                ),
            )
        )

    failed_rules = [r for r in rules if r.status == "failed"]
    needs_check_rules = [r for r in rules if r.status == "needs_check"]

    if failed_rules:
        verdict = "ineligible"
    elif needs_check_rules:
        verdict = "check_manually"
    else:
        verdict = "eligible"

    is_eligible = verdict == "eligible"
    is_last_attempt = is_eligible and (max_allowed_age - candidate_age <= 1)

    # Plan-B syllabus overlap
    overlap_pct = None
    if primary_exam_id and primary_exam_id in exam_topics_map and exam.id in exam_topics_map:
        base_topics = exam_topics_map[primary_exam_id]
        target_topics = exam_topics_map[exam.id]
        if target_topics:
            shared = base_topics.intersection(target_topics)
            overlap_pct = round((len(shared) / len(target_topics)) * 100, 1)

    source_url = getattr(exam, "source_url", None) or exam.official_pdf_url
    last_checked_at = getattr(exam, "last_checked_at", None) or date.today()

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
        reasons_failed=[r.message for r in failed_rules],
        syllabus_overlap_pct=overlap_pct,
        verdict=verdict,
        check_manually=verdict == "check_manually",
        rules=rules,
        source_url=source_url,
        last_checked_at=last_checked_at,
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
    check_manually: List[ExamMatchResult] = []

    for exam in exams:
        if not getattr(exam, "is_active", True):
            continue
        res = check_single_exam_eligibility(candidate, exam, exam_topics_map, primary_exam_id)
        if res.verdict == "eligible":
            eligible_now.append(res)
            if res.is_last_attempt_age:
                borderline.append(res)
        elif res.verdict == "check_manually":
            check_manually.append(res)
        else:
            ineligible.append(res)

    # Rank eligible exams by highest syllabus overlap first, then earliest deadline
    eligible_now.sort(
        key=lambda x: (-(x.syllabus_overlap_pct or 0.0), x.application_deadline)
    )
    borderline.sort(key=lambda x: x.application_deadline)
    check_manually.sort(key=lambda x: x.application_deadline)

    return EligibilityCheckResponse(
        candidate_name=candidate.full_name,
        eligible_now=eligible_now,
        borderline_last_chance=borderline,
        ineligible=ineligible,
        check_manually=check_manually,
    )
