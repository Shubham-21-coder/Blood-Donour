"""
LifeLink: LLM Wrapper
Supports ASI1 API (ASI:One API), Anthropic Claude API, and OpenAI-compatible endpoints.
Provides structured prompt execution with automatic graceful fallback when API keys are absent.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("lifelink.llm")


class LLMClient:
    """Unified client for LLM intent parsing and reply generation."""

    def __init__(self):
        self.asi1_key = os.getenv("ASI1_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.asi1_key or self.anthropic_key or self.openai_key)

    async def complete(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Query configured LLM provider asynchronously."""
        # 1. Try ASI1 API / OpenAI-compatible endpoint
        if self.asi1_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.asi1_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "asi1-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post("https://api.asi1.ai/v1/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"ASI1 API call failed: {e}. Falling back...")

        # 2. Try Anthropic Claude API
        if self.anthropic_key:
            try:
                headers = {
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 500,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["content"][0]["text"]
            except Exception as e:
                logger.warning(f"Anthropic API call failed: {e}. Falling back...")

        return None
