"""
LifeLink: Optional Telegram Bot Integration for Live Stage Demo (F12)
Allows a presenter or teammate to receive a real alert on Telegram and click 'Accept' live on stage.
Operates transparently in simulated mode when TELEGRAM_BOT_TOKEN is not configured.
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger("lifelink.tools.telegram")


class TelegramAlertBot:
    """Lightweight async Telegram Bot client for live demo alerts."""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.api_base = f"https://api.telegram.org/bot{self.token}" if self.token else None

    @property
    def is_enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send_emergency_alert(
        self,
        hospital_name: str,
        blood_type: str,
        units: int,
        request_id: str
    ) -> bool:
        """Send emergency blood alert to the configured demo Telegram channel or user."""
        if not self.is_enabled:
            logger.info(f"[Simulation Mode] Telegram alert simulated for {hospital_name}: {units} units of {blood_type}")
            return True

        message_text = (
            f"🚨 *LIFELINK EMERGENCY BLOOD BROADCAST* 🚨\n\n"
            f"• *Hospital*: {hospital_name}\n"
            f"• *Blood Group Needed*: `{blood_type}`\n"
            f"• *Units*: {units}\n"
            f"• *Urgency*: CRITICAL\n\n"
            f"Reply with `/accept_{request_id}` to confirm arrival."
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message_text,
            "parse_mode": "Markdown"
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{self.api_base}/sendMessage", json=payload)
                if resp.status_code == 200:
                    logger.info("Live Telegram emergency alert dispatched.")
                    return True
                else:
                    logger.warning(f"Telegram API responded with {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Failed to dispatch live Telegram alert: {e}")

        return False
