from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.core.tasks import prune_expired_sessions
from app.models.auth import Session, User

REGISTER_URL = "/api/v1/auth/register"


async def _make_user(client) -> int:
    resp = await client.post(
        REGISTER_URL,
        json={"email": "cleanup@example.com", "password": "cleanup-horse-battery", "full_name": "Clean Up"},
    )
    assert resp.status_code == 201, resp.text
    async with AsyncSessionLocal() as db:
        return await db.scalar(select(User.id).where(User.email == "cleanup@example.com"))


async def test_prune_expired_sessions_removes_only_expired(client):
    user_id = await _make_user(client)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        db.add(
            Session(
                token_hash="expired-token-hash-" + "x" * 32,
                user_id=user_id,
                expires_at=now - timedelta(hours=1),
            )
        )
        db.add(
            Session(
                token_hash="valid-token-hash-" + "y" * 32,
                user_id=user_id,
                expires_at=now + timedelta(days=1),
            )
        )
        await db.commit()

    removed = await prune_expired_sessions()
    assert removed >= 1

    async with AsyncSessionLocal() as db:
        remaining = (
            await db.execute(
                select(Session.token_hash).where(Session.user_id == user_id)
            )
        ).scalars().all()
        assert "valid-token-hash-" + "y" * 32 in remaining
        assert "expired-token-hash-" + "x" * 32 not in remaining


async def test_security_headers_present_everywhere(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Content-Security-Policy"].startswith("default-src 'none'")
    # ENVIRONMENT=test, so HSTS (HTTPS-only) must not be emitted.
    assert "Strict-Transport-Security" not in resp.headers
