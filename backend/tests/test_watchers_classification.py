"""Watcher registry + Hindi/exam-city classification (offline, no network)."""
from __future__ import annotations

from types import SimpleNamespace

from app.services.layer2_worker import classify_notice, detect_notice_kind
from app.watchers.registry import all_watchers, schedule_summary, watcher_slugs, watcher_specs


def test_registry_has_all_priority_watchers_without_duplicates():
    specs = watcher_specs()
    slugs = [s["slug"] for s in specs]
    assert len(slugs) == len(set(slugs))
    expected = {
        "upsssc-admit-cards", "rssb-home", "uppsc-admit-watch",
        "ibps-admit-watch", "sbi-admit-watch", "rrb-admit-watch",
        "cisf-admit-watch", "crpf-admit-watch", "bsf-admit-watch",
    }
    assert expected <= set(slugs)
    assert all(s["fetch_mode"] in ("httpx", "playwright", "json_api") for s in specs)
    assert all(s["interval_seconds"] >= 300 for s in specs)
    assert schedule_summary()["priority_1"]


async def test_hindi_admit_headline_classified_as_admit_card():
    kind, subtype, conf = await classify_notice(
        "18/11/2026 विज्ञापन संख्या-11-परीक्षा/2026, हवलदार प्रशिक्षक की लिखित परीक्षा के एडमिट कार्ड जारी",
        "https://upsssc.gov.in/upssscadmitcard/admitCard.aspx?ID=MAIN",
    )
    assert kind == "admit_card"
    assert subtype == "admit_card"
    assert conf >= 0.9


async def test_exam_city_stays_distinct():
    kind, subtype, conf = await classify_notice(
        "Information regarding city of examination and admission certificate for candidates",
        "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/x.pdf",
    )
    assert kind == "admit_card"
    assert subtype == "exam_city"


def test_sync_detect_notice_kind_uses_same_regex():
    link = SimpleNamespace(title="Admit Card Released 2026", url="https://example.gov.in/a.pdf")
    assert detect_notice_kind(link, None) == "admit_card"
    forced = SimpleNamespace(config={"notice_kind": "admit_card"}, name="x")
    assert detect_notice_kind(SimpleNamespace(title="result 2026", url="x"), forced) == "admit_card"
