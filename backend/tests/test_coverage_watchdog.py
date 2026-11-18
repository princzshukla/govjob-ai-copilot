"""Coverage watchdog — parser and matcher unit tests (no network)."""
from __future__ import annotations

from app.services.coverage_watchdog import (
    CoverageEntry,
    build_report,
    match_score,
    normalize_title,
    parse_latest_jobs,
)

SAMPLE_HTML = """
<div class="entry-content">
<h2>All Latest Jobs</h2>
<ul class="latest-posts-last-date"><li><a href="https://example.com/a1/" target="_blank" rel="noopener">Assam Rifles Technical / Tradesman Online Form 2026</a> – Last Date: 14 December 2026</li><li><a href="https://example.com/a2/" target="_blank" rel="noopener">UPSSSC Inter (12th) Level Online Form 2026</a> – Last Date: 01 December 2026</li><li><a href="https://example.com/a3/" target="_blank" rel="noopener">RSSB Support Engineer Online Form 2025 (1050 Posts)</a> – Last Date: Available Soon</li><li><a href="https://example.com/a4/" target="_blank" rel="noopener">Some Notice With No Date At All Here 2026</a></li></ul>
</div>
"""


def test_parse_latest_jobs_extracts_entries_and_dates():
    entries = parse_latest_jobs(SAMPLE_HTML)
    assert [e.title for e in entries] == [
        "Assam Rifles Technical / Tradesman Online Form 2026",
        "UPSSSC Inter (12th) Level Online Form 2026",
        "RSSB Support Engineer Online Form 2025 (1050 Posts)",
        "Some Notice With No Date At All Here 2026",
    ]
    assert entries[0].url == "https://example.com/a1/"
    assert entries[0].last_date == "14 December 2026"
    assert entries[2].last_date == "Available Soon"
    assert entries[3].last_date is None


def test_parse_latest_jobs_html_entities_and_en_dash():
    html = "<ul class=\"latest-posts-last-date\"><li><a href=\"https://example.com/x\">M&amp;H Semi Conductor SCL Various Post Online Form 2026</a> \u2013 Last Date: 30 November 2026</li></ul>"
    entries = parse_latest_jobs(html)
    assert entries[0].title == "M&H Semi Conductor SCL Various Post Online Form 2026"
    assert entries[0].last_date == "30 November 2026"


def test_parse_without_wrapper_falls_back_to_document():
    entries = parse_latest_jobs(
        "<ul><li><a href=\"https://example.com/y\">Some Railway Apprentice Online Form 2026</a> – Last Date: 25 November 2026</li></ul>"
    )
    assert len(entries) == 1
    assert entries[0].last_date == "25 November 2026"


def test_normalize_title_strips_punctuation_and_case():
    assert normalize_title("UPESSC UP TGT Online Form 2026 (17,735 Posts)") == "upessc up tgt online form 2026 17 735 posts"


def test_match_score_prefers_token_overlap():
    a = normalize_title("UPESSC UP TGT Online Form 2026 (17,735 Posts)")
    b = normalize_title("UPESSC Assistant Teacher (TGT) 2026 — 17,735 posts")
    assert match_score(a, b) > 0.55
    assert match_score(a, normalize_title("DRDO Scientist B Computer Science 2026")) < 0.55


def test_build_report_splits_matched_and_missing():
    entries = [
        CoverageEntry("Assam Rifles Technical / Tradesman Online Form 2026", "https://x/1", "14 December 2026"),
        CoverageEntry("Totally Obscure Board Recruitment 2099", "https://x/2", "01 January 2099"),
    ]
    seed = ["Assam Rifles Technical & Tradesman Recruitment Rally 2026 — 354 posts"]
    report = build_report(entries, seed)
    assert len(report.matched) == 1
    assert report.matched[0][0].url == "https://x/1"
    assert [e.url for e in report.missing] == ["https://x/2"]
    assert report.seed_count == 1
    assert report.coverage_pct == 50.0


def test_parse_last_date_formats():
    from datetime import date

    from app.services.coverage_watchdog import parse_last_date

    assert parse_last_date("06 December 2026") == date(2026, 12, 6)
    assert parse_last_date("Available Soon") is None
    assert parse_last_date("NA") is None
    assert parse_last_date(None) is None
    assert parse_last_date("Last Date : 22 November 2026") == date(2026, 11, 22)


def test_actionable_filter_drops_stale_entries():
    from datetime import date

    from app.services.coverage_watchdog import is_actionable

    today = date(2026, 11, 17)
    live = CoverageEntry("Some Live Recruitment Online Form 2026", "https://x/1", "26 November 2026")
    stale = CoverageEntry("Some Old Recruitment Online Form 2025", "https://x/2", "10 November 2025")
    nodate = CoverageEntry("Some Dateless Notice Online Form 2025", "https://x/3", None)
    assert is_actionable(live, today) is True
    assert is_actionable(stale, today) is False
    assert is_actionable(nodate, today) is False


def test_build_report_actionable_only_counts_skipped():
    from datetime import date

    entries = [
        CoverageEntry("Assam Rifles Technical / Tradesman Online Form 2026", "https://x/1", "14 December 2026"),
        CoverageEntry("Old Archive Recruitment Online Form 2024", "https://x/2", "14 December 2024"),
    ]
    report = build_report(entries, ["Assam Rifles Technical & Tradesman Recruitment Rally 2026 — 354 posts"],
                          actionable_only=True, today=date(2026, 11, 17))
    assert [e.url for e in report.entries] == ["https://x/1"]
    assert report.filtered_out == 1


SAMPLE_ADMIT_HTML = """
<h2 class="gb-headline-text">All Latest Admit Card</h2>
<div class="gb-container">
<ul class="wp-block-latest-posts__list wp-block-latest-posts is-layout-flow"><li><a class="wp-block-latest-posts__post-title" href="https://example.com/cpo/">SSC CPO SI CAPF Paper-I Exam City Details 2026</a></li><li><a class="wp-block-latest-posts__post-title" href="https://example.com/cg/">SSC Constable GD Admit Card 2026 – Out</a></li><li><a class="wp-block-latest-posts__post-title" href="https://example.com/short/">A&amp;B</a></li></ul>
</div>
<ul class="footer-links"><li><a class="wp-block-latest-posts__post-title" href="https://example.com/footer/">Footer Link That Should Not Be Picked Up At All 2026</a></li></ul>
"""


def test_parse_admit_cards_page_scopes_and_unescapes():
    from app.services.coverage_watchdog import parse_admit_cards_page

    entries = parse_admit_cards_page(SAMPLE_ADMIT_HTML)
    titles = [e.title for e in entries]
    assert "SSC CPO SI CAPF Paper-I Exam City Details 2026" in titles
    assert "SSC Constable GD Admit Card 2026 – Out" in titles
    # scoped to the heading section — footer link not included
    assert all("Footer" not in t for t in titles)
    # too-short titles filtered
    assert all(len(t) >= 10 for t in titles)


def test_admit_card_report_matches_seed():
    from app.services.coverage_watchdog import CoverageEntry, build_report

    entries = [CoverageEntry("SSC Constable GD Admit Card 2026 – Out", "https://x/1", None)]
    report = build_report(entries, ["SSC GD Constable (CAPFs, SSF & Rifleman)"], kind="admit_card")
    assert report.kind == "admit_card"
    assert report.seed_count == 1


def test_watchdog_filters_postponed_typos_and_maps_known_alias():
    from app.services.coverage_watchdog import (
        _NOT_ADMIT_RE,
        _TITLE_ALIASES,
        normalize_title,
    )

    assert _NOT_ADMIT_RE.search("BPSC Project Manager Pre Exam 2026 - Postpned")
    assert _NOT_ADMIT_RE.search("Bihar BPSC Factory Inspector Revised DV Schedule 2026")
    alias = normalize_title("SSC CPO SI CAPF Paper-I Exam City Details 2026")
    assert alias in _TITLE_ALIASES
    assert "delhi police" in _TITLE_ALIASES[alias]


def test_false_positive_upessc_vs_mphc_is_not_covered():
    from app.services.coverage_watchdog import (
        ADMIT_CARD_MATCH_THRESHOLD,
        CoverageEntry,
        build_report,
    )

    entry = CoverageEntry("UPESSC UP Assistant Professor Admit Card 2026", "https://x/1", None)
    seed = "Madhya Pradesh High Court — Assistant Grade III 2026: Pre-Exam Date / Admit Card"
    report = build_report(
        [entry], [seed], threshold=ADMIT_CARD_MATCH_THRESHOLD, kind="admit_card"
    )
    assert report.matched == []
    assert [e.title for e in report.missing] == [entry.title]


def test_one_seed_cannot_cover_multiple_sbi_entries():
    from app.services.coverage_watchdog import CoverageEntry, build_report

    seed = "SBI Junior Associates (Clerk) 2026 — Mains Admit Card"
    entries = [
        CoverageEntry(t, f"https://x/{i}", None)
        for i, t in enumerate([
            "SBI Junior Associates Clerk Mains Admit Card 2026",
            "SBI Junior Associates Clerk Mains Exam Date 2026",
            "SBI Junior Associates Clerk Backlog Mains Admit Card 2026",
        ])
    ]
    report = build_report(entries, [seed], threshold=0.5, kind="admit_card")
    assert len(report.matched) == 1
    assert report.distinct_matched_seeds == [seed]
    assert len(report.missing) == 2
    assert len(report.duplicate_matches.get(seed, [])) == 2


def test_explicit_ssc_cpo_alias_survives_strict_threshold():
    from app.services.coverage_watchdog import CoverageEntry, build_report
    from app.core.admit_cards import SEED_ADMIT_CARDS

    seed = next(
        s["title"] for s in SEED_ADMIT_CARDS
        if s["id"] == "ssc-si-dp-capf-2025-cpo-admit-card"
    )
    entry = CoverageEntry("SSC CPO SI CAPF Paper-I Exam City Details 2026", "https://x/1", None)
    report = build_report(
        [entry], [seed], threshold=0.99, kind="admit_card"
    )
    assert len(report.matched) == 1
    assert report.matched[0][1] == seed
    assert report.matched[0][2] == 1.0
