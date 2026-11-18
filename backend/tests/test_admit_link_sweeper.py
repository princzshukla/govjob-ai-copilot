"""Conservative admit-card link health checks (offline, mocked client)."""
from __future__ import annotations

from types import SimpleNamespace

from app.core.tasks import link_health_decision, probe_admit_link


class FakeResponse:
    def __init__(self, status: int):
        self.status_code = status


class FakeClient:
    def __init__(self, head_status: int, get_status: int = 200, fail_head: bool = False):
        self.head_status = head_status
        self.get_status = get_status
        self.fail_head = fail_head
        self.get_calls = 0

    async def head(self, url):
        if self.fail_head:
            raise TimeoutError("timed out")
        return FakeResponse(self.head_status)

    async def get(self, url, headers=None):
        self.get_calls += 1
        return FakeResponse(self.get_status)


async def test_head_404_get_206_is_reachable():
    client = FakeClient(404, 206)
    probe = await probe_admit_link(client, "https://example.gov.in/a.pdf", {})
    assert probe["reachable"] is True
    assert probe["method"] == "GET"
    assert probe["status"] == 206
    assert probe["attempts"] == 2
    assert "head" not in probe["decision"].lower() or probe["reachable"]


async def test_head_404_get_200_is_reachable():
    client = FakeClient(404, 200)
    probe = await probe_admit_link(client, "https://example.gov.in/a.pdf", {})
    assert probe["reachable"] is True
    assert probe["status"] == 200


async def test_head_405_requires_get_fallback():
    client = FakeClient(405, 206)
    probe = await probe_admit_link(client, "https://example.gov.in/a.pdf", {})
    assert client.get_calls == 1
    assert probe["reachable"] is True


async def test_throttle_and_timeout_are_inconclusive_without_get():
    for status in (403, 429, 500):
        client = FakeClient(status)
        probe = await probe_admit_link(client, "https://example.gov.in/a.pdf", {})
        assert probe["reachable"] is False
        assert probe["confirmed_dead"] is False
        assert client.get_calls == 0
    client = FakeClient(0, fail_head=True)
    probe = await probe_admit_link(client, "https://example.gov.in/a.pdf", {})
    assert probe["confirmed_dead"] is False


def test_two_confirmed_failures_required_before_deactivation():
    row = SimpleNamespace(link_fail_count=0, link_kind="notice_pdf")
    dead = {"reachable": False, "confirmed_dead": True, "method": "GET", "status": 404,
            "attempts": 2, "decision": "confirmed_dead"}
    count, deactivate, note = link_health_decision(row, dead, threshold=2)
    assert (count, deactivate) == (1, False)
    row.link_fail_count = count
    count, deactivate, _ = link_health_decision(row, dead, threshold=2)
    assert (count, deactivate) == (2, True)


def test_temporary_failure_does_not_increment_counter():
    row = SimpleNamespace(link_fail_count=1, link_kind="notice_page")
    probe = {"reachable": False, "confirmed_dead": False, "method": "HEAD", "status": 500,
             "attempts": 1, "decision": "inconclusive: throttled/server error"}
    count, deactivate, _ = link_health_decision(row, probe, threshold=2)
    assert (count, deactivate) == (1, False)


def test_candidate_portal_is_never_deactivated_on_404():
    row = SimpleNamespace(link_fail_count=3, link_kind="candidate_portal")
    dead = {"reachable": False, "confirmed_dead": True, "method": "GET", "status": 404,
            "attempts": 2, "decision": "confirmed_dead"}
    count, deactivate, _ = link_health_decision(row, dead, threshold=2)
    assert deactivate is False
    assert count == 4
