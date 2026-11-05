from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.notifier import send_telegram_alert

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class AlertRequest(BaseModel):
    chat_id: str
    exam_title: str
    application_deadline: str
    days_left: int

@router.post("/send-deadline-alert")
async def trigger_deadline_alert(payload: AlertRequest):
    """
    Sends an urgent deadline alert reminder to the candidate's Telegram Chat ID.
    """
    message = (
        f"🚨 *GovJob Copilot: Deadline Reminder!*\n\n"
        f"📌 *Exam:* {payload.exam_title}\n"
        f"⏳ *Form Deadline:* `{payload.application_deadline}`\n"
        f"⚠️ *Time Remaining:* *{payload.days_left} Days Left!*\n\n"
        f"Don't miss out! Open your GovJob Copilot dashboard to apply or review your study roadmap."
    )

    success = await send_telegram_alert(payload.chat_id, message)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dispatch Telegram notification."
        )

    return {
        "status": "success",
        "message": f"Deadline alert successfully sent to Telegram chat {payload.chat_id}!"
    }