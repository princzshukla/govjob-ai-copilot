"""Missing-notification discovery engine.

Research-only layer over the existing architecture:

* unmatched entries come from the coverage watchdog (no new scraping of the
  aggregator);
* organization/year/subtype signals are reused from coverage_watchdog;
* official candidates come from a small registry of board websites plus links
  already discovered by Layer 1 (always official domains);
* PDF verification reuses notification_extractor.extract_text_stats (PyMuPDF);
* nothing is published here — a human must approve via the admin endpoints,
  which promote into the existing SEED_ADMIT_CARDS structure.

The aggregator title/URL is only a *lead*. Evidence is always an official
board URL and, where available, text from its PDF.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.discovery import DiscoveryHistory, NotificationDiscovery
from app.models.pipeline import RawDiscoveredLink
from app.services import coverage_watchdog as cw
from app.services import notification_extractor as nx

logger = logging.getLogger(__name__)

STATUS_DISCOVERED = "discovered"
STATUS_SOURCE_SEARCH = "source_search"
STATUS_SOURCE_FOUND = "source_found"
STATUS_PDF_VERIFIED = "pdf_verified"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_DUPLICATE = "duplicate"

# Verified official board entry points (browser-verified 2026-11-18 where
# possible). Only these domains count as official evidence.
OFFICIAL_SOURCES: dict[str, dict[str, str]] = {
    "ssc": {"website": "https://ssc.gov.in/", "domain": "ssc.gov.in",
            "notice_page": "https://ssc.gov.in/notices"},
    "upsc": {"website": "https://www.upsc.gov.in/", "domain": "upsc.gov.in",
             "notice_page": "https://www.upsc.gov.in/whats-new"},
    "upsssc": {"website": "https://upsssc.gov.in/", "domain": "upsssc.gov.in",
               "notice_page": "https://upsssc.gov.in/AllNotifications.aspx"},
    "uppsc": {"website": "https://uppsc.up.nic.in/", "domain": "up.nic.in"},
    "upessc": {"website": "https://upessc.up.gov.in/", "domain": "upessc.up.gov.in"},
    "ibps": {"website": "https://www.ibps.in/", "domain": "ibps.in"},
    "sbi": {"website": "https://sbi.bank.in/web/careers", "domain": "sbi.bank.in"},
    "rrb": {"website": "https://rrb.indianrailways.gov.in/", "domain": "indianrailways.gov.in"},
    "rssb": {"website": "https://rssb.rajasthan.gov.in/", "domain": "rssb.rajasthan.gov.in"},
    "mphc": {"website": "https://mphc.gov.in/", "domain": "mphc.gov.in"},
    "allhc": {"website": "https://www.allahabadhighcourt.in/", "domain": "allahabadhighcourt.in"},
    "dhc": {"website": "https://www.delhihighcourt.nic.in/", "domain": "delhihighcourt.nic.in"},
    "bpsc": {"website": "https://bpsc.bihar.gov.in/", "domain": "bpsc.bihar.gov.in"},
    "cgpsc": {"website": "https://psc.cg.gov.in/", "domain": "psc.cg.gov.in"},
    "mpesb": {"website": "https://esb.mp.gov.in/e_default.html", "domain": "mp.gov.in"},
    "ctet": {"website": "https://ctet.nic.in/", "domain": "ctet.nic.in"},
    "navy": {"website": "https://www.joinindiannavy.gov.in/", "domain": "joinindiannavy.gov.in"},
    "cisf": {"website": "https://cisfrectt.cisf.gov.in/", "domain": "cisf.gov.in"},
    "bsf": {"website": "https://rectt.bsf.gov.in/", "domain": "bsf.gov.in"},
    "ssb": {"website": "https://ssb.gov.in/", "domain": "ssb.gov.in"},
    "skau": {"website": "https://skau.ac.in/", "domain": "skau.ac.in"},
    "upcisb": {"website": "https://upcisb.upsdc.gov.in/", "domain": "upsdc.gov.in"},
    "bob": {"website": "https://bankofbaroda.bank.in/", "domain": "bankofbaroda.bank.in"},
    "iob": {"website": "https://indianoverseasbank.co.in/", "domain": "indianoverseasbank.co.in"},
    "iim": {"website": "https://iimcat.ac.in/", "domain": "iimcat.ac.in"},
    "sci": {"website": "https://www.sci.gov.in/recruitments/", "domain": "sci.gov.in"},
    "aibe": {"website": "https://www.allindiabarexamination.com/", "domain": "allindiabarexamination.com"},
    "kvs": {"website": "https://kvsangathan.nic.in/en/", "domain": "kvsangathan.nic.in"},
    "nvs": {"website": "https://navodaya.gov.in/", "domain": "navodaya.gov.in"},
}

_HTTP_HEADERS = {"User-Agent": "govjob-copilot/0.1 (official-notice discovery)"}
_MAX_PDF_BYTES = 6 * 1024 * 1024


def analyze_entry(title: str) -> dict:
    """Deterministic signals from an aggregator title (lead, never evidence)."""
    orgs = sorted(cw.org_signals(title))
    years = sorted(cw.year_signals(title))
    subtypes = sorted(cw.subtype_signals(title))
    return {
        "organization": orgs[0] if len(orgs) == 1 else None,
        "organization_candidates": orgs,
        "recruitment_year": years[-1] if years else None,
        "notice_subtype": subtypes[0] if len(subtypes) == 1 else None,
        "normalized_title": cw.normalize_title(title),
        "strong_title": cw.normalize_strong(title),
    }


def is_official_url(url: str, organization: str | None) -> bool:
    """True when the URL host belongs to the registry domain for the org."""
    source = OFFICIAL_SOURCES.get(organization or "")
    if not source:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    domain = source["domain"].lower()
    return host == domain or host.endswith("." + domain)


def _token_overlap(title: str, document_text: str) -> float:
    """Fraction of significant aggregator tokens present in official text."""
    tokens = [t for t in cw.normalize_strong(title).split() if len(t) >= 4]
    if not tokens:
        return 0.0
    text = cw.normalize_strong(document_text[:40000])
    return round(sum(1 for t in tokens if t in text) / len(tokens), 3)


async def verify_official_candidate(url: str, title: str, client: httpx.AsyncClient) -> dict:
    """Fetch an official URL and verify it is live & topically related.

    Returns a log-safe dict; never stores aggregator HTML as evidence.
    """
    result = {"url": url, "status": 0, "method": "", "is_pdf": False,
              "text_chars": 0, "token_overlap": 0.0, "reachable": False,
              "document_matched": False, "reason": ""}
    try:
        response = await client.head(url, timeout=15)
        method, status = "HEAD", response.status_code
        if status in (404, 410, 405):
            response = await client.get(url, headers={**_HTTP_HEADERS, "Range": "bytes=0-0"}, timeout=15)
            method, status = "GET", response.status_code
    except Exception as exc:
        result["reason"] = f"network:{type(exc).__name__}"
        return result
    result["method"], result["status"] = method, status
    if not (200 <= status < 300):
        result["reason"] = f"http_{status}"
        return result
    result["reachable"] = True
    try:
        full = await client.get(url, timeout=25)
        body = full.content
    except Exception as exc:
        result["reason"] = f"download:{type(exc).__name__}"
        return result
    if body.startswith(b"%PDF-"):
        result["is_pdf"] = True
        if len(body) > _MAX_PDF_BYTES:
            result["reason"] = "pdf_too_large"
            return result
        try:
            text, _pages, _cpp = nx.extract_text_stats(body)
        except Exception as exc:
            result["reason"] = f"pdf_parse:{type(exc).__name__}"
            return result
    else:
        text = body.decode(full.encoding or "utf-8", errors="ignore")
    result["text_chars"] = len(text)
    result["token_overlap"] = _token_overlap(title, text)
    result["document_matched"] = result["token_overlap"] >= 0.4
    result["reason"] = "official_document_verified" if result["document_matched"] else "content_mismatch"
    return result


async def find_candidates(db, title: str, analysis: dict, limit: int = 6) -> list[dict]:
    """Official URLs to investigate: registry pages + Layer-1 discovered links."""
    candidates: list[dict] = []
    org = analysis.get("organization")
    source = OFFICIAL_SOURCES.get(org or "")
    if source:
        for key in ("notice_page", "website"):
            if source.get(key):
                candidates.append({"url": source[key], "source": f"registry:{key}"})
    # Layer-1 raw links are official board URLs by construction.
    try:
        rows = (await db.execute(select(RawDiscoveredLink).order_by(RawDiscoveredLink.first_seen_at.desc()))).scalars().all()
        for row in rows:
            url = row.url or ""
            if not is_official_url(url, org):
                continue
            if cw.match_score(analysis["strong_title"], cw.normalize_strong(row.title or "")) >= 0.3:
                candidates.append({"url": url, "source": "layer1_official_link"})
    except Exception:
        logger.exception("discovery candidate lookup failed")
    seen: set[str] = set()
    unique = []
    for candidate in candidates:
        if candidate["url"] not in seen:
            seen.add(candidate["url"])
            unique.append(candidate)
    return unique[:limit]


def detect_duplicate(
    *,
    analysis: dict,
    official_url: str | None,
    existing: list[dict],
) -> dict:
    """Pure duplicate check against seeds/DB/previous discoveries.

    existing items: {"id": str, "url": str|None, "title": str,
                     "organization": str|None, "year": str|None}
    """
    normalized = analysis.get("normalized_title", "")
    if official_url:
        for item in existing:
            if item.get("url") and item["url"] == official_url:
                return {"is_duplicate": True, "reference": item["id"], "reason": "exact_url"}
    for item in existing:
        if cw.normalize_title(item.get("title") or "") == normalized:
            return {"is_duplicate": True, "reference": item["id"], "reason": "normalized_title"}
    org, year = analysis.get("organization"), analysis.get("recruitment_year")
    if org and year:
        for item in existing:
            if (item.get("organization") == org and item.get("year") == year
                    and cw.match_score(normalized, cw.normalize_title(item.get("title") or "")) >= 0.8):
                return {"is_duplicate": True, "reference": item["id"], "reason": "same_org_year_same_notice"}
    return {"is_duplicate": False, "reference": None, "reason": None}


def validate_approval(record) -> str | None:
    """Gate for manual approval. Returns a reason string when not eligible."""
    if record.discovery_status in (STATUS_REJECTED, STATUS_DUPLICATE, STATUS_APPROVED):
        return f"invalid status {record.discovery_status}"
    if not (record.official_pdf_url or record.official_notification_url):
        return "no_official_url"
    if record.verification_status != "official_evidence":
        return "no_verified_official_evidence"
    return None


def compute_confidence(analysis: dict, verification: dict | None, duplicate: dict | None) -> float:
    """Confidence in the *discovery*, not an auto-publish verdict."""
    score = 0.0
    if analysis.get("organization"):
        score += 0.2
    if analysis.get("recruitment_year"):
        score += 0.1
    if analysis.get("notice_subtype"):
        score += 0.1
    if verification and verification.get("reachable"):
        score += 0.2
        if verification.get("is_pdf") and verification.get("document_matched"):
            score += 0.3
        elif verification.get("is_pdf"):
            score += 0.1
    if duplicate and duplicate.get("is_duplicate"):
        score = min(score, 0.35)
    return round(min(1.0, score), 3)


async def add_history(db, record, from_status: str | None, to_status: str,
                      note: str | None, actor: str = "system") -> None:
    db.add(DiscoveryHistory(
        discovery_id=record.id, from_status=from_status, to_status=to_status,
        actor=actor, note=(note or "")[:1000] or None,
    ))


def transition(record, to_status: str, note: str | None, actor: str = "system") -> None:
    record.discovery_status = to_status
    record.updated_at = datetime.now(timezone.utc)
    # history is written by callers that have a DB session


async def collect_existing(db, exclude_id: int | None = None,
                           notification_kind: str = "admit_card") -> list[dict]:
    """Seeds + DB rows + prior discoveries for the given notification kind.

    Default (``admit_card``) preserves the legacy comparison set exactly. The
    jobs watchdog passes ``notification_kind='job'`` to compare against
    ``SEED_EXAMS`` and ``exam_notifications`` instead.
    """
    items: list[dict] = []
    if notification_kind == "job":
        from app.core.seed import SEED_EXAMS
        from app.models.exam import ExamNotification

        for seed in SEED_EXAMS:
            signals = analyze_entry(str(seed.get("title") or ""))
            items.append({
                "id": str(seed.get("id") or ""),
                "url": seed.get("official_pdf_url") or seed.get("source_url"),
                "title": str(seed.get("title") or ""),
                "organization": signals.get("organization"),
                "year": signals.get("recruitment_year"),
                "source": "exam_seed",
            })
        for exam in (await db.execute(select(ExamNotification))).scalars().all():
            signals = analyze_entry(exam.title)
            items.append({
                "id": exam.id, "url": exam.official_pdf_url or exam.source_url,
                "title": exam.title, "organization": signals.get("organization"),
                "year": signals.get("recruitment_year"), "source": "exam_notifications",
            })
    else:
        from app.core.admit_cards import SEED_ADMIT_CARDS
        from app.models.admit_card import AdmitCardNotification

        for seed in SEED_ADMIT_CARDS:
            signals = analyze_entry(str(seed.get("title") or ""))
            items.append({
                "id": str(seed.get("id") or ""),
                "url": seed.get("admit_url"),
                "title": str(seed.get("title") or ""),
                "organization": signals.get("organization"),
                "year": signals.get("recruitment_year"),
                "source": "seed",
            })
        for card in (await db.execute(select(AdmitCardNotification))).scalars().all():
            signals = analyze_entry(card.title)
            items.append({
                "id": card.id, "url": card.admit_url, "title": card.title,
                "organization": signals.get("organization"),
                "year": signals.get("recruitment_year"), "source": "admit_cards",
            })
    prior_stmt = select(NotificationDiscovery).where(
        NotificationDiscovery.notification_kind == notification_kind
    )
    if exclude_id is not None:
        prior_stmt = prior_stmt.where(NotificationDiscovery.id != exclude_id)
    for prior in (await db.execute(prior_stmt)).scalars().all():
        items.append({
            "id": f"discovery-{prior.id}",
            "url": prior.official_pdf_url or prior.official_notification_url,
            "title": prior.aggregator_title, "organization": prior.organization,
            "year": prior.recruitment_year, "source": "discovery",
        })
    return items


async def process_entry(
    db,
    entry: "cw.CoverageEntry",
    client: httpx.AsyncClient,
    *,
    notification_kind: str = "admit_card",
    classification: str | None = None,
    verifier=None,
) -> NotificationDiscovery | None:
    """Investigate one unmatched entry. Never approves or publishes.

    ``notification_kind``/``classification``/``verifier`` are keyword-only and
    default to the legacy admit-card behaviour.
    """
    existing = (
        await db.execute(select(NotificationDiscovery).where(NotificationDiscovery.aggregator_url == entry.url))
    ).scalar_one_or_none()
    if existing is not None:
        return None  # duplicate aggregator entry — already in the queue

    # Snapshot comparison set BEFORE inserting this record, otherwise the
    # new row matches itself on normalized title.
    existing_items = await collect_existing(db, notification_kind=notification_kind)
    analysis = analyze_entry(entry.title)
    record = NotificationDiscovery(
        aggregator_title=entry.title[:500],
        aggregator_url=entry.url,
        organization=analysis["organization"],
        recruitment_year=analysis["recruitment_year"],
        notice_subtype=analysis["notice_subtype"],
        notification_kind=notification_kind,
        classification=classification,
        official_website=(OFFICIAL_SOURCES.get(analysis["organization"] or "") or {}).get("website"),
        extracted_information={"analysis": analysis},
        confidence_score=0.0,
        verification_status="unverified",
        discovery_status=STATUS_DISCOVERED,
    )
    db.add(record)
    await db.flush()
    await add_history(db, record, None, STATUS_DISCOVERED,
                      "Created from coverage watchdog unmatched entry")
    previous_status = STATUS_DISCOVERED

    duplicate = detect_duplicate(analysis=analysis, official_url=None, existing=existing_items)
    verification: dict | None = None
    candidates: list[dict] = []

    if duplicate["is_duplicate"]:
        record.discovery_status = STATUS_DUPLICATE
        record.duplicate_reference = duplicate["reference"]
        record.verification_status = "duplicate"
        note = f"Duplicate before source search: {duplicate['reason']} -> {duplicate['reference']}"
    else:
        record.discovery_status = STATUS_SOURCE_SEARCH
        await add_history(db, record, previous_status, STATUS_SOURCE_SEARCH,
                          "Searching official board sources")
        previous_status = STATUS_SOURCE_SEARCH
        candidates = await find_candidates(db, entry.title, analysis)
        official_candidates = [c for c in candidates if is_official_url(c["url"], analysis["organization"])]
        if not official_candidates:
            record.discovery_status = STATUS_NEEDS_REVIEW
            record.verification_status = "unverified"
            note = "No official-domain candidate found; manual source research required"
        else:
            for candidate in official_candidates:
                verify = verifier or verify_official_candidate
                attempt = await verify(candidate["url"], entry.title, client)
                if verification is None or attempt["token_overlap"] > verification["token_overlap"]:
                    verification = attempt
                if attempt["document_matched"]:
                    break
            url = verification["url"] if verification else ""
            if verification and verification["reachable"]:
                if verification["is_pdf"]:
                    record.official_pdf_url = url
                else:
                    record.official_notification_url = url
                record.discovery_status = (
                    STATUS_PDF_VERIFIED if verification["document_matched"] else STATUS_SOURCE_FOUND
                )
                record.verification_status = (
                    "official_evidence" if verification["document_matched"] else "official_source_only"
                )
                duplicate = detect_duplicate(analysis=analysis, official_url=url, existing=existing_items)
                if duplicate["is_duplicate"]:
                    record.discovery_status = STATUS_DUPLICATE
                    record.duplicate_reference = duplicate["reference"]
                    record.verification_status = "duplicate"
                note = (
                    f"Official candidate {verification['method']} {verification['status']}, "
                    f"pdf={verification['is_pdf']}, overlap={verification['token_overlap']}, "
                    f"reason={verification['reason']}"
                )
            else:
                record.discovery_status = STATUS_NEEDS_REVIEW
                note = f"Official candidate not verified: {(verification or {}).get('reason', 'none')}"

    record.confidence_score = compute_confidence(analysis, verification, duplicate)
    record.extracted_information = {
        "analysis": analysis,
        "verification": verification or {},
        "fields": (verification or {}).get("fields", {}),
        "classification": classification,
        "duplicate_check": duplicate,
        "candidate_count": len(candidates),
        "evidence_policy": "official_board_url_and_pdf_text_only",
    }
    record.updated_at = datetime.now(timezone.utc)
    await add_history(db, record, previous_status, record.discovery_status, note)
    return record


async def run_discovery(
    db,
    entries: list["cw.CoverageEntry"],
    limit: int = 25,
    *,
    notification_kind: str = "admit_card",
    classification_fn=None,
    verifier=None,
) -> dict:
    """Investigate unmatched entries; returns counts for logging/reporting."""
    stats = {"processed": 0, "skipped": 0, "failed": 0, "pdf_verified": 0,
             "needs_review": 0, "duplicate": 0, "source_found": 0}
    async with httpx.AsyncClient(timeout=25.0, headers=_HTTP_HEADERS, follow_redirects=True) as client:
        for entry in entries[:limit]:
            try:
                classification = classification_fn(entry) if classification_fn else None
                record = await process_entry(
                    db, entry, client, notification_kind=notification_kind,
                    classification=classification, verifier=verifier,
                )
                await db.commit()
                if record is None:
                    stats["skipped"] += 1
                else:
                    stats["processed"] += 1
                    if record.discovery_status in stats:
                        stats[record.discovery_status] += 1
            except IntegrityError:
                # Concurrent watchdog/admin scan inserted the same aggregator
                # URL first — that is an expected duplicate, not a failure.
                await db.rollback()
                stats["skipped"] += 1
            except Exception:
                await db.rollback()
                stats["failed"] += 1
                logger.exception("discovery failed for %s", entry.url)
    logger.info("discovery run: %s", stats)
    return stats
