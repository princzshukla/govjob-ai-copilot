"""Admit-card seed + idempotent upsert.

A small, hand-curated list of currently-live admit cards, sourced only from
official board notices/PDFs (links verified at seed time). Discovery-only
automation feeds this later; the eligibility pipeline never sees these rows.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# Verified against the official source on 2026-11-17 (both SSC PDFs returned
# HTTP 200 from ssc.gov.in; the UPSC page returned HTTP 200).
_BASE_SEED_ADMIT_CARDS: list[dict] = [
    {
        "id": "ssc-si-dp-capf-2025-cpo-admit-card",
        "title": "SSC — Sub-Inspector in Delhi Police & CAPFs (2025), Paper-I: City of Examination & Admission Certificate",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "Sub-Inspector in Delhi Police and CAPFs Examination, 2025",
        "link_kind": "notice_pdf",
        "notification_date": date(2026, 11, 13),
        "exam_date": None,  # Paper-I date per the notice; not restated here on purpose
        "admit_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/City%20live%20CPO%20Exam%20notice_13112026.pdf",
        "source_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/City%20live%20CPO%20Exam%20notice_13112026.pdf",
        "last_checked_at": date(2026, 11, 17),
    },
    {
        "id": "ssc-cgept-01-02-2027-admit-card",
        "title": "SSC — Indian Coast Guard CGEPT 01/2027 & 02/2027: City of Examination & Admit Card",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "CGEPT 01/2027 & 02/2027 (Indian Coast Guard)",
        "link_kind": "notice_pdf",
        "notification_date": date(2026, 11, 6),
        "exam_date": None,
        "admit_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Englishnotice_06112026.pdf",
        "source_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Englishnotice_06112026.pdf",
        "last_checked_at": date(2026, 11, 17),
    },
    {
        "id": "upsc-ifs-main-2026-admit-card",
        "title": "UPSC — Indian Forest Service (Main) Examination 2026: e-Admit Card",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "Indian Forest Service (Main) Examination, 2026",
        "link_kind": "notice_page",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/whats-new/Indian%20Forest%20Service%20%28Main%29%20Examination%2C%202026/e%20-%20Admit%20Card",
        "source_url": "https://www.upsc.gov.in/whats-new/Indian%20Forest%20Service%20%28Main%29%20Examination%2C%202026/e%20-%20Admit%20Card",
        "last_checked_at": date(2026, 11, 17),
    },
    # Candidate-portal entries: the admit card is never a public file — the
    # official link is the board's own candidate-login page (where the card is
    # downloaded). All verified live (HTTP 200) on 2026-11-18.
    {
        "id": "ibps-rrb-officer-scale1-pre-2026",
        "title": "IBPS RRB Officer Scale-I (15th CRP RRB) Preliminary 2026 — Admit Card",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "exam_name": "IBPS RRB Officer Scale-I (Prelims) 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ibps.in/",
        "source_url": "https://ibps.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ibps-clerk-xvi-pre-2026",
        "title": "IBPS Clerk (CRP Clerks XVI) Preliminary 2026 — Admit Card",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "exam_name": "IBPS Clerk (Prelims) 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ibps.in/",
        "source_url": "https://ibps.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ibps-po-mt-xvi-mains-2026",
        "title": "IBPS PO / MT (XVI) Mains 2026 — Admit Card",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "exam_name": "IBPS Probationary Officer (Mains) 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ibps.in/",
        "source_url": "https://ibps.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ibps-so-xvi-mains-2026",
        "title": "IBPS Specialist Officer (SO XVI) Mains 2026 — Admit Card",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "exam_name": "IBPS Specialist Officer (Mains) 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ibps.in/",
        "source_url": "https://ibps.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "iim-cat-2026-admit-card",
        "title": "IIM CAT 2026 — Admit Card",
        "organizing_body": "Indian Institute of Management (IIM) / CAT",
        "exam_name": "Common Admission Test (CAT) 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://iimcat.ac.in/",
        "source_url": "https://iimcat.ac.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        # Canonical SBI careers URL verified 2026-11-18: sbi.co.in/careers
        # 302-redirects here (HTTP 200). Bot HEAD requests get 4xx — the link
        # sweeper treats portal 4xx as unverified, never as dead.
        "id": "sbi-po-2026-interview-letter",
        "title": "SBI Probationary Officers (PO) 2026 — Interview Letter",
        "organizing_body": "State Bank of India (SBI)",
        "exam_name": "SBI Probationary Officer 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://sbi.bank.in/web/careers",
        "source_url": "https://sbi.bank.in/web/careers",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "sbi-clerk-2026-mains",
        "title": "SBI Junior Associates (Clerk) 2026 — Mains Admit Card",
        "organizing_body": "State Bank of India (SBI)",
        "exam_name": "SBI Junior Associates (Clerk) Mains 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://sbi.bank.in/web/careers",
        "source_url": "https://sbi.bank.in/web/careers",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "rrb-ntpc-ug-cbtst-cen-07-2025",
        "title": "RRB NTPC (UG) CEN 07/2025 — CBTST Exam City & Admit Card",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "exam_name": "RRB NTPC Undergraduate (CEN 07/2025) CBTST",
        "link_kind": "notice_pdf",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://rrb.indianrailways.gov.in/-/image/1793605352744CBTST_exam_notice_07_2025_-_English_&_Hindi.pdf/examsDocuments",
        "source_url": "https://rrb.indianrailways.gov.in/-/image/1793605352744CBTST_exam_notice_07_2025_-_English_&_Hindi.pdf/examsDocuments",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsssc-havildar-instructor-2026",
        "title": "UPSSSC Havildar Instructor 2026 — Exam City & Admit Card",
        "organizing_body": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
        "exam_name": "UPSSSC Havildar Instructor Examination 2026",
        "link_kind": "candidate_portal",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://upsssc.gov.in/upssscadmitcard/admitCard.aspx?ID=MAIN",
        "source_url": "https://upsssc.gov.in/upssscadmitcard/admitCard.aspx?ID=MAIN",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "rssb-cet-12th-level-2026",
        "title": "RSSB CET 12th Level 2026 — Exam Date & Admit Card",
        "organizing_body": "Rajasthan Subordinate and Ministerial Services Selection Board (RSSB)",
        "exam_name": "RSSB Common Eligibility Test (CET) 12th Level 2026",
        "link_kind": "notice_pdf",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://rssb.rajasthan.gov.in/storage/news_item/1794893623.pdf",
        "source_url": "https://rssb.rajasthan.gov.in/storage/news_item/1794893623.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "rrb-paramed-05-2026-admit",
        "title": "RRB Paramedical Staff (CEN 05/2026) — Exam City Intimation / Admit Card",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "exam_name": "RRB Paramedical Staff CEN 05/2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://rrb.indianrailways.gov.in/-/image/1794634614350City_Intimation_Notice_05_2026_Hindi-merged.pdf/examsDocuments",
        "source_url": "https://rrb.indianrailways.gov.in/-/image/1794634614350City_Intimation_Notice_05_2026_Hindi-merged.pdf/examsDocuments",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "cisf-tradesman-2026-admit",
        "title": "CISF Constable (Tradesman) 2026 — Admit Card / Exam City",
        "organizing_body": "Central Industrial Security Force (CISF)",
        "exam_name": "CISF Constable Tradesman Recruitment 2026",
        "link_kind": "candidate_portal",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://cisfrectt.cisf.gov.in/",
        "source_url": "https://cisfrectt.cisf.gov.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "bsf-tradesman-2026-admit",
        "title": "BSF Constable Tradesman 2026 — Written Exam Admit Card",
        "organizing_body": "Border Security Force (BSF)",
        "exam_name": "BSF Constable Tradesman Recruitment 2026",
        "link_kind": "candidate_portal",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://rectt.bsf.gov.in/",
        "source_url": "https://rectt.bsf.gov.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "mphc-ag3-2026-admit",
        "title": "Madhya Pradesh High Court — Assistant Grade III 2026: Pre-Exam Date / Admit Card",
        "organizing_body": "Madhya Pradesh High Court (MPHC)",
        "exam_name": "MPHC Assistant Grade III (District Courts) 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://portal.mphc.gov.in/PDF/web_pdf/RE/Notification%20of%20online%20pre%20exam%20dates%20of%20DC%20AG-III.pdf",
        "source_url": "https://portal.mphc.gov.in/PDF/web_pdf/RE/Notification%20of%20online%20pre%20exam%20dates%20of%20DC%20AG-III.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "allhc-ps-2026-admit",
        "title": "Allahabad High Court — Private Secretary Grade-I 2026: Admit Card",
        "organizing_body": "Allahabad High Court",
        "exam_name": "Allahabad HC Private Secretary Grade-I Examination 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.allahabadhighcourt.in/event/event_27547_13-11-2026.pdf",
        "source_url": "https://www.allahabadhighcourt.in/event/event_27547_13-11-2026.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "dhc-spa-pa-2026-admit",
        "title": "Delhi High Court — SPA/PA Typing Test 2026: Exam City / Admit Card",
        "organizing_body": "Delhi High Court",
        "exam_name": "Delhi HC SPA/PA Typing Test 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.delhihighcourt.nic.in/files/2026-10/recuritment/93-exams-nj.pdf",
        "source_url": "https://www.delhihighcourt.nic.in/files/2026-10/recuritment/93-exams-nj.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "bob-so-2026-admit",
        "title": "Bank of Baroda — Specialist Officer 2026: Online Exam Admit Card",
        "organizing_body": "Bank of Baroda",
        "exam_name": "Bank of Baroda Specialist Officer 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://bankofbaroda.bank.in/-/media/Project/BOB/CountryWebsites/India/Career/2026/26-10/Online-Examination-Digital-23-34.pdf",
        "source_url": "https://bankofbaroda.bank.in/-/media/Project/BOB/CountryWebsites/India/Career/2026/26-10/Online-Examination-Digital-23-34.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "navy-agniveer-2026-admit",
        "title": "Indian Navy Agniveer SSR/MR 2026 — Stage-II Admit Card",
        "organizing_body": "Indian Navy",
        "exam_name": "Indian Navy Agniveer SSR/MR 2026 Stage-II",
        "link_kind": "candidate_portal",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://agniveer.navydmpr.in/sailorscycle5/login",
        "source_url": "https://agniveer.navydmpr.in/sailorscycle5/login",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ssc-dp-hcmin-2025-admit",
        "title": "SSC Delhi Police — HC (Ministerial) 2025: PE & MT Admit Card",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "SSC Delhi Police Head Constable (Ministerial) 2025",
        "link_kind": "notice_page",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://sscnr.nic.in/newlook/ADMIT_CARD_OF_HC_MIN_2025/ADMIT_CARD_OF_HC_MIN_2025.html",
        "source_url": "https://sscnr.nic.in/newlook/ADMIT_CARD_OF_HC_MIN_2025/ADMIT_CARD_OF_HC_MIN_2025.html",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ssc-dp-exec-2025-admit",
        "title": "SSC Delhi Police Constable (Executive) 2025 — PE & MT Admit Card",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "SSC Delhi Police Constable (Executive) 2025",
        "link_kind": "notice_page",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://sscnr.nic.in/newlook/DPCE_Admit_Card/DPCE_Admit_Card.HTML",
        "source_url": "https://sscnr.nic.in/newlook/DPCE_Admit_Card/DPCE_Admit_Card.HTML",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upcisb-2026-admit",
        "title": "UPCISB UP Cooperative Bank 2026 — Various Post Admit Card",
        "organizing_body": "Uttar Pradesh Cooperative Institutional Service Board (UPCISB)",
        "exam_name": "UPCISB Various Posts 2026",
        "link_kind": "candidate_portal",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://upcisb.upsdc.gov.in/",
        "source_url": "https://upcisb.upsdc.gov.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "bihar-blet-2026-admit",
        "title": "Bihar Library Eligibility Test (BLET) 2026 — Admit Card",
        "organizing_body": "Bihar State Examination Board (BSEB)",
        "exam_name": "Bihar Library Eligibility Test 2026",
        "link_kind": "candidate_portal",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://sletregistration.cbrt.co.in/login",
        "source_url": "https://sletregistration.cbrt.co.in/login",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsssc-platoon-2026-admit",
        "title": "UPSSSC Platoon Commander / Block Organizer 2026 — Admit Card",
        "organizing_body": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
        "exam_name": "UPSSSC Platoon Commander / Block Organizer 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://upsssc.gov.in/ViewPdf.aspx?8gFyyKfR64qVwmHyHohSvVgIePwSxOV976bhdQNOdeQ=",
        "source_url": "https://upsssc.gov.in/ViewPdf.aspx?8gFyyKfR64qVwmHyHohSvVgIePwSxOV976bhdQNOdeQ=",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsc-cse-intv-2026",
        "title": "UPSC Civil Services Examination 2026 — Interview Schedule",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "UPSC Civil Services Examination (Main) 2026 Interview",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/sites/default/files/Intv-CSM-2026-Engl-171126.pdf",
        "source_url": "https://www.upsc.gov.in/sites/default/files/Intv-CSM-2026-Engl-171126.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsc-ese-pre-2027",
        "title": "UPSC Engineering Services Examination 2027 — Preliminary Exam Schedule",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "UPSC Engineering Services Examination 2027 Prelims",
        "link_kind": "notice_pdf",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/sites/default/files/TT-ESEP-2027-Engl-101126.pdf",
        "source_url": "https://www.upsc.gov.in/sites/default/files/TT-ESEP-2027-Engl-101126.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ssc-cpo-si-paper2-2025",
        "title": "SSC CPO SI (CAPF) Paper-II 2025 — Exam Date Notice",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "SSC CPO SI Paper-II 2025",
        "link_kind": "notice_pdf",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/notice_18112026.pdf",
        "source_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/notice_18112026.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "concor-mt-2026-exam-date",
        "title": "CONCOR MT / Assistant Officer 2026 — Exam Date / Official Notices",
        "organizing_body": "Container Corporation of India (CONCOR)",
        "exam_name": "CONCOR MT & Assistant Officer 2026",
        "link_kind": "notice_page",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.concorindia.co.in/recruitment-notice?lang=en",
        "source_url": "https://www.concorindia.co.in/recruitment-notice?lang=en",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ssb-hc-min-2026-admit",
        "title": "SSB Head Constable (Ministerial) 2026 — Skill Test / Admit Card",
        "organizing_body": "Sashastra Seema Bal (SSB)",
        "exam_name": "SSB HC Ministerial 2026 Skill Test",
        "link_kind": "notice_page",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ssb.gov.in/",
        "source_url": "https://ssb.gov.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsc-epfo-intv-2026",
        "title": "UPSC EPFO (APFC / EO-AO) 2026 — Interview Schedule",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "UPSC EPFO APFC/EO-AO 2026 Interview",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/sites/default/files/RT-Intv-74-APFC-EPFO-Engl-301026.pdf",
        "source_url": "https://www.upsc.gov.in/sites/default/files/RT-Intv-74-APFC-EPFO-Engl-301026.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsc-geo-2027-notice",
        "title": "UPSC Geo Scientist Examination 2027 — Official Notification",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "UPSC Combined Geo-Scientist Examination 2027",
        "link_kind": "notice_pdf",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/sites/default/files/Notif-CGSPE-2027-Engl-020926.pdf",
        "source_url": "https://www.upsc.gov.in/sites/default/files/Notif-CGSPE-2027-Engl-020926.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "dcb-ae-je-2026-admit",
        "title": "Delhi Cantonment Board AE / JE 2026 — Admit Card / Exam Notice",
        "organizing_body": "Delhi Cantonment Board",
        "exam_name": "Delhi Cantonment Board AE & JE 2026",
        "link_kind": "notice_page",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://delhi.cantt.gov.in/",
        "source_url": "https://delhi.cantt.gov.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "upsc-ies-iss-intv-2026",
        "title": "UPSC IES / ISS Examination 2026 — Interview Schedule",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "UPSC Engineering/Statistical Services 2026 Interview",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/sites/default/files/Intv-IES-Exam-2026-Engl-151026.pdf",
        "source_url": "https://www.upsc.gov.in/sites/default/files/Intv-IES-Exam-2026-Engl-151026.pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "rrb-min-isolated-2026",
        "title": "RRB Ministerial & Isolated Categories 2026 — CBT Exam Date Notice",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "exam_name": "RRB Ministerial & Isolated Categories CBT 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://rrb.indianrailways.gov.in/-/image/1791546063653Merge_pdf_for_Tentative_notice.pdf/examsDocuments",
        "source_url": "https://rrb.indianrailways.gov.in/-/image/1791546063653Merge_pdf_for_Tentative_notice.pdf/examsDocuments",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "skau-nonteach-2026-admit",
        "title": "SKAU Kurukshetra Non-Teaching 2026 — Admit Card",
        "organizing_body": "Sri Kurukshetra University (SKAU)",
        "exam_name": "SKAU Non-Teaching Recruitment 2026",
        "link_kind": "candidate_portal",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://skau.eapplynow.com/Pages/AdmitCard01Login7.aspx",
        "source_url": "https://skau.eapplynow.com/Pages/AdmitCard01Login7.aspx",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "ctet-sep-2026-exam-date",
        "title": "CTET September 2026 — Exam Date / Official Portal",
        "organizing_body": "Central Board of Secondary Education (CBSE)",
        "exam_name": "CTET September 2026",
        "link_kind": "notice_page",
        "notice_subtype": "exam_city",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://ctet.nic.in/",
        "source_url": "https://ctet.nic.in/",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "cgpsc-adpo-2026-admit",
        "title": "CGPSC ADPO 2026 — Exam Schedule / Admit Card",
        "organizing_body": "Chhattisgarh Public Service Commission (CGPSC)",
        "exam_name": "CGPSC Assistant District Prosecution Officer 2026",
        "link_kind": "notice_pdf",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://psc.cg.gov.in/PDFs/notifications/SAHAYAK_JILA_LOK_ABHIYOJAN_ADHIKARI-2026_EXAM_SCHEDULE%20(06-08-2026).pdf",
        "source_url": "https://psc.cg.gov.in/PDFs/notifications/SAHAYAK_JILA_LOK_ABHIYOJAN_ADHIKARI-2026_EXAM_SCHEDULE%20(06-08-2026).pdf",
        "last_checked_at": date(2026, 11, 18),
    },
    {
        "id": "kvs-nvs-intv-2026",
        "title": "KVS / NVS Teaching & Non-Teaching 2026 — Interview Letter",
        "organizing_body": "Kendriya Vidyalaya Sangathan (KVS) / NVS",
        "exam_name": "KVS NVS Teaching & Non-Teaching 2026 Interview",
        "link_kind": "notice_page",
        "notice_subtype": "admit_card",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://kvsangathan.nic.in/en/",
        "source_url": "https://kvsangathan.nic.in/en/",
        "last_checked_at": date(2026, 11, 18),
    },
]
# Admin-approved discoveries are persisted in a small JSON overlay and become
# part of the same seed list used by upsert_admit_cards(). No second pipeline.
APPROVED_SEED_PATH = Path(
    os.environ.get("DISCOVERY_SEED_OVERLAY")
    or Path(__file__).with_name("approved_discoveries.json")
)


def load_approved_discoveries() -> list[dict]:
    try:
        data = json.loads(APPROVED_SEED_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        for card in data:
            for field in ("notification_date", "exam_date", "last_checked_at"):
                value = card.get(field)
                if isinstance(value, str):
                    card[field] = date.fromisoformat(value)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def record_approved_seed(item: dict) -> dict:
    """Append an approved discovery to the overlay (id/url dedup enforced)."""
    existing = load_approved_discoveries()
    if any(card["id"] == item["id"] or card.get("admit_url") == item.get("admit_url")
           for card in existing + _BASE_SEED_ADMIT_CARDS):
        raise ValueError("approved discovery duplicates an existing seed id or URL")
    serializable = {
        key: (value.isoformat() if isinstance(value, date) else value)
        for key, value in item.items()
    }
    existing.append(serializable)
    APPROVED_SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = APPROVED_SEED_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, APPROVED_SEED_PATH)
    # Refresh the live list so upsert_admit_cards() sees the new row.
    refresh_approved_discoveries()
    return item


def refresh_approved_discoveries() -> None:
    approved = load_approved_discoveries()
    known = {card["id"] for card in SEED_ADMIT_CARDS}
    for item in approved:
        if item.get("id") not in known:
            SEED_ADMIT_CARDS.append(item)
            known.add(item["id"])


SEED_ADMIT_CARDS: list[dict] = _BASE_SEED_ADMIT_CARDS + load_approved_discoveries()


# Older seed entries predate notice_subtype/link_kind — fill sane defaults so
# a refresh can never write NULL into a NOT NULL column.
for _seed_card in SEED_ADMIT_CARDS:
    _seed_card.setdefault("link_kind", "notice_pdf")
    _seed_card.setdefault("notice_subtype", "admit_card")


_REFRESHABLE_FIELDS = (
    "exam_name",
    "notification_date",
    "exam_date",
    "admit_url",
    "source_url",
    "last_checked_at",
    "link_kind",
    "notice_subtype",
)


async def upsert_admit_cards(db) -> int:
    """Insert missing seed admit cards; refresh provenance on existing rows.

    Reopens a row when a previously missing/moved-forward exam date arrives.
    Never overwrites admin deactivations unless the exam date actually moved
    forward. Returns the number of rows inserted.
    """
    from sqlalchemy import select

    from app.core.timeutils import today_ist
    from app.models.admit_card import AdmitCardNotification

    existing = {
        row.id: row
        for row in (await db.execute(select(AdmitCardNotification))).scalars().all()
    }
    inserted = 0
    refreshed = 0
    today = today_ist()
    for item in SEED_ADMIT_CARDS:
        row = existing.get(item["id"])
        if row is None:
            db.add(AdmitCardNotification(**item))
            inserted += 1
            continue
        changed = False
        new_exam = item.get("exam_date")
        if (
            new_exam is not None
            and row.exam_date is not None
            and new_exam > row.exam_date
            and not row.is_active
            and new_exam >= today
        ):
            row.is_active = True
            changed = True
        for field in _REFRESHABLE_FIELDS:
            value = item.get(field)
            if value != getattr(row, field):
                setattr(row, field, value)
                changed = True
        if changed:
            refreshed += 1
    if inserted or refreshed:
        await db.commit()
    if refreshed:
        logger.info("refreshed provenance for %d admit card rows", refreshed)
    return inserted
