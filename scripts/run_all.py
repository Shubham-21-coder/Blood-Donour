"""
LifeLink: Multi-Agent Launcher
Boots all 3 uAgents:
1. Coordinator Agent (ACP, exposed to ASI:One)
2. Inventory Agent (OSM/Overpass geocoding & stock)
3. Donor Outreach Agent (NBTC eligibility, ranking, alert waves, privacy gate)
"""

import os
import sys
import asyncio
import logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from uagents import Bureau
from agents.coordinator import coordinator_agent
from agents.inventory import inventory_agent
from agents.donor_outreach import donor_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lifelink.launcher")


def main():
    print("=" * 70)
    print("   LifeLink: Emergency Blood Donor Multi-Agent System")
    print("   ASI:One Agent Challenge — 'From Intent to Action'")
    print("=" * 70)
    print(f"[*] Coordinator Agent Address: {coordinator_agent.address}")
    print(f"[*] Inventory Agent Address:   {inventory_agent.address}")
    print(f"[*] Donor Outreach Address:    {donor_agent.address}")
    print("-" * 70)
    print("[+] Surface: ASI:One Chat via Agent Chat Protocol (ACP v0.3.0)")
    print("[+] Cards:   Carousel, Form Review, Live Status (with Text Fallbacks)")
    print("[+] Safety:  NBTC Rule-Based Eligibility | Privacy Gate Masked Contacts")
    print("=" * 70)
    print("Starting agents in Bureau mode...")

    bureau = Bureau(port=8000)
    bureau.add(coordinator_agent)
    bureau.add(inventory_agent)
    bureau.add(donor_agent)

    bureau.run()


if __name__ == "__main__":
    main()
