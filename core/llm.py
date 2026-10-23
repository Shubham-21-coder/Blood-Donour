"""
LifeLink: ASI:One LLM Client & Connection Engine
Connects directly to the official ASI:One API (https://api.asi1.ai/v1) using OpenAI SDK / HTTP.
Provides verified model completions, test_connection validation, and graceful fallback.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv
import httpx
from openai import AsyncOpenAI

load_dotenv()
logger = logging.getLogger("lifelink.llm")

DEFAULT_ASI_ONE_BASE_URL = "https://api.asi1.ai/v1"
DEFAULT_ASI_ONE_MODEL = "asi1-mini"  # Official models: asi1, asi1-mini, asi1-ultra


class LLMClient:
    """Unified client for official ASI:One LLM integration."""

    def __init__(self):
        # Support both ASI_ONE_API_KEY and legacy ASI1_API_KEY
        self.api_key = os.getenv("ASI_ONE_API_KEY") or os.getenv("ASI1_API_KEY")
        self.base_url = os.getenv("ASI_ONE_BASE_URL", DEFAULT_ASI_ONE_BASE_URL).rstrip("/")
        self.model = os.getenv("ASI_ONE_MODEL", DEFAULT_ASI_ONE_MODEL)
        
        # Optional fallback keys
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        self._openai_client = None
        if self.api_key:
            self._openai_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    @property
    def is_configured(self) -> bool:
        """Returns True if a valid ASI:One API key is present."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Tests the connection to the official ASI:One API with a minimal ping.
        Returns (success: bool, message: str).
        """
        if not self.is_configured:
            return False, "ASI_ONE_API_KEY is not configured in .env."

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a test ping responder."},
                    {"role": "user", "content": "ping"}
                ],
                "max_tokens": 10,
                "temperature": 0.0
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return True, f"Connection successful! Model '{self.model}' replied: {content.strip()}"
                elif resp.status_code == 401:
                    return False, "Authentication failed (401 Unauthorized). Please check your ASI_ONE_API_KEY in .env."
                else:
                    return False, f"ASI:One API returned status {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, f"Connection error to {self.base_url}: {str(e)}"

    async def complete(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Query official ASI:One API for structured prompt or conversational completion."""
        if self.is_configured and self._openai_client:
            try:
                response = await self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt or "You are an intelligent medical dispatch agent."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"ASI:One OpenAI-client call failed: {e}. Trying raw httpx fallback...")
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1
                    }
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            return data["choices"][0]["message"]["content"]
                except Exception as ex2:
                    logger.error(f"Raw HTTP ASI:One API call failed: {ex2}")

        return None
