# app/core/exam_patterns.py
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ExamPattern:
    option_count: int       # 4 for SSC/UPSC/RRB, 5 for Banking (IBPS/SBI)
    marks_correct: float    # e.g. 2.0 or 1.0
    negative_marks: float   # e.g. 0.50, 0.25, 0.66
    default_time_sec: int   # Baseline expected solve time per question


EXAM_PATTERNS: Dict[str, ExamPattern] = {
    # SSC Exams (4 options, +2.0, -0.50)
    "ssc-cgl-general": ExamPattern(4, 2.0, 0.50, 45),
    "ssc-chsl-12th": ExamPattern(4, 2.0, 0.50, 45),
    "ssc-mts-havaldar-10th": ExamPattern(4, 3.0, 1.00, 40),
    "ssc-gd-constable-10th": ExamPattern(4, 2.0, 0.25, 40),
    "delhi-police-constable-12th": ExamPattern(4, 1.0, 0.25, 40),

    # Banking Exams (5 options, +1.0, -0.25)
    "ibps-so-it-officer": ExamPattern(5, 1.0, 0.25, 45),
    "sbi-po-general": ExamPattern(5, 1.0, 0.25, 50),

    # Railways (4 options, +1.0, -0.33)
    "rrb-ntpc-grad": ExamPattern(4, 1.0, 0.33, 45),
    "rrb-ntpc-undergrad-12th": ExamPattern(4, 1.0, 0.33, 45),

    # UPSC & Defense (4 options, 1/3rd negative marking)
    "upsc-cse-ias": ExamPattern(4, 2.0, 0.66, 60),
    "nda-na-12th": ExamPattern(4, 2.5, 0.83, 55),
    "ib-acio-grade-ii": ExamPattern(4, 1.0, 0.25, 45),

    # Technical / Scientist (4 options)
    "nic-scientific-technical-asst": ExamPattern(4, 1.0, 0.25, 50),
    "drdo-scientist-b-cs": ExamPattern(4, 1.0, 0.25, 60),
}

DEFAULT_PATTERN = ExamPattern(option_count=4, marks_correct=2.0, negative_marks=0.50, default_time_sec=45)


def get_exam_pattern(exam_id: str) -> ExamPattern:
    return EXAM_PATTERNS.get(exam_id, DEFAULT_PATTERN)