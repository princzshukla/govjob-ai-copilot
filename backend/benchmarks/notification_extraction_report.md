# Notification-Extraction Benchmark Report

Date: 2026-11-15 · PDFs: 10 · model: `openai/gpt-oss-120b`

## Per-PDF results

### ibps-po-xvi.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.93 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies']

- [✗] `total_vacancies` — expected `6715` · got `None`

- [✓] `min_age` — expected `20` · got `20`

- [✓] `age_max_general` — expected `30` · got `30`

- [✓] `age_cutoff_date` — expected `2026-07-01` · got `2026-07-01`

- [✓] `application_last_date` — expected `2026-07-21` · got `2026-07-21`

- [✓] `age_relaxations` — expected `{'SC': 5, 'ST': 5, 'OBC': 3}` · got `{'SC': 5, 'ST': 5, 'OBC': 3, 'PWBD': 10, 'EX-SERVICEMEN': 5}`

- [✓] `required_qualification` — expected `tokens ['graduation']` · got `A Degree (Graduation) in any discipline from a University recognised by the Govt. Of India or any equivalent qualification`

- [✓] `pay_level` — expected `tokens ['48480']` · got `Basic: ₹ 48480-2000/7-62480-2340/2-67160-2680/7-85920`


### upsc-advt-13-2026.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.8 · needs_manual_review: True · review_reasons: ['missing critical fields: age_cutoff_date']

- [✓] `total_vacancies` — expected `13` · got `13`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `35` · got `35`

- [✗] `age_cutoff_date` — expected `2026-07-03` · got `None`

- [✓] `application_last_date` — expected `2026-12-04` · got `2026-12-04`

- [–] `age_relaxations` — expected `ungraded` · got `{'SC': 5, 'OBC': 3, 'PWBD': 10}`

- [✓] `required_qualification` — expected `tokens ['degree']` · got `A recognised Bachelor of Dental Surgery degree qualification included in part-1 of the Dentists Act, 1948 (16 of 1948)`

- [✓] `pay_level` — expected `tokens ['7th cpc']` · got `Level- 10 in the Pay Matrix as per 7th CPC`


### bhel-artisan-detailed-ad.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.95 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies']

- [✗] `total_vacancies` — expected `515` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `27` · got `27`

- [✓] `age_cutoff_date` — expected `2025-07-01` · got `2025-07-01`

- [✓] `application_last_date` — expected `2025-08-12` · got `2025-08-12`

- [✓] `age_relaxations` — expected `{'SC': 5, 'ST': 5, 'OBC': 3}` · got `{'SC': 5, 'ST': 5, 'OBC': 3, 'PWBD': 10}`

- [✓] `required_qualification` — expected `tokens ['class xth', 'national trade certificate']` · got `Class Xth PLUS National Trade Certificate (NTC / ITl) PLUS National Apprenticeship Certificate (NAC) in the respective trade`

- [✓] `pay_level` — expected `tokens ['29500']` · got `Rs 29500 – Rs 65,000`


### bhel-et-detailed-ad.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.0 · needs_manual_review: True · review_reasons: ['LLM unavailable: Error code: 400 - {\'error\': {\'message\': "Failed to generate JSON. Please adjust your prompt. See \'failed_generation\' for more details.", \'type\': \'invalid_request_error\', \'code\': \'json_validate_failed\', \'failed_generation\': \'{"total_vacancies":{"value":150,"confidence":0.9,"evidence":"Total 150^"},{"min_age":{"value":null,"confidence":0.2,"evidence":null},"age_max_general":{"value":27,"confidence":0.7,"evidence":"Upper Age Limit (years) (as on 01/09/2022) ... 27 Years"},"age_relaxations":{"value":{"SC":5,"ST":5,"OBC":3,"PwBD":10},"confidence":0.6,"evidence":"Upper age limit is relaxable for candidates belonging to the following categories ... SC/ST: - by 5 years ... OBC (NCL): – by 3 years ... Persons with Disabilities Candidates: - by 10 years for General"},"age_cutoff_date":{"value":"2022-09-01","confidence":0.9,"evidence":"(as on 01/09/2022)"},"required_qualification":{"value":"Full-Time Bachelor’s Degree in Engineering/Technology or Five year integrated Master’s degree or Dual Degree programme in Engineering or Technology in the disciplines of Civil or Mechanical or IT or Electrical or Chemical or Metallurgy Engineering","confidence":0.9,"evidence":"Full-Time Bachelor’s Degree in Engineering /Technology ... disciplines of Civil or Mechanical or IT or Electrical or Chemical or Metallurgy Engineering"},"application_last_date":{"value":"2022-10-04","confidence":0.9,"evidence":"Closing of On-line submission of application 4th October, 2022"},"pay_level":{"value":"Rs 50,000-1,60,000","confidence":0.8,"evidence":"basic pay of Rs 50,000/- in the scale of pay of Rs 50,000-1,60,000/-"},"confidence":0.65}}\'}}']

- [✗] `total_vacancies` — expected `150` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✗] `age_max_general` — expected `27 | 29` · got `None`

- [✗] `age_cutoff_date` — expected `2022-09-01` · got `None`

- [✗] `application_last_date` — expected `2022-10-04` · got `None`

- [✗] `age_relaxations` — expected `{'SC': 5, 'ST': 5, 'OBC': 3}` · got `{}`

- [✗] `required_qualification` — expected `tokens ['engineering']` · got `None`

- [✗] `pay_level` — expected `tokens ['50,000']` · got `None`


### bhel-ptmc-kolkata.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.9 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies']

- [✗] `total_vacancies` — expected `2` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `65` · got `65`

- [✓] `age_cutoff_date` — expected `2026-11-01` · got `2026-11-01`

- [✓] `application_last_date` — expected `2026-11-28` · got `2026-11-28`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['mbbs']` · got `MBBS`

- [✓] `pay_level` — expected `tokens ['500']` · got `500/- per hour`


### bhel-ptmc-corp-oct2026.pdf — **PASS**

- confidence: 0.9 · needs_manual_review: False · review_reasons: []

- [✓] `total_vacancies` — expected `2` · got `2`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `65` · got `65`

- [✓] `age_cutoff_date` — expected `2026-10-01` · got `2026-10-01`

- [✓] `application_last_date` — expected `2026-10-22` · got `2026-10-22`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['mbbs']` · got `MBBS`

- [✓] `pay_level` — expected `tokens ['500']` · got `500/- per hour`


### bhel-ptmc-ivp-goindwal.pdf — **PASS**

- confidence: 0.9 · needs_manual_review: False · review_reasons: []

- [✓] `total_vacancies` — expected `1` · got `1`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `70` · got `70`

- [✓] `age_cutoff_date` — expected `2026-08-01` · got `2026-08-01`

- [✓] `application_last_date` — expected `2026-08-26` · got `2026-08-26`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['mbbs']` · got `MBBS with Minimum one-year Exp.`

- [✓] `pay_level` — expected `tokens ['400']` · got `Rs. 68400/-`


### bhel-atc-jhansi.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.94 · needs_manual_review: True · review_reasons: ['missing critical fields: age_cutoff_date']

- [✓] `total_vacancies` — expected `2` · got `2`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `64` · got `64`

- [✗] `age_cutoff_date` — expected `2026-08-01` · got `None`

- [✓] `application_last_date` — expected `2026-08-25` · got `2026-08-25`

- [–] `age_relaxations` — expected `ungraded` · got `{}`

- [✓] `required_qualification` — expected `tokens ['iti', 'electrician']` · got `ITI passed with National Trade Certificate (NTC) in Electrician trade`

- [✓] `pay_level` — expected `tokens ['40,000']` · got `Rs. 40,000 per month`


### bhel-fta-pssr-chennai.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.85 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies, required_qualification']

- [✗] `total_vacancies` — expected `1` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `34` · got `34`

- [✓] `age_cutoff_date` — expected `2026-10-01` · got `2026-10-01`

- [✓] `application_last_date` — expected `2026-11-17 | 2026-11-23` · got `2026-11-23`

- [–] `age_relaxations` — expected `ungraded` · got `{'PWBD': 10, 'J&K': 5}`

- [✗] `required_qualification` — expected `tokens ['hindi', 'english']` · got `None`

- [✓] `pay_level` — expected `tokens ['45000']` · got `Rs.45000/- 1st Year, Rs 48,000/- 2nd Year`


### bhel-fta-cfp-rudrapur-hindi.pdf — **FLAGGED-WITH-MISSES**

- confidence: 0.8 · needs_manual_review: True · review_reasons: ['missing critical fields: total_vacancies, required_qualification']

- [✗] `total_vacancies` — expected `1` · got `None`

- [–] `min_age` — expected `-` · got `-`

- [✓] `age_max_general` — expected `35` · got `35`

- [✓] `age_cutoff_date` — expected `2026-10-30` · got `2026-10-30`

- [✓] `application_last_date` — expected `2026-11-20` · got `2026-11-20`

- [–] `age_relaxations` — expected `ungraded` · got `{'PWBD': 10}`

- [–] `required_qualification` — expected `ungraded` · got `None`

- [✓] `pay_level` — expected `tokens ['45,000']` · got `₹45,000/- per month (first year), ₹48,000/- per month (second year)`


## Scanned controls

- scanned-control-upsc.pdf: PASS — is_scanned=True needs_manual_review=True reasons=['scanned/image-only PDF — 0 chars/page, no usable text layer']
- scanned-control-ssccr.pdf: PASS — is_scanned=True needs_manual_review=True reasons=['scanned/image-only PDF — 0 chars/page, no usable text layer']

## Tally

- PASS: 2/10
- FLAGGED for manual review (safe): 8/10
- FAIL (wrong values, publishable): 0/10
- **≥ 9/10 safe (PASS or FLAGGED, zero silent wrong dates/ages): PASS** (10/10)

---

## Addendum — 2026-11-15 (re-run after Groq free-tier quota reset)

Full re-run against `openai/gpt-oss-120b` on both the primary Groq key and the
`LLM_FALLBACK_*` Groq key (same model, separate TPD budget — wired into `.env`,
never committed). Fresh tally: **2 PASS / 8 FLAGGED / 0 FAIL — 10/10 safe**,
gate still holds (≥ 9/10 safe, zero silent wrong dates/ages). Compared with the
2026-11-13 run (3 PASS / 7 FLAGGED / 0 FAIL):

* `bhel-et-detailed-ad` regressed from PASS to **LLM unavailable**: Groq rejects
  the model's output with `json_validate_failed` (HTTP 400, quota NOT the issue;
  per-day token budget was healthy). The fallback key fails the same way — same
  model, same validator. The document stays safely in `review`; nothing is
  published from it. Not scoreable either way; flagged, never published.
* `ibps-po-xvi`, `bhel-artisan-detailed-ad`, `bhel-ptmc-kolkata`: `total_vacancies`
  came back null today (was present-but-flagged on 2026-11-13) — flagged `review`.
* `upsc-advt-13-2026`, `bhel-atc-jhansi`: `age_cutoff_date` missing → `review`.
* `bhel-fta-pssr-chennai`: 2026-11-23 (the doc's latest possible date) picked
  over the 2026-11-17 starting date — correct supersetting within the doc's own
  "between 17th and 23rd November" wording; still flagged `review` (vacancies).
* Scanned controls 2/2 again: `is_scanned=True`, no LLM call, `review`.

Net effect of the trust gate held in both independent runs: **no document with a
missing or implausible critical field ever reached a publishable state.**
