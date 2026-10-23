"""
LifeLink: Inventory Agent (uAgent)
Responsible for geocoding, querying nearby hospitals and blood banks, and returning
blood stock inventory with timestamps.
Exposed via internal agent-to-agent protocol.
"""

import os
import json
import logging
import asyncio

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from uagents import Agent, Context
from dotenv import load_dotenv

from core.models import InventoryCheckRequest, InventoryCheckResponse
from tools.overpass import find_nearby_facilities
from tools.geocode import geocode_location
from core.compatibility import get_compatible_donor_types

load_dotenv()
logger = logging.getLogger("lifelink.agent.inventory")

INVENTORY_SEED = os.getenv("INVENTORY_SEED", "lifelink_inventory_agent_seed_phrase_demo_2026")
INVENTORY_PORT = int(os.getenv("INVENTORY_PORT", "8002"))

inventory_agent = Agent(
    name="inventory",
    port=INVENTORY_PORT,
    seed=INVENTORY_SEED,
    endpoint=[f"http://127.0.0.1:{INVENTORY_PORT}/submit"]
)


@inventory_agent.on_event("startup")
async def startup_handler(ctx: Context):
    ctx.logger.info(f"Inventory Agent started at address: {inventory_agent.address}")


@inventory_agent.on_message(model=InventoryCheckRequest, replies=InventoryCheckResponse)
async def handle_inventory_check(ctx: Context, sender: str, msg: InventoryCheckRequest):
    ctx.logger.info(f"Received InventoryCheckRequest for {msg.blood_type} near ({msg.latitude}, {msg.longitude})")
    
    lat = msg.latitude
    lon = msg.longitude
    if (lat == 0.0 and lon == 0.0) and msg.hospital_name:
        lat, lon = await geocode_location(msg.hospital_name)

    # Search nearby facilities (auto-expanding radius if results are few, per F7)
    facilities = await find_nearby_facilities(lat, lon, radius_km=msg.radius_km, auto_expand=True)
    
    # Calculate compatible blood units in stock
    compatible_types = get_compatible_donor_types(msg.blood_type) if msg.blood_type else []
    total_compatible_units = 0
    facilities_payload = []

    for f in facilities:
        f_units = sum(f.stock.get(ct, 0) for ct in compatible_types)
        total_compatible_units += f_units
        facilities_payload.append(f.model_dump())

    response = InventoryCheckResponse(
        request_id=msg.request_id,
        facilities=facilities_payload,
        search_radius_km=msg.radius_km,
        compatible_units_total=total_compatible_units,
        status="success",
        timestamp=facilities[0].last_updated if facilities else "recent"
    )

    ctx.logger.info(f"Replying to {sender}: found {len(facilities)} facilities, {total_compatible_units} units available.")
    await ctx.send(sender, response)


if __name__ == "__main__":
    inventory_agent.run()
