"""
Test ASI:One API Connection and LLM Response Generation
"""

import os
import sys
import asyncio

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import LLMClient
from agents.coordinator import process_user_turn


async def main():
    print("=" * 65)
    print("   Testing ASI:One API Integration")
    print("=" * 65)
    
    llm = LLMClient()
    print(f"[*] Base URL:  {llm.base_url}")
    print(f"[*] Model:     {llm.model}")
    print(f"[*] Key Set:   {'Yes (Configured)' if llm.is_configured else 'No (Empty in .env)'}")
    print("-" * 65)

    if not llm.is_configured:
        print("[!] NOTICE: ASI_ONE_API_KEY is not yet populated in .env.")
        print("    Please paste your key into .env: ASI_ONE_API_KEY=your_key_here")
        return

    print("[*] Testing live connection to ASI:One API...")
    success, msg = await llm.test_connection()
    if success:
        print(f"[+] SUCCESS: {msg}")
        
        # Test agent intent parsing through the LLM
        print("\n[*] Testing Agent Turn processing with ASI:One LLM...")
        turn_result = await process_user_turn("test-session-asi1", "Need 2 units of O+ blood at SMS Hospital Jaipur, critical")
        print("[+] Agent successfully processed turn using ASI:One!")
        print(f"    State: {turn_result.get('state')}")
        print(f"    Donors Matched: {turn_result.get('matched_count', 0)}")
    else:
        print(f"[-] FAILED: {msg}")


if __name__ == "__main__":
    asyncio.run(main())
