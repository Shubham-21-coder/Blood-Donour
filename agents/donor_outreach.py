"""
LifeLink: Donor Outreach & Match Agent (uAgent)
Responsible for:
- Deterministic compatibility filtering
- NBTC clinical eligibility enforcement
- Multi-factor ranking (distance, reliability, verification badge)
- Alert wave dispatch with per-donor daily cap
- Simulated donor replies & Privacy-gated masked contact release
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

from typing import List, Dict, Any, Optional
from uagents import Agent, Context
from dotenv import load_dotenv

from core.models import (
    Donor, DonorMatchQuery, DonorMatchResult,
    BroadcastAlertRequest, BroadcastAlertStatus,
    MaskedContactRequest, MaskedContactResponse
)
from core.compatibility import get_compatible_donor_types, can_donate
from core.eligibility import is_donor_eligible
from core.ranking import rank_donors
from core.privacy import release_masked_contact
from tools.geocode import haversine_distance

load_dotenv()
logger = logging.getLogger("lifelink.agent.donor")

DONOR_SEED = os.getenv("DONOR_SEED", "lifelink_donor_outreach_agent_seed_phrase_demo_2026")
DONOR_PORT = int(os.getenv("DONOR_PORT", "8003"))
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "donors.json")

donor_agent = Agent(
    name="donor_outreach",
    port=DONOR_PORT,
    seed=DONOR_SEED,
    endpoint=[f"http://127.0.0.1:{DONOR_PORT}/submit"]
)

# In-memory donor database loaded from synthetic JSON
DONORS_DB: Dict[str, Donor] = {}


def load_donors():
    """Load synthetic donors into memory."""
    global DONORS_DB
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for d in raw:
                donor_obj = Donor(**d)
                DONORS_DB[donor_obj.id] = donor_obj
    logger.info(f"Loaded {len(DONORS_DB)} synthetic donors into memory.")


load_donors()


@donor_agent.on_event("startup")
async def startup_handler(ctx: Context):
    ctx.logger.info(f"Donor Outreach Agent started at address: {donor_agent.address}")


@donor_agent.on_message(model=DonorMatchQuery, replies=DonorMatchResult)
async def handle_donor_match(ctx: Context, sender: str, msg: DonorMatchQuery):
    ctx.logger.info(f"Processing DonorMatchQuery for {msg.blood_type} at ({msg.latitude}, {msg.longitude})")
    
    # 1. Determine compatible donor blood types
    compatible_types = get_compatible_donor_types(msg.blood_type)
    
    # 2. Filter & calculate distance
    eligible_donors: List[Donor] = []
    for d in DONORS_DB.values():
        # Compatibility check
        if d.blood_type not in compatible_types:
            continue
            
        # NBTC Eligibility check (rule-based code)
        eligible, reason = is_donor_eligible(d)
        if not eligible:
            ctx.logger.debug(f"Donor {d.name} ({d.id}) disqualified: {reason}")
            continue

        # Compute real haversine distance
        d.distance_km = haversine_distance(msg.latitude, msg.longitude, d.latitude, d.longitude)
        eligible_donors.append(d)

    # 3. Multi-factor rank
    ranked = rank_donors(eligible_donors)
    top_matches = ranked[:msg.max_donors]

    # Package matched donors
    serialized_matches = []
    for item in top_matches:
        d = item["donor"]
        serialized_matches.append({
            "id": d.id,
            "name": d.name,
            "blood_type": d.blood_type,
            "masked_phone": d.masked_phone,
            "distance_km": item["distance_km"],
            "score": item["score"],
            "badge": item["badge"],
            "verification_tier": d.verification_tier,
            "reliability_score": d.reliability_score,
            "est_eta_minutes": item["est_eta_minutes"]
        })

    resp = DonorMatchResult(
        request_id=msg.request_id,
        blood_type=msg.blood_type,
        compatible_types=compatible_types,
        matched_donors=serialized_matches,
        total_eligible=len(eligible_donors),
        status="success"
    )

    ctx.logger.info(f"Found {len(eligible_donors)} eligible donors, returning top {len(serialized_matches)}")
    await ctx.send(sender, resp)


@donor_agent.on_message(model=BroadcastAlertRequest, replies=BroadcastAlertStatus)
async def handle_broadcast_alerts(ctx: Context, sender: str, msg: BroadcastAlertRequest):
    """
    F11: Broadcast in waves with per-donor cap.
    F12: Simulate donor replies (with live acceptance).
    """
    ctx.logger.info(f"Initiating Wave {msg.wave_number} broadcast to {len(msg.donor_ids)} donors.")
    
    contacted_donors = []
    accepted_count = 0
    declined_count = 0

    for idx, did in enumerate(msg.donor_ids):
        donor = DONORS_DB.get(did)
        if not donor:
            continue

        # Increment daily alert count for spam prevention
        donor.alerts_today += 1

        # Simulate donor replies (e.g. #1 accepts, #2 declines, etc.)
        # In the demo script, the primary closest donor accepts!
        if idx == 0:
            donor.response_status = "accepted"
            donor.eta_minutes = int(12 + (donor.distance_km or 3.0) * 3)
            accepted_count += 1
            status_text = "accepted"
        elif idx == 1:
            donor.response_status = "declined"
            declined_count += 1
            status_text = "declined"
        else:
            donor.response_status = "unresponsive"
            status_text = "no_response"

        contacted_donors.append({
            "donor_id": donor.id,
            "name": donor.name,
            "status": status_text,
            "eta_minutes": donor.eta_minutes,
            "masked_phone": donor.masked_phone
        })

    summary = f"Wave {msg.wave_number} complete: {accepted_count} confirmed donor(s), {declined_count} declined."

    status_update = BroadcastAlertStatus(
        request_id=msg.request_id,
        wave_number=msg.wave_number,
        contacted_count=len(contacted_donors),
        accepted_count=accepted_count,
        declined_count=declined_count,
        donors_status=contacted_donors,
        status_summary=summary,
        is_wave_complete=True
    )

    await ctx.send(sender, status_update)


@donor_agent.on_message(model=MaskedContactRequest, replies=MaskedContactResponse)
async def handle_masked_contact_request(ctx: Context, sender: str, msg: MaskedContactRequest):
    """
    F14: Privacy Gate - Masked contact released ONLY after donor acceptance.
    """
    donor = DONORS_DB.get(msg.donor_id)
    if not donor:
        resp = MaskedContactResponse(
            request_id=msg.request_id,
            donor_id=msg.donor_id,
            donor_name="Unknown",
            masked_phone="[NOT FOUND]",
            call_relay_token="[NONE]",
            eta_minutes=0,
            unlocked=False,
            notice="Donor not found in registry."
        )
    else:
        has_accepted = (donor.response_status == "accepted")
        resp = release_masked_contact(msg.request_id, donor, has_accepted)

    await ctx.send(sender, resp)


if __name__ == "__main__":
    donor_agent.run()
