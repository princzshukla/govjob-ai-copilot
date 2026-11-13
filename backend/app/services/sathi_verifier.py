# app/services/sathi_verifier.py
import ast
import math
import operator
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from app.core.exam_patterns import ExamPattern
from app.models.adaptive import QuestionBank

# Allowed safe math operations for verifying Quant/Reasoning answer keys
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_SAFE_FUNCS = {
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "gcd": math.gcd,
    "lcm": getattr(math, "lcm", lambda a, b: abs(a * b) // math.gcd(a, b)),
    "factorial": math.factorial,
}


def eval_safe_math(expr: str) -> Optional[float]:
    """Safely evaluates a numeric expression returned by the model to verify Quant/Reasoning keys."""
    if not expr or len(expr) > 200:
        return None

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
            return _SAFE_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
            return _SAFE_OPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = _SAFE_FUNCS.get(node.func.id)
            if fn:
                args = [_eval(a) for a in node.args]
                return float(fn(*args))
        raise ValueError("Unsupported AST node")

    try:
        tree = ast.parse(expr.strip(), mode="eval")
        return float(_eval(tree))
    except Exception:
        return None


def _extract_first_number(text: str) -> Optional[float]:
    cleaned = text.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    return float(m.group(0)) if m else None


def normalize_question_stem(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()


def is_near_duplicate(stem: str, existing_stems: List[str], threshold: float = 0.82) -> bool:
    norm_new = normalize_question_stem(stem)
    for old in existing_stems:
        norm_old = normalize_question_stem(old)
        if SequenceMatcher(None, norm_new, norm_old).ratio() >= threshold:
            return True
    return False


def is_current_affairs_expired(ca_month: Optional[str], max_age_months: int = 8) -> bool:
    """Retires Current Affairs questions older than max_age_months (format: 'YYYY-MM')."""
    if not ca_month:
        return False
    try:
        q_date = datetime.strptime(ca_month.strip()[:7], "%Y-%m")
        now = datetime.utcnow()
        months_diff = (now.year - q_date.year) * 12 + (now.month - q_date.month)
        return months_diff > max_age_months
    except ValueError:
        return False


def verify_question_candidate(
    raw_q: Dict[str, Any],
    pattern: ExamPattern,
    allowed_topics: Optional[set],
    existing_stems: List[str],
    topic: str,
    subject: str,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Runs Gate 1 (Pattern & Explanation), Gate 2 (Duplicate & Syllabus),
    and Gate 3 (Deterministic Math/Option Uniqueness).
    Returns (is_valid, rejection_reason, enriched_question_data).
    """
    stem = (raw_q.get("question") or "").strip()
    options = raw_q.get("options") or {}
    correct_opt = str(raw_q.get("correct_option") or "").strip().upper()
    explanation = (raw_q.get("explanation") or "").strip()
    shortcut = (raw_q.get("shortcut_method") or "").strip()
    why_wrong = raw_q.get("why_wrong") or {}

    # 1. Basic Completeness & Explanation Check
    if len(stem) < 15:
        return False, "Question stem too short", {}
    if not explanation and not shortcut:
        return False, "Missing teaching explanation", {}

    # 2. Exam Pattern Option Count Check (4 vs 5 options)
    expected_keys = [chr(65 + i) for i in range(pattern.option_count)]  # ['A','B','C','D'] or + 'E'
    if isinstance(options, list):
        if len(options) != pattern.option_count:
            return False, f"Expected {pattern.option_count} options, got {len(options)}", {}
        options = {chr(65 + i): str(v).strip() for i, v in enumerate(options)}
    elif isinstance(options, dict):
        options = {k.strip().upper(): str(v).strip() for k, v in options.items() if k.strip().upper() in expected_keys}
        if len(options) != pattern.option_count:
            return False, f"Expected options {expected_keys}, got {list(options.keys())}", {}

    if correct_opt not in expected_keys:
        return False, f"Invalid correct_option '{correct_opt}'", {}

    # 3. Reject Duplicate Options Inside the Same Question
    norm_opt_vals = [v.lower().strip() for v in options.values()]
    if len(set(norm_opt_vals)) != len(norm_opt_vals):
        return False, "Question has duplicate/identical option values", {}

    # 4. Reject Out-of-Syllabus Topic (if exam topics are restricted)
    if allowed_topics and topic not in allowed_topics:
        matched = any(t.lower() in topic.lower() or topic.lower() in t.lower() for t in allowed_topics)
        if not matched:
            return False, f"Topic '{topic}' is outside exam syllabus", {}

    # 5. Reject Near-Duplicates Against Question Bank
    if is_near_duplicate(stem, existing_stems):
        return False, "Near-duplicate of existing question", {}

    # 6. Deterministic Math Verification for Quant / Reasoning
    calc_expr = raw_q.get("verification_expr")
    is_quant = any(k in subject.lower() or k in topic.lower() for k in [
        "quant", "math", "algebra", "percentage", "ratio", "number", "interest",
        "geometry", "trigonometry", "profit", "time", "average", "mensuration", "data interpretation"
    ])
    if calc_expr:
        computed_val = eval_safe_math(str(calc_expr))
        if computed_val is None and is_quant:
            return False, "Invalid math verification expression", {}
        if computed_val is not None:
            correct_num = _extract_first_number(options[correct_opt])
            if correct_num is not None and abs(computed_val - correct_num) > 0.15:
                return False, f"Math mismatch: expr={computed_val} vs option {correct_opt}={correct_num}", {}
            # Ensure no OTHER option also evaluates to the same number
            matching_opts = [
                k for k, v in options.items()
                if _extract_first_number(v) is not None and abs(_extract_first_number(v) - computed_val) <= 0.05
            ]
            if len(matching_opts) > 1:
                return False, f"Ambiguous options {matching_opts} match computed answer", {}

    # 7. Build Rich Teaching Explanation String (Backward-compatible with existing UI)
    wrong_lines = []
    if isinstance(why_wrong, dict):
        for k, reason in why_wrong.items():
            if k.upper() != correct_opt and reason:
                wrong_lines.append(f"• Option {k.upper()}: {reason}")

    teaching_parts = []
    if shortcut:
        teaching_parts.append(f"⚡ Shortcut Method: {shortcut}")
    if explanation and explanation != shortcut:
        teaching_parts.append(f"Concept: {explanation}")
    if wrong_lines:
        teaching_parts.append("Why other options are wrong:\n" + "\n".join(wrong_lines))
    teaching_parts.append(f"📚 Roadmap Topic: {topic}")

    full_explanation = "\n\n".join(teaching_parts)

    origin_type = raw_q.get("origin_type", "PYQ_STYLE")
    enriched = {
        "question": stem,
        "options": options,
        "correct_option": correct_opt,
        "explanation": full_explanation,
        "shortcut_method": shortcut or explanation,
        "why_wrong": why_wrong if isinstance(why_wrong, dict) else {},
        "roadmap_topic_link": f"/roadmap?topic={topic}",
        "expected_time_sec": raw_q.get("expected_time_sec", pattern.default_time_sec),
        "origin_type": origin_type,
        "pyq_year": raw_q.get("pyq_year"),
        "source_title": raw_q.get("source_title"),
        "source_date": raw_q.get("source_date"),
        "ca_month": raw_q.get("ca_month"),
        "marks_correct": pattern.marks_correct,
        "negative_marks": pattern.negative_marks,
        "verification_badge": "Verified Real PYQ" if origin_type == "REAL_PYQ" else "Sathi AI Verified (PYQ-Style)",
    }
    return True, "OK", enriched


def update_question_telemetry(
    q_record: QuestionBank,
    is_correct: bool,
    time_taken_sec: int,
    reported: bool = False,
) -> None:
    """
    Updates per-question telemetry, calibrates difficulty from real student accuracy
    once attempts >= 20, and auto-retires broken/heavily-reported questions.
    """
    if reported:
        q_record.report_count = (q_record.report_count or 0) + 1

    prev_attempts = q_record.attempts_count or 0
    new_attempts = prev_attempts + 1
    q_record.attempts_count = new_attempts

    if is_correct:
        q_record.correct_count = (q_record.correct_count or 0) + 1

    # Rolling average solve time (clamped between 2s and 300s)
    clamped_time = max(2, min(int(time_taken_sec or 30), 300))
    prev_avg = q_record.avg_time_sec or 45.0
    q_record.avg_time_sec = round(((prev_avg * prev_attempts) + clamped_time) / new_attempts, 1)

    accuracy_ratio = (q_record.correct_count or 0) / new_attempts
    report_rate = (q_record.report_count or 0) / max(new_attempts, 1)

    # 1. Calibrate Difficulty from Real Data once attempts >= 20
    if new_attempts >= 20:
        if accuracy_ratio >= 0.75:
            calibrated = "Easy"
        elif accuracy_ratio >= 0.40:
            calibrated = "Medium"
        else:
            calibrated = "Hard"
        q_record.calibrated_difficulty = calibrated
        q_record.difficulty = calibrated

    # 2. Compute Quality Score (0.0 to 1.0)
    penalty = (q_record.report_count or 0) * 0.20
    if new_attempts >= 15 and (accuracy_ratio < 0.10 or accuracy_ratio > 0.98):
        penalty += 0.25  # Odd statistical distribution
    q_record.quality_score = round(max(0.0, 1.0 - penalty), 2)

    # 3. Auto-Retire Questions with High Reports or Broken Answer Keys
    if (q_record.report_count or 0) >= 3:
        q_record.is_retired = True
    elif new_attempts >= 10 and report_rate > 0.15:
        q_record.is_retired = True
    elif new_attempts >= 25 and accuracy_ratio < 0.10:
        q_record.is_retired = True
    elif is_current_affairs_expired(q_record.ca_month):
        q_record.is_retired = True