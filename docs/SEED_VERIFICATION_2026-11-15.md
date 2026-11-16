# Seed deadline verification — 2026-11-15

Every one of the 45 seed exams was checked against **official sources only** (the
recruiting organisation's own site / official notification PDF, or the Gazette of
India for UPSC calendar confirmations). Aggregators and news sites were used, at
most, to *locate* the official link — never as the proof.

Web content was treated as untrusted data. Verification was performed by five
parallel review agents on 2026-11-15 (IST). **Automated web checks can be wrong.
Please spot-check a sample before trusting the whole set** — see the shortlist
below. Nothing here is deployed until you push this branch and the DB migration
`b8d3f5a16c07` runs.

## Headline

As of 2026-11-15 (IST), only **two seed rows are in an open application window**:

| id | Job | Window |
|----|-----|--------|
| `rrb-ntpc-undergrad-12th` | RRB CEN 07/2026 NTPC Undergrad (1,688 posts) | open until **2026-11-15** (today, extended from 2026-11-13 by official corrigendum) |
| `afcat` | AFCAT-01/2027 (flying & ground duty) | open **2026-11-12 → 2026-12-11**, exam 2027-01-31 |

All other 43 rows reference the latest closed cycle; each is tagged `verified`
(dates read from an official notification) or, for one row, `check_required`.
Closed rows are **not shown in the app** — the expiry job (`app/core/tasks.py`)
hides anything with `application_deadline < today` (IST, end-of-day), and the
`/api/v1/eligibility/*` queries filter them at runtime as well. They are kept,
not deleted, and will reappear automatically when a later seed update carries a
forward deadline (that is how extended SSC/RRB/UPSC notifications reopen).

> Practical consequence: after deploy, users will see ~2 jobs until cycles of the
> 2026–27 season start getting notified (e.g. SSC GD 2027, CHSL 2027, CSE 2027 in
> Feb 2027, CDS-I 2027 around 2026-12-02). That is the honest state of the world.

## What changed per row (old → new)

`old` = the invented placeholder deadline that was in the repo before this
verification. `new` = the official deadline found, or "unverified".

| id | old | new (official) | source / note |
|----|-----|----------------|---------------|
| ssc-chsl-12th | 2026-12-30 | 2026-10-07 (CHSL 2026, closed) | Notice_of_adv_chsl_2026.pdf |
| nda-na-12th | 2026-12-10 | 2026-06-09 (NDA-II 2026, closed) | Notif-NDA-II-2026-Engl-200526.pdf |
| rrb-ntpc-undergrad-12th | 2026-12-15 | **2026-11-15 (OPEN, extended)** | rrb.indianrailways.gov.in |
| ssc-mts-havaldar-10th | 2026-12-10 | 2025-07-24 (2025 cycle, closed; 2026 not notified) | Notice_of_adv_mts_2025.pdf |
| ssc-gd-constable-10th | 2026-12-31 | 2025-12-31 (2026 cycle, closed) | Notice_of_CTGD_2026.pdf |
| delhi-police-constable-12th | 2026-12-20 | 2025-10-21 (2025 cycle, closed) | delhipolice.gov.in PDF |
| ssc-cgl-general | 2026-12-15 | 2026-06-22 (CGL 2026, Tier-I done Oct 2026) | Notice_of_adv_cgl_2026.pdf |
| rrb-ntpc-grad | 2026-11-30 | 2026-11-06 (CEN 06/2026, closed; possible extension to 2026-11-08 reported but **not officially confirmed**) | rrb.indianrailways.gov.in |
| ibps-so-it-officer | 2026-11-25 | 2026-07-21 (CRP SPL-XVI, closed) | Detailed-Notification-CRP-SPL-XVI_Final_V1_30.06.2026.pdf |
| nic-scientific-technical-asst | 2026-12-20 | 2026-09-30 (NIC STA-A, GATE-based) | recruitment.nic.in/DetailedSTA.pdf |
| sbi-po-general | 2026-12-05 | 2026-07-08 (SBI PO 2026, closed) | sbi.bank.in/web/careers/current-openings |
| ib-acio-grade-ii | 2026-12-18 | 2025-08-10 (ACIO-II 2025, closed) | mha.gov.in (live PDF 404; dates read from verbatim official notification; 2026 cycle not notified) |
| upsc-cse-ias | 2027-02-21 | 2026-02-27 (CSE 2026, closed; **CSE 2027 not yet notified**) | upsc.gov.in CSE 2026 page |
| drdo-scientist-b-cs | 2026-12-28 | 2025-07-04 (RAC Advt 156, GATE-based, closed) | rac.gov.in/download/advt_156_v3.pdf |
| ssc-stenographer-12th | 2026-12-02 | 2026-05-15 (Steno 2026, closed) | Notice_of_adv_steno_2026.pdf |
| indian-army-agniveer-gd | 2026-12-31 | 2026-04-01 (RY 2027, closed; CEE held June 2026) | joinindianarmy.nic.in rally PDF |
| iaf-agniveervayu | 2026-12-12 | 2026-07-26 (Intake 02/2027, closed; registered 06–26.07.2026) | iafrecruitment.edcil.co.in PDF |
| indian-navy-mr | 2026-12-08 | 2026-04-06 (Agniveer MR 01/27 & 02/27, closed) | joinindiannavy.gov.in PDF |
| indian-navy-ssr | 2026-12-08 | 2026-04-06 (Agniveer SSR 01/27 & 02/27, closed) | joinindiannavy.gov.in PDF |
| ibps-rrb-officer-scale1 | 2026-12-20 | 2026-09-27 (CRP RRBs-XV, extended) | CRP-RRBs-XV-notification_Revised.pdf |
| ibps-rrb-clerk | 2026-12-20 | 2026-09-27 (CRP RRBs-XV, extended; OA prelims Dec 2026) | CRP-RRBs-XV-notification_Revised.pdf |
| rbi-assistant | 2027-01-05 | 2026-03-08 (Assistant PY2025, closed) | rbidocs.rbi.org.in PDF |
| rbi-grade-b | 2027-03-08 | 2026-05-20 (Grade B PY2026, closed) | rbi.org.in/Scripts/bs_viewcontent.aspx?Id=4997 |
| nabard-grade-a | 2027-01-10 | 2025-11-30 (Advt 05/Grade A/2025-26, closed) | nabard.org Career Notices |
| lic-aao | 2026-12-12 | 2025-09-08 (AAO 32nd batch, closed) | licindia.in AAO 2025 page |
| epfo-eo-ao | 2027-01-18 | 2025-08-18 (**UPSC** Special Advt 52/2025; route moved from SSC to UPSC — title fixed) | upsc.gov.in recruitment notices |
| ssc-cpo-sub-inspector | 2027-01-10 | 2026-09-30 (CPO 2026, 1,871 vacancies, closed) | Notice_of_adv_capf_2026.pdf |
| upsc-capf-ac | 2027-04-25 | 2026-03-12 (CAPF ACs 2026, closed) | upsc.gov.in CAPF 2026 page |
| upsc-cds | 2027-01-05 | 2026-06-09 (CDS-II 2026, closed; **CDS-I 2027 expected 2026-12-02 notification, apps till 2026-12-22, exam 2027-04-11**) | Notif-CDS-II-2026-Engl-200526.pdf + UPSC Calendar 2027 |
| upsc-ies | 2026-12-05 | 2026-10-06 (**ESE 2027**, prelims 2027-01-31, closed) | Notif-ESEP-2027-Engl-160926.pdf |
| afcat | 2026-12-11 | **2026-12-11 (OPEN)** — AFCAT-01/2027, exam 2027-01-31 | careerairforce.gov.in Notification-for-AFCAT-2027.pdf |
| upsc-geologist | 2027-03-10 | 2026-09-22 (**CGSPE 2027**, prelims 2027-01-10, closed) | Notif-CGSPE-2027-Engl-020926.pdf |
| isro-scientist-b | 2027-01-30 | 2026-09-16 (ICRB:03(EMC):2026, closed; **post is 'SC', not 'SB'** — title fixed; CBT postponed, new date TBD) | isro.gov.in/ICRB_Recruitment13.html |
| iocl-officer | 2027-01-25 | 2026-09-03 (Advt IOCL/CO-HR/RECTT/2026/01, closed) | iocl.com DetailedAd14082026.pdf |
| ntpc-executive | 2027-02-10 (kept as internal placeholder; date **hidden in UI**) | **UNVERIFIED — no application window exists** (pre-GATE-2027 notice 11/26 of 2026-08-14; detailed ad after GATE-2027) | careers.ntpc.co.in — tagged `check_required` |
| kvs-tgt | 2027-01-05 | 2025-12-11 (KVS/NVS Notification 01/2025, closed; interviews Nov 2026) | cdnbbsr.s3waas.gov.in PDF |
| indian-army-technical | 2027-01-15 | 2026-04-01 (RY 2027 Agniveer Technical, closed; CEE June 2026) | joinindianarmy.nic.in ARO PDF |
| rrb-alp-10th | 2027-01-15 | 2026-06-14 (CEN 01/2026 ALP, 11,127 vacancies → 14,627 after corrigendum; CBT-1 done Nov 2026) | RRB CEN 01/2026 PDF |
| rrb-je-diploma | 2027-01-20 | 2026-09-13 (CEN 04/2026 JE/DMS, closed; CBT-1 late Oct 2026) | RRB CEN 04/2026 PDF |
| ssc-je-diploma | 2027-01-12 | 2026-09-22 (JE 2026, Paper-I Nov–Dec 2026) | Notice_of_adv_je_2026.pdf |
| rrb-technician-diploma | 2027-01-25 | 2026-07-29 (CEN 02/2026 Technician Gr-I/III, closed) | RRB CEN 02/2026 PDF |
| bsnl-jto | 2027-02-10 | 2026-07-03 (JTO(T)(DR) 2026, 100 posts, closed; exam held 2026-08-23) | externalexam.bsnl.co.in PDF |
| ibps-po-general | 2026-12-01 | 2026-07-21 (CRP PO/MT-XVI, closed; prelims Aug 2026) | Detailed-Notification_CRP-PO-XVI PDF |
| ibps-clerk-general | 2026-12-08 | 2026-08-21 (CRP CSA-XVI, closed; prelims Oct 2026) | Notification_CRP_CSA_XVI-Final.pdf |
| sbi-clerk-general | 2026-12-04 | 2025-08-26 (JA 2025, 6,589 posts, closed) | sbi.bank.in JA 2025 PDF |

Every row: `verified_on = 2026-11-15` except `ntpc-executive` (`check_required`,
`verified_on = NULL`). `official_pdf_url` now points at the document that was
actually checked (the PDF, not the homepage, where one exists).

## Rows to spot-check (suggested sample of 10, one per source family)

1. `afcat` — window is open **now**; double-check the apply link works and dates.
2. `rrb-ntpc-undergrad-12th` — closes today; likely about to be hidden.
3. `ssc-cgl-general` — biggest central exam; confirm the 2026-06-22 deadline floor.
4. `upsc-cds` — verify the CDS-II-2026 PDF is the official one on upsc.gov.in.
5. `ibps-po-general` — Ibps detailed notification CRP PO/MT-XVI.
6. `rbi-grade-b` — rbi.org.in Id=4997 (script URL, not a PDF).
7. `isro-scientist-b` — confirm the post is 'SC' and the application page is live.
8. `epfo-eo-ao` — the SSC→UPSC route change; hardest call in this batch.
9. `indian-navy-mr` — INET PDF on joinindiannavy.gov.in.
10. `ntpc-executive` — confirm no application window exists; confirm the
    "check official notification" badge renders and no guessed date is shown.

## Known errors/edge cases to watch

- `rrb-ntpc-grad`: extension to 2026-11-08 was reported in secondary coverage but
  could not be confirmed against an official corrigendum — 2026-11-06 was kept.
- `ib-acio-grade-ii`: live MHA PDF 404s; dates were read from a verbatim copy of
  the official notification (19.07–10.08.2025). The 2026 cycle is not notified.
- `epfo-eo-ao`: older references call this "via SSC"; the current cycle is UPSC
  Special Advt 52/2025. If you have better current info, fix the title/url in
  `app/core/seed.py`.
- `isro-scientist-b`: ISRO runs ICRB recruitments, and the CBT date was postponed.
  The row will reopen when a fresh advertisement carries a forward deadline.
- `ntpc-executive` is intentionally unverifiable right now (pre-GATE notice);
  it ships as `check_required` and must never show a guessed date.
- Next-cycle dates will arrive patchily (SSC GD 2027 slated Sept–Oct 2026 per the
  SSC calendar but not notified as of today). Re-running verification at each
  season is a maintenance task, not a one-off.

## Data flow after deploy

1. `alembic upgrade head` runs: adds `verified_on`/`verification_status`
   (`a1c7e3f94d52`), then applies this verification to existing rows
   (`b8d3f5a16c07`, idempotent: rows missing from the DB seed set are left alone;
   the 42 closed rows flip to `is_active=false`, history retained).
2. On startup, `upsert_seed_exams` re-applies the same verified values from
   `app/core/seed.py` to seed-id rows and **reopens** any row whose deadline in
   the file moved into the future (the extension path).
3. The expiry loop hides rows whose `application_deadline` (IST, end-of-day) has
   passed — twice a day, plus once at startup — and the eligibility queries
   filter them at runtime as a backstop.
4. UI: verified rows show "✓ Deadline verified 2026-11-15" next to the deadline;
   `check_required` rows render "Check official notification" instead of any
   date.

## Addendum — upcoming official-calendar cycles seeded 2026-11-15

Four 2027 cycles whose dates are announced in the official UPSC Programme of
Examinations/Recruitment Tests-2027 (published 2026-05-20; the upsc.gov.in PDF
403s to automated clients, but the full table is consistently reproduced by
multiple independent outlets, e.g. karmasandhan.com reproduces the sheet
verbatim — 02 Dec 2026 / 22 Dec 2026 / 11 Apr 2027 for NDA-I & CDS-I, etc.):

| id | deadline | exam | source |
|----|----------|------|--------|
| `upsc-cds-i-2027` | 2026-12-22 | 2027-04-11 | uploaded with CDS-II-2026 listing + calendar |
| `upsc-nda-i-2027` | 2026-12-22 | 2027-04-11 | same row in calendar (NDA/NA(I) & CDS(I)) |
| `upsc-cse-2027` | 2027-02-02 | 2027-05-23 | calendar (notif 2027-01-13; mains 2027-08-20) |
| `upsc-capf-ac-2027` | 2027-03-09 | 2027-07-04 | calendar (notif 2027-02-17) |

All four are `check_required` (`verified_on = NULL`, official_pdf_url = the
calendar PDF): the UI hides their dates and shows "check official notification".
Every one flips to a proper `verified` state, with real per-exam notification
PDFs, when the actual notification drops (NDA-I/CDS-I on 2026-12-02) — rerun
this verification at that time. Until then, treat the calendar dates as
planning values; the calendar's own footnote says dates are liable to
alteration if circumstances so warrant.

These four rows were inserted into the live database automatically by the
startup seed upsert (insert-missing only). No migration was required.

## Addendum 2 — currently open Prince-matching recruitments (2026-11-15)

From a manual sweep of the aggregator listing, 12 open recruitments were checked
against official sources. 4 failed verification/scope rules and were NOT seeded
(Prince not eligible or profile mismatch): SC Junior Court Attendant (max
qualification 12th), SC Court Assistant (Technical) (needs 3–4 years
software-dev experience), RRB CEN 09/2026 "Ministerial & Isolated" (all posts
need Law/Journalism/Psych/HR-diploma/Science-12th), and NTPC Executive (no
application window yet). UPSSSC Lower PCS and UPPSC RO/ARO were also left out:
both require extra gates Prince does not currently meet (PET-2025 scorecard;
NIELIT O-Level + 25 wpm Hindi). Seeded instead (all open, all Prince-eligible,
official sources only):

| id | job | deadline | verified_on |
|----|-----|----------|-------------|
| `rrb-station-master` | RRB Station Master (CEN 08/2026) | 2026-11-25 | 2026-11-15 |
| `dsssb-mts` | DSSSB Multi-Tasking Staff (Advt 06/2026) | 2026-12-11 | 2026-11-15 |
| `indian-bank-apprentice` | Indian Bank Apprentice (FY 2026-27) | 2026-11-25 | 2026-11-15 |
| `nicl-apprentice` | NICL Graduate Apprentice (2026-27) | 2026-11-18 | 2026-11-15 |
| `hcl-apprentice-10th` | HCL Trade Apprentice (10th-pass trades only) | 2026-11-24 | 2026-11-15 |
| `bhu-computer-operator` | BHU Computer Operator Grade-I (Advt 03/26-27; BCA/B.Sc ≥55%) | 2026-11-25 | 2026-11-15 |
| `rml-lims-hospital-attendant` | Dr RMLIMS Hospital Attendant Grade-II (Advt 81/2026) | 2026-11-20 | 2026-11-15 |

The RRB row is the only one whose notification PDF is WAF-blocked to automated
fetches — dates/vacancies were corroborated via official PIB release and RRB
listings (open in a browser for the full CEN). Indian Bank's official domain is
now `indianbank.bank.in`; `indianbank.co.in` did not respond. Apply-links and
the exact exam dates above must be re-checked on the official pages the moment
you actually apply.

## Not done (out of scope, as agreed)

- Broadening to dozens of official portals — after hosting is sorted, add one at
  a time, starting with the sources your students ask about most.
- Automatic next-cycle detection for closed rows — a poll failure mode today is
  silent hiding; monitoring (Layer-1 zero-change alerts) exists for sources, not
  for "reopen on new notification" of seed rows. Seed extensions only reopen via
  the seed refresh at startup or the Layer-2 publish path.

## Addendum — apply links seeded 2026-11-16

The seed file now carries an `apply_url` (official online application portal)
per row, researched on 2026-11-16 against official sources only. Stable
portal entry points were preferred over cycle-specific direct links; where a
window is open, the cycle-specific official registration link is used.

| id | apply_url | source |
|----|-----------|--------|
| ssc-chsl-12th, ssc-mts-havaldar-10th, ssc-gd-constable-10th, ssc-cgl-general, ssc-stenographer-12th, ssc-je-diploma, ssc-cpo-sub-inspector | `https://ssc.gov.in/home/apply` | SSC notices: "online mode at ssc.gov.in" |
| nda-na-12th, upsc-cse-ias, upsc-capf-ac, upsc-cds, upsc-ies, upsc-geologist, epfo-eo-ao (UPSC route), upsc-cds-i-2027, upsc-nda-i-2027, upsc-cse-2027, upsc-capf-ac-2027 | `https://upsconline.nic.in` | UPSC/PIB: all applications via the UPSC Online Application Portal |
| rrb-ntpc-undergrad-12th, rrb-ntpc-grad, rrb-alp-10th, rrb-je-diploma, rrb-technician-diploma, rrb-station-master | `https://rrbapply.gov.in` | CEN 08/2026: "link for online application will be made live on rrbapply.gov.in"; RRB FAQs |
| ibps-so-it-officer, ibps-po-general, ibps-clerk-general, ibps-rrb-officer-scale1, ibps-rrb-clerk | `https://ibpsreg.ibps.in` | IBPS CRP notices: apply via ibps.in "CLICK HERE TO APPLY ONLINE" (ibpsreg.ibps.in) |
| sbi-po-general, sbi-clerk-general | `https://sbi.bank.in/web/careers/current-openings` | SBI recruitment advertisements: apply via the Careers page |
| rbi-assistant, rbi-grade-b | `https://opportunities.rbi.org.in` | RBI: applications/results only at opportunities.rbi.org.in |
| nabard-grade-a | `https://nabard.org/career` | NABARD Grade A notice: "Application is fully online at nabard.org/career" |
| lic-aao | `https://licindia.in/careers` | LIC AAO notices: applications via licindia.in Careers |
| dsssb-mts (Advt 06/2026) | `https://dsssbonline.nic.in` | Official ad: "apply online through the website dsssbonline.nic.in" |
| afcat (AFCAT-01/2027) | `https://afcat.edcil.co.in` | AFCAT-01/2027 notification: online applications only via afcat.edcil.co.in |
| nicl-apprentice | `https://nats.education.gov.in/index.php` | NICL ad: apply via the NATS portal (Enrolment ID EWBPNC096867) |
| indian-bank-apprentice | `https://ibpsreg.ibps.in/inbraoct26/` | Indian Bank Careers page (cycle-specific registration link; hides with the row after 25 Nov) |
| hcl-apprentice-10th (Hindustan Copper, Advt HCL/MCP/HR/Trade App./01/2026) | `https://www.hindustancopper.com/ITIApplicationmcp/Login/145` | Official notice: register on apprenticeship.gov.in first, then apply on the HCL site |
| bhu-computer-operator | `https://bhu.ac.in/rac` | BHU Advt 03/2026-2027: "application has to be filled online on the website bhu.ac.in/rac" |
| rml-lims-hospital-attendant | `https://www.drrmlims.ac.in/` | Dr RMLIMS Advt 78-83/2026 (online form displayed on drrmlims.ac.in) |
| iaf-agniveervayu | `https://iafrecruitment.edcil.co.in` | IAF recruitment portal hosting the Agniveer Vayu intake (02/2027 ran there) |
| indian-army-agniveer-gd, indian-army-technical | `https://joinindianarmy.nic.in` | Join Indian Army portal (rally registration) |
| indian-navy-mr, indian-navy-ssr | `https://www.joinindiannavy.gov.in` | Join Indian Navy portal |
| bsnl-jto | `https://externalexam.bsnl.co.in` | BSNL external exams portal hosting the JTO(T) recruitment |
| nic-scientific-technical-asst | `https://recruitment.nic.in` | NIC STA-A GATE-based recruitment portal |
| drdo-scientist-b-cs | `https://rac.gov.in` | DRDO RAC Scientist-B recruitment portal |

**Deliberately left without `apply_url`** (not verified against an official
source this session — the UI shows no Apply button for them):
`delhi-police-constable-12th`, `ib-acio-grade-ii`, `isro-scientist-b`,
`iocl-officer`, `ntpc-executive`, `kvs-tgt`. Future pipeline-published
notifications get an apply URL automatically when the printed notice states
one (optional, non-critical Layer-2 field), or via the admin review-queue
"Apply URL" edit before publish.

These are cycle/portal entry points, not a substitute for checking the
notice you actually apply under. Re-verify them at every season alongside
the deadline verification pass. `_REFRESHABLE_FIELDS` refreshes `apply_url`
on seed rows but never nulls a stored value the file does not define.
