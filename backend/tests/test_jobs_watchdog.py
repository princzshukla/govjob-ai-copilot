"""Jobs Watchdog regression tests (offline: no DB, no network)."""
from __future__ import annotations

from datetime import date

from app.services import coverage_watchdog as cw
from app.services import jobs_report
from app.services import jobs_watchdog as jw


def _entry(title: str, url: str = "https://agg.example/1") -> cw.CoverageEntry:
    return cw.CoverageEntry(title=title, url=url, last_date="10 December 2026")


def test_strict_threshold_is_not_lowered():
    assert jw.JOBS_MATCH_THRESHOLD == 0.72
    assert cw.DEFAULT_MATCH_THRESHOLD == 0.55  # legacy path untouched
    assert cw.ADMIT_CARD_MATCH_THRESHOLD == 0.72


def test_one_seed_covers_at_most_one_entry():
    seeds = ["Alpha Recruitment Board Assistant 2026", "Beta Recruitment Board Clerk 2026"]
    entries = [
        _entry("Alpha Recruitment Board Assistant 2026 Online Form", "https://agg.example/a1"),
        _entry("Alpha Recruitment Board Assistant 2026 Online Form", "https://agg.example/a2"),
    ]
    report = jw.build_jobs_report(entries, seeds, today=date(2026, 1, 1))
    assert len(report.matched) == 1
    assert len(report.missing) == 1
    assert sum(len(v) for v in report.duplicate_matches.values()) == 1


def test_false_positive_different_organization_is_not_matched():
    seeds = ["SSC Combined Graduate Level (CGL)"]
    entries = [_entry("UPSC CGL 2026 Online Form")]
    report = jw.build_jobs_report(entries, seeds, today=date(2026, 1, 1))
    assert report.matched == []
    assert len(report.missing) == 1


def test_different_recruitment_year_lowers_the_score():
    seed = "SSC Combined Graduate Level (CGL) 2026"
    same = jw.job_signal_penalty("SSC Combined Graduate Level (CGL) 2026", seed)
    other = jw.job_signal_penalty("SSC Combined Graduate Level (CGL) 2025", seed)
    assert other < same
    assert other <= same - 0.3


def test_explicit_alias_resolves_to_the_curated_seed():
    alias_title = "SSC CHSL 2026 Online Form"
    seed_title = "SSC Combined Higher Secondary Level (CHSL)"
    assert cw.normalize_title(alias_title) in jw._JOB_TITLE_ALIASES
    report = jw.build_jobs_report([_entry(alias_title)], [seed_title], today=date(2026, 1, 1))
    assert len(report.matched) == 1
    assert report.matched[0][1] == seed_title
    assert report.matched[0][2] == 1.0


def test_qualification_and_category_signals_penalize_mismatch():
    related = jw.job_signal_penalty("SSC CHSL 12th pass 2026",
                                    "SSC Combined Higher Secondary Level (CHSL)")
    unrelated = jw.job_signal_penalty("AFMS Medical Officer MBBS 2026",
                                      "SSC Combined Higher Secondary Level (CHSL)")
    assert unrelated < related


def test_irrelevant_feed_items_are_filtered():
    assert not jw.is_job_entry(_entry("SSC CGL Answer Key 2026"))
    assert not jw.is_job_entry(_entry("SSC CGL Result 2026"))
    assert not jw.is_job_entry(_entry("SSC CGL Admit Card 2026"))
    assert not jw.is_job_entry(_entry("SSC CGL Exam City Details 2026"))


def test_classifications_are_explicit_and_exhaustive():
    analysis = {"organization": "ssc", "organization_candidates": ["ssc"]}
    verdict = {"reachable": True, "is_pdf": True, "document_matched": True}
    assert jw.classify_entry(_entry("SSC CGL 2026"), analysis=analysis,
                             verdict=verdict) == jw.CLASS_NEW
    assert jw.classify_entry(_entry("SSC CGL 2026"), analysis=analysis,
                             duplicate={"is_duplicate": True}) == jw.CLASS_DUPLICATE
    assert jw.classify_entry(_entry("SSC CGL 2026"), analysis=analysis,
                             ambiguous=True) == jw.CLASS_AMBIGUOUS
    assert jw.classify_entry(_entry("SSC CGL Result 2026"), analysis=analysis) == jw.CLASS_IRRELEVANT
    assert jw.classify_entry(_entry("Board Recruitment 2026"),
                             analysis={"organization": None, "organization_candidates": []}) == jw.CLASS_VERIFY


def test_official_pdf_field_extraction_and_null_preservation():
    text = (
        "OFFICIAL RECRUITMENT NOTIFICATION 2026\n"
        "Total Vacancies: 1,234\n"
        "Starting Date: 01.11.2026\n"
        "Last Date: 30 November 2026\n"
        "Age Limit: 18 to 27 years\n"
        "Educational Qualification: Bachelor's degree in any discipline.\n"
    )
    fields = jw.extract_job_fields(text)
    assert fields["application_start_date"] == "2026-11-01"
    assert fields["application_last_date"] == "2026-11-30"
    assert fields["total_vacancies"] == 1234
    assert fields["min_age"] == 18 and fields["age_max_general"] == 27
    assert "Bachelor" in fields["required_qualification"]
    assert fields["cancelled"] is False

    empty = jw.extract_job_fields("No dates stated in this notice.")
    assert empty["application_start_date"] is None
    assert empty["application_last_date"] is None
    assert empty["total_vacancies"] is None
    assert empty["required_qualification"] is None


def test_cancelled_and_revised_notices_are_detected():
    cancelled = jw.extract_job_fields("The recruitment is cancelled with immediate effect.")
    assert cancelled["cancelled"] is True
    revised = jw.extract_job_fields("Corrigendum: the schedule is revised.")
    assert revised["revised"] is True


def test_candidature_wording_does_not_count_as_recruitment_cancellation():
    # Real apprenticeship notices contain these sentences; they must not
    # deactivate the notification (see RRC/ISRO/UP Anganwadi false positives).
    text = (
        "The candidature of such applicants will be cancelled. "
        "Candidates who have withdrawn from the Apprenticeship Training are not eligible. "
        "Application withdrawal is allowed before the last date."
    )
    assert jw.extract_job_fields(text)["cancelled"] is False


def test_report_never_claims_a_misleading_clean_coverage():
    text = jobs_report.format_jobs_report({
        "coverage_pct": 100.0, "total_live": 10, "total_seeds": 20,
        "distinct_matched_seeds": 10, "unmatched": 1, "duplicate_candidates": 2,
        "ambiguous": 1, "newly_discovered": 0, "official_pdfs_verified": 0,
        "awaiting_review": 1, "deadlines_approaching": 3, "honest": False,
        "coverage_note": "1 unmatched, 1 ambiguous and 2 duplicate candidates are excluded",
    })
    assert "100.0%" in text
    assert "honest: False" in text
    assert "unmatched: 1" in text
    assert "duplicate candidates: 2" in text


def test_lock_is_released_and_can_be_reacquired():
    handle = jw.try_acquire_lock()
    if handle is None:
        return  # a real scheduled worker holds it; nothing to assert here
    jw.release_lock(handle)
    again = jw.try_acquire_lock()
    assert again is not None
    jw.release_lock(again)
