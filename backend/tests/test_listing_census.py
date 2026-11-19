"""Listing census regression tests (offline, frozen HTML fixtures)."""
from __future__ import annotations

from scripts.listing_census import collect_census, count_page

JOBS_HTML = """
<ul class="latest-posts-last-date">
  <li><a href="https://agg.example/j1">SSC CGL 2026 Online Form</a> – Last Date: 25 November 2026</li>
  <li><a href="https://agg.example/j2">UPSC NDA 2027 Online Form</a> – Last Date: 22 December 2026</li>
  <li><a href="https://agg.example/j3">SSC CGL Syllabus / Exam Pattern 2026</a></li>
  <li class="latest-post-ad"><ins class="adsbygoogle"></ins></li>
  <li class="latest-post-ad"><ins class="adsbygoogle"></ins></li>
</ul>
"""

ADMIT_HTML = """
<ul class="wp-block-latest-posts__list wp-block-latest-posts is-layout-flow">
  <li><a class="wp-block-latest-posts__post-title" href="https://agg.example/a1">SSC CGL Admit Card 2026</a></li>
  <li><a class="wp-block-latest-posts__post-title" href="https://agg.example/a2">SBI Clerk Admit Card 2026</a></li>
  <li><a class="wp-block-latest-posts__post-title" href="https://agg.example/a3">SSC Exam Calendar 2026-27</a></li>
  <li class="adsense-between-posts"><script>ads</script></li>
</ul>
"""


def test_jobs_census_counts_real_listings_and_ads():
    result = count_page(JOBS_HTML, "https://agg.example/latest-jobs/", "jobs")
    assert result["selector_found"] is True
    assert result["raw_listings"] == 3
    assert result["ad_placeholders"] == 2
    assert result["filtered_out"] == 1  # syllabus item
    assert result["effective_listings"] == 2


def test_admit_census_filters_non_admit_items():
    result = count_page(ADMIT_HTML, "https://agg.example/admit-card/", "admit_cards")
    assert result["selector_found"] is True
    assert result["raw_listings"] == 3
    assert result["ad_placeholders"] == 1
    assert result["filtered_out"] == 1  # exam calendar
    assert result["effective_listings"] == 2


def test_pagination_is_detected():
    html_with_next = JOBS_HTML + '<a href="/latest-jobs/page/2/">Next »</a>'
    assert count_page(html_with_next, "https://agg.example/latest-jobs/", "jobs")["raw_listings"] == 3
    from scripts.listing_census import _next_page_urls

    urls = _next_page_urls(html_with_next, "https://agg.example/latest-jobs/")
    assert "https://agg.example/latest-jobs/page/2/" in urls


def test_markup_drift_is_flagged_not_silently_zero():
    result = count_page("<html><body>nothing here</body></html>", "https://agg.example/", "jobs")
    assert result["selector_found"] is False
    assert result["raw_listings"] == 0


class _NoFetchClient:
    async def get(self, *args, **kwargs):
        raise AssertionError("collect_census must not fetch when both HTML pages are supplied")


async def test_collect_census_combines_both_pages_without_extra_requests():
    result = await collect_census(
        jobs_html=JOBS_HTML, admit_html=ADMIT_HTML, client=_NoFetchClient()
    )
    assert result["markup_ok"] is True
    assert result["drift"] == []
    assert result["jobs"]["effective_listings"] == 2
    assert result["admit_cards"]["effective_listings"] == 2
    assert result["jobs"]["pages_fetched"] == 1
    assert result["admit_cards"]["pagination_detected"] is False


async def test_collect_census_flags_drift_from_empty_pages():
    result = await collect_census(jobs_html="", admit_html="", client=_NoFetchClient())
    assert result["markup_ok"] is False
    assert len(result["drift"]) == 2
