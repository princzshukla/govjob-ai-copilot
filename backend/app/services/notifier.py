import httpx
import os

async def send_telegram_alert(chat_id: str, message: str) -> bool:
    """
    Dispatches a Telegram message via Bot API. 
    Falls back to console logging if TELEGRAM_BOT_TOKEN environment variable is not set.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print(f"\n[MOCK TELEGRAM ALERT DISPATCHED TO CHAT ID: {chat_id}]")
        print(message)
        print("-" * 50)
        return True  # Return true for local testing

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram notification error: {str(e)}")
            return False