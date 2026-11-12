"""Phase 1 acceptance tests: account ownership at the database level.

The endpoints that write these tables arrive in later phases, so the tests
exercise the schema directly. They cover the invariants the plan calls out:

* deleting an account cascades to every row it owns;
* owners must exist (FK integrity) and must be present (NOT NULL);
* phone numbers are unique but optional;
* one roadmap per account per exam;
* a week can only be completed once, and only for a positive week number.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.auth import Session, User
from app.models.candidate import CandidateProfile
from app.models.progress import RoadmapProgress
from app.models.roadmap import SavedRoadmap
from app.models.telegram import TelegramLink

PASSWORD_HASH = "$argon2id$placeholder-not-used-for-auth"
PHONE = "+919999999999"


def make_user(email: str = "owner@example.com", phone: str | None = None) -> User:
    return User(email=email, password_hash=PASSWORD_HASH, phone=phone)


def make_profile(user_id: int, profile_id: str | None = None) -> CandidateProfile:
    return CandidateProfile(
        id=profile_id or str(uuid.uuid4()),
        user_id=user_id,
        full_name="Test Candidate",
        dob=date(2000, 1, 1),
        gender="Male",
        category="General",
        is_pwd=False,
        domicile_state="Uttar Pradesh",
        highest_degree="B.Sc",
    )


def make_roadmap(user_id: int, exam_id: str = "ssc-cgl-tier1") -> SavedRoadmap:
    return SavedRoadmap(
        id=str(uuid.uuid4()),
        user_id=user_id,
        exam_id=exam_id,
        target_weeks=12,
        roadmap_json={"weeks": []},
    )


def make_progress(roadmap_id: str, week_no: int = 1) -> RoadmapProgress:
    return RoadmapProgress(roadmap_id=roadmap_id, week_no=week_no)


def make_session(user_id: int) -> Session:
    return Session(
        user_id=user_id,
        token_hash="0" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


async def add_user(db, **kwargs) -> User:
    user = make_user(**kwargs)
    db.add(user)
    await db.flush()
    return user


async def add_roadmap(db, user_id: int, exam_id: str = "ssc-cgl-tier1") -> SavedRoadmap:
    roadmap = make_roadmap(user_id, exam_id)
    db.add(roadmap)
    await db.flush()
    return roadmap


async def test_deleting_user_removes_every_owned_row():
    async with AsyncSessionLocal() as db:
        user = await add_user(db)
        db.add(make_profile(user.id))
        roadmap = await add_roadmap(db, user.id)
        db.add_all(
            [
                make_progress(roadmap.id),
                make_session(user.id),
                TelegramLink(user_id=user.id, chat_id="123456789"),
            ]
        )
        await db.commit()
        user_id = user.id

    # Plain row delete: the database cascade must do the cleanup, not the ORM.
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        assert user is not None
        await db.delete(user)
        await db.commit()

    async with AsyncSessionLocal() as db:
        for model in (
            User,
            Session,
            CandidateProfile,
            SavedRoadmap,
            RoadmapProgress,
            TelegramLink,
        ):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_deleting_roadmap_removes_its_progress():
    async with AsyncSessionLocal() as db:
        user = await add_user(db)
        roadmap = await add_roadmap(db, user.id)
        db.add(make_progress(roadmap.id))
        await db.commit()
        roadmap_id = roadmap.id

    async with AsyncSessionLocal() as db:
        roadmap = await db.get(SavedRoadmap, roadmap_id)
        assert roadmap is not None
        await db.delete(roadmap)
        await db.commit()

    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(RoadmapProgress)) == 0


async def test_owner_must_exist():
    async with AsyncSessionLocal() as db:
        db.add(make_profile(user_id=999_999))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_owner_is_required():
    async with AsyncSessionLocal() as db:
        db.add(make_profile(user_id=None))  # type: ignore[arg-type]
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_phone_is_unique_but_optional():
    async with AsyncSessionLocal() as db:
        await add_user(db, email="first@example.com", phone=PHONE)
        await add_user(db, email="second@example.com", phone=None)
        await add_user(db, email="third@example.com", phone=None)
        await db.commit()

    async with AsyncSessionLocal() as db:
        db.add(make_user(email="fourth@example.com", phone=PHONE))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_one_profile_per_user():
    async with AsyncSessionLocal() as db:
        user = await add_user(db)
        db.add(make_profile(user.id))
        await db.commit()
        user_id = user.id

    async with AsyncSessionLocal() as db:
        db.add(make_profile(user_id))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_one_roadmap_per_user_and_exam():
    async with AsyncSessionLocal() as db:
        user = await add_user(db)
        await add_roadmap(db, user.id, "ssc-cgl-tier1")
        await db.commit()
        user_id = user.id

    async with AsyncSessionLocal() as db:
        db.add(make_roadmap(user_id, "ssc-cgl-tier1"))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()

    # A different exam is a different roadmap: allowed.
    async with AsyncSessionLocal() as db:
        await add_roadmap(db, user_id, "ibps-po")
        await db.commit()


async def test_a_telegram_chat_cannot_be_linked_twice():
    async with AsyncSessionLocal() as db:
        first = await add_user(db, email="first@example.com")
        second = await add_user(db, email="second@example.com")
        db.add(TelegramLink(user_id=first.id, chat_id="123456789"))
        await db.commit()
        second_id = second.id

    async with AsyncSessionLocal() as db:
        db.add(TelegramLink(user_id=second_id, chat_id="123456789"))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_a_week_can_only_be_completed_once():
    async with AsyncSessionLocal() as db:
        user = await add_user(db)
        roadmap = await add_roadmap(db, user.id)
        db.add(make_progress(roadmap.id, week_no=1))
        await db.commit()
        roadmap_id = roadmap.id

    async with AsyncSessionLocal() as db:
        db.add(make_progress(roadmap_id, week_no=1))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_week_number_must_be_positive():
    async with AsyncSessionLocal() as db:
        user = await add_user(db)
        roadmap = await add_roadmap(db, user.id)
        db.add(make_progress(roadmap.id, week_no=0))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


async def test_new_columns_get_defaults():
    async with AsyncSessionLocal() as db:
        user = await add_user(db, email="defaults@example.com")
        await db.flush()
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.email_verified_at is None
        assert user.phone_verified_at is None
