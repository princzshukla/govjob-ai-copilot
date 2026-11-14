# Notification-Extraction Benchmark Report

Date: 2026-11-13 · PDFs: 10 · model: `openai/gpt-oss-120b`

## Per-PDF results

### ibps-po-xvi.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.9 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies, required_qualification']

- [✗] `total_vacancies` — expected `6715` · got `None`

- [✓] `min_age` — expected `20` · got `20`

- [✓] `age_max_general` — expected `30` · got `30`

- [✓] `age_cutoff_date` — expected `2026-07-01` · got `2026-07-01`

- [✓] `application_last_date` — expected `2026-07-21` · got `2026-07-21`

- [✓] `age_relaxations` — expected `{'SC': 5, 'ST': 5, 'OBC': 3}` · got `{'SC': 5, 'ST': 5, 'OBC': 3, 'PWBD': 10, 'EX-SERVICEMEN': 5}`

- [✗] `required_qualification` — expected `tokens ['graduation']` · got `None`

- [✓] `pay_level` — expected `tokens ['48480']` · got `Basic: ₹ 48480-2000/7-62480-2340/2-67160-2680/7-85920`


### upsc-advt-13-2026.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.75 · needs_manual_review: True · review_reasons: ['missing critical fields: age_cutoff_date']

- [✓] `total_vacancies` — expected `13` · got `13`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `35` · got `35`

- [✗] `age_cutoff_date` — expected `2026-07-03` · got `None`

- [✓] `application_last_date` — expected `2026-12-04` · got `2026-12-04`

- [–] `age_relaxations` — expected `ungraded` · got `{'SC': 5, 'OBC': 3, 'PWBD': 10}`

- [✓] `required_qualification` — expected `tokens ['degree']` · got `A recognised Bachelor of Dental Surgery degree qualification included in part-1 of the Dentists Act, 1948`

- [✓] `pay_level` — expected `tokens ['7th cpc']` · got `Level- 10 in the Pay Matrix as per 7th CPC`


### bhel-artisan-detailed-ad.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.9 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies']

- [✗] `total_vacancies` — expected `515` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `27` · got `27`

- [✓] `age_cutoff_date` — expected `2025-07-01` · got `2025-07-01`

- [✓] `application_last_date` — expected `2025-08-12` · got `2025-08-12`

- [✓] `age_relaxations` — expected `{'SC': 5, 'ST': 5, 'OBC': 3}` · got `{'SC': 5, 'ST': 5, 'OBC': 3, 'PWBD': 10}`

- [✓] `required_qualification` — expected `tokens ['class xth', 'national trade certificate']` · got `Class Xth PLUS National Trade Certificate (NTC / ITl) PLUS National Apprenticeship Certificate (NAC) in the respective trade`

- [✓] `pay_level` — expected `tokens ['29500']` · got `Rs 29500 – Rs 65,000`


### bhel-et-detailed-ad.pdf — **PASS**

- confidence: 0.9 · needs_manual_review: False · review_reasons: []

- [✓] `total_vacancies` — expected `150` · got `150`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `27 | 29` · got `27`

- [✓] `age_cutoff_date` — expected `2022-09-01` · got `2022-09-01`

- [✓] `application_last_date` — expected `2022-10-04` · got `2022-10-04`

- [✓] `age_relaxations` — expected `{'SC': 5, 'ST': 5, 'OBC': 3}` · got `{'SC': 5, 'ST': 5, 'OBC': 3, 'PWBD': 10}`

- [✓] `required_qualification` — expected `tokens ['engineering']` · got `Full-Time Bachelor’s Degree in Engineering/Technology or Five year integrated Master’s degree or Dual Degree programme in Engineering or Technology in the disciplines of Civil or Mechanical or IT or Electrical or Chemical or Metallurgy Engineering`

- [✓] `pay_level` — expected `tokens ['50,000']` · got `Rs 50,000-1,60,000`


### bhel-ptmc-kolkata.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.9 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies']

- [✗] `total_vacancies` — expected `2` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `65` · got `65`

- [✓] `age_cutoff_date` — expected `2026-11-01` · got `2026-11-01`

- [✓] `application_last_date` — expected `2026-11-28` · got `2026-11-28`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['mbbs']` · got `MBBS`

- [✓] `pay_level` — expected `tokens ['500']` · got `Rs. 500 per hour`


### bhel-ptmc-corp-oct2026.pdf — **PASS**

- confidence: 1.0 · needs_manual_review: False · review_reasons: []

- [✓] `total_vacancies` — expected `2` · got `2`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `65` · got `65`

- [✓] `age_cutoff_date` — expected `2026-10-01` · got `2026-10-01`

- [✓] `application_last_date` — expected `2026-10-22` · got `2026-10-22`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['mbbs']` · got `MBBS`

- [✓] `pay_level` — expected `tokens ['500']` · got `500/- per hour`


### bhel-ptmc-ivp-goindwal.pdf — **PASS**

- confidence: 0.8 · needs_manual_review: False · review_reasons: []

- [✓] `total_vacancies` — expected `1` · got `1`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `70` · got `70`

- [✓] `age_cutoff_date` — expected `2026-08-01` · got `2026-08-01`

- [✓] `application_last_date` — expected `2026-08-26` · got `2026-08-26`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['mbbs']` · got `MBBS with Minimum one-year Exp.`

- [✓] `pay_level` — expected `tokens ['400']` · got `Rs. 68400/-`


### bhel-atc-jhansi.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.95 · needs_manual_review: True · review_reasons: ['missing critical fields: age_cutoff_date']

- [✓] `total_vacancies` — expected `2` · got `2`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `64` · got `64`

- [✗] `age_cutoff_date` — expected `2026-08-01` · got `None`

- [✓] `application_last_date` — expected `2026-08-25` · got `2026-08-25`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['iti', 'electrician']` · got `ITI passed with National Trade Certificate (NTC) in Electrician trade`

- [✓] `pay_level` — expected `tokens ['40,000']` · got `Rs. 40,000 per month`


### bhel-fta-pssr-chennai.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.9 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies, required_qualification']

- [✗] `total_vacancies` — expected `1` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `34` · got `34`

- [✓] `age_cutoff_date` — expected `2026-10-01` · got `2026-10-01`

- [✓] `application_last_date` — expected `2026-11-17 | 2026-11-23` · got `2026-11-23`

- [–] `age_relaxations` — expected `ungraded` · got `{'PWBD': 10, 'J&K': 5}`

- [✗] `required_qualification` — expected `tokens ['hindi', 'english']` · got `None`

- [✓] `pay_level` — expected `tokens ['45000']` · got `Rs.45000/- 1st Year, Rs 48,000/- 2nd Year`


### bhel-fta-cfp-rudrapur-hindi.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.0 · needs_manual_review: True · review_reasons: ["LLM unavailable: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kz37qspnf93r00m0gy0emfjw` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 194209, Requested 6522. Please try again in 5m15.792s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}"]

- [✗] `total_vacancies` — expected `1` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✗] `age_max_general` — expected `35` · got `None`

- [✗] `age_cutoff_date` — expected `2026-10-30` · got `None`

- [✗] `application_last_date` — expected `2026-11-20` · got `None`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [–] `required_qualification` — expected `ungraded` · got `None`

- [✗] `pay_level` — expected `tokens ['45,000']` · got `None`


## Scanned controls

- scanned-control-upsc.pdf: PASS — is_scanned=True needs_manual_review=True reasons=['scanned/image-only PDF — 0 chars/page, no usable text layer']
- scanned-control-ssccr.pdf: PASS — is_scanned=True needs_manual_review=True reasons=['scanned/image-only PDF — 0 chars/page, no usable text layer']

## Tally

- PASS: 3/10
- FLAGGED for manual review (safe): 7/10
- FAIL (wrong values, publishable): 0/10
- **≥ 9/10 safe (PASS or FLAGGED, zero silent wrong dates/ages): PASS** (10/10)

---

## Addendum — 2026-11-13 (later same day)

After the run above, the extractor was hardened further: boilerplate stripping was fixed (table cells like `TOTAL` rows were being dropped as "running headers"), the keyword-window compression was re-prioritized so the annexure total-table and the qualification section are guaranteed to be inside the prompt, 429/413 now retry with Retry-After-aware backoff (413 shrinks the token budget), and the age model was changed to `age_max_general` + per-category `age_relaxations` (SC/ST +5, OBC +3, PwBD +10).

A live re-run against the same Groq free tier failed with **HTTP 429 — tokens-per-day limit hit (198,316 / 200,000 used)**. A full clean re-run is therefore pending tomorrow's quota reset; the gate stands on the completed run above (3 PASS / 7 FLAGGED / 0 FAIL, scanned controls 2/2, age relaxations extracted correctly for IBPS/Artisan/ET ads). Structural verification of the compression fix (asserts in `tests/test_notification_extractor.py` — the qualification section and the annexure `6715` total-table are now provably inside the compressed prompt within budget) passes 11/11.
