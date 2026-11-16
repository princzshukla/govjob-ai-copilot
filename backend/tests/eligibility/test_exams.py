"""The /eligibility/exams listing endpoint.

``status=open`` (default) = only open windows. ``status=all`` = every stored
notification, annotated with a computed ``window_state`` (open/closed/unknown),
open windows sorted by deadline first, closed ones after.
"""
from app.core.seed import SEED_EXAMS

EXAMS_URL = "/api/v1/eligibility/exams"


async def test_exams_all_returns_every_seed_row_with_window_state(client):
    resp = await client.get(EXAMS_URL, params={"status": "all"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == len(body["exams"])
    assert body["total"] == len(SEED_EXAMS)
    assert all(e["window_state"] in ("open", "closed", "unknown") for e in body["exams"])
    # Open windows first, closed cycles after.
    states = [0 if e["window_state"] != "closed" else 1 for e in body["exams"]]
    assert states == sorted(states)


async def test_exams_open_is_subset_and_never_closed(client):
    all_body = (await client.get(EXAMS_URL, params={"status": "all"})).json()
    open_body = (await client.get(EXAMS_URL)).json()
    all_ids = {e["id"] for e in all_body["exams"]}
    open_ids = {e["id"] for e in open_body["exams"]}
    assert open_ids <= all_ids
    assert all(e["window_state"] != "closed" for e in open_body["exams"])
    assert open_body["total"] == len(open_body["exams"])


async def test_exams_rejects_bad_status(client):
    resp = await client.get(EXAMS_URL, params={"status": "everything"})
    assert resp.status_code == 422
