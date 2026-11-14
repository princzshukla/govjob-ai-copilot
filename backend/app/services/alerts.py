"""Telegram alerts for verified users (product differentiator).

Two digest types, computed with the same eligibility engine that powers the
API so a match here is exactly what the user would see as "eligible" in the
product:

* ``notify_deadline_reminders`` — eligible exams whose ``application_deadline``
  is within ``within_days`` days. Students miss deadlines constantly; this is
  the nudge.
* ``notify_new_matches`` — eligible exams whose ``notification_date`` is
  within ``within_days`` days ("a new job matching your profile just dropped" —
  Sarkari Result shows everyone everything; this does not).

Messages go only to chats verified in ``telegram_links`` — never to a
client-supplied chat_id. When no admin chat is configured the caller can
still inspect output with ``dry_run=True``.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, select

from app.core.database import AsyncSessionLocal
from app.models.candidate import CandidateProfile
from app.models.exam import ExamNotification
from app.models.telegram import TelegramLink
from app.schemas.candidate import CandidateProfileCreate
from app.services.matcher import evaluate_all_exams
from app.services.notifier import send_telegram_alert

logger = logging.getLogger(__name__)


@dataclass
class Digest:
    user_id: int
    chat_id: str
    exam_ids: list[str]


async def _eligible_exams_for(profile: CandidateProfile, exams: list[ExamNotification]) -> list[ExamNotification]:
    candidate = CandidateProfileCreate(
        full_name=profile.full_name,
        dob=profile.dob,
        gender=profile.gender,
        category=profile.category,
        is_pwd=profile.is_pwd,
        domicile_state=profile.domicile_state,
        highest_degree=profile.highest_degree,
        stream=profile.stream,
        percentage_cgpa=float(profile.percentage_cgpa) if profile.percentage_cgpa is not None else 0.0,
        passing_year=profile.passing_year,
        graduation_status=profile.graduation_status or "Completed",
        previous_attempts=profile.previous_attempts or 0,
        skills=profile.skills or [],
    )
    response = evaluate_all_exams(candidate=candidate, exams=exams, exam_topics_map={}, primary_exam_id=None)
    allowed = {exam.exam_id for exam in response.eligible_now}
    return [exam for exam in exams if exam.id in allowed]


async def _verified_profiles() -> list[tuple[int, str, CandidateProfile]]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(TelegramLink.user_id, TelegramLink.chat_id, CandidateProfile)
                .join(CandidateProfile, CandidateProfile.user_id == TelegramLink.user_id)
                .where(TelegramLink.verified_at.is_not(None))
            )
        ).all()
        return [(user_id, chat_id, profile) for user_id, chat_id, profile in rows]


async def _active_exams() -> list[ExamNotification]:
    async with AsyncSessionLocal() as db:
        return list(
            (await db.execute(select(ExamNotification).where(ExamNotification.is_active.is_(True))))
            .scalars()
            .all()
        )


async def notify_deadline_reminders(within_days: int = 7, dry_run: bool = False) -> list[Digest]:
    today = date.today()
    exams = await _active_exams()
    digests: list[Digest] = []
    for user_id, chat_id, profile in await _verified_profiles():
        soon = [
            exam
            for exam in await _eligible_exams_for(profile, exams)
            if 0 <= (exam.application_deadline - today).days <= within_days
        ]
        if not soon:
            continue
        lines = [f"⚠️ Deadlines close within {within_days} days — exams you qualify for:"]
        for exam in sorted(soon, key=lambda e: e.application_deadline):
            lines.append(f"• {exam.title} ({exam.organizing_body}) — last date {exam.application_deadline.isoformat()}")
        text = "\n".join(lines)
        digests.append(Digest(user_id=user_id, chat_id=chat_id, exam_ids=[e.id for e in soon]))
        if dry_run:
            logger.info("[dry-run] to user %s:\n%s", user_id, text)
        else:
            await send_telegram_alert(chat_id, text)
    return digests


async def notify_new_matches(within_days: int = 7, dry_run: bool = False) -> list[Digest]:
    today = date.today()
    exams = await _active_exams()
    fresh = [
        exam
        for exam in exams
        if exam.notification_date and 0 <= (today - exam.notification_date).days <= within_days
    ]
    digests: list[Digest] = []
    for user_id, chat_id, profile in await _verified_profiles():
        matches = [exam for exam in await _eligible_exams_for(profile, exams) if exam in fresh]
        if not matches:
            continue
        lines = ["🎯 New notification{s} you may be eligible for:".format(s="s" if len(matches) > 1 else "")]
        for exam in sorted(matches, key=lambda e: e.application_deadline):
            lines.append(f"• {exam.title} ({exam.organizing_body}) — last date {exam.application_deadline.isoformat()}")
        text = "\n".join(lines)
        digests.append(Digest(user_id=user_id, chat_id=chat_id, exam_ids=[e.id for e in matches]))
        if dry_run:
            logger.info("[dry-run] to user %s:\n%s", user_id, text)
        else:
            await send_telegram_alert(chat_id, text)
    return digests


def main() -> None:
    parser = argparse.ArgumentParser(description="Send eligibility digests to Telegram-verified users")
    parser.add_argument("--deadlines", action="store_true", help="eligible exams closing soon")
    parser.add_argument("--new-matches", action="store_true", help="newly notified eligible exams")
    parser.add_argument("--within-days", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    async def run() -> None:
        if args.deadlines:
            digests = await notify_deadline_reminders(args.within_days, args.dry_run)
            print(f"deadline digests sent: {len(digests)}")
        if args.new_matches:
            digests = await notify_new_matches(args.within_days, args.dry_run)
            print(f"new-match digests sent: {len(digests)}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
