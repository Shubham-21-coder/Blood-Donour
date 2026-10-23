"""
LifeLink: Coordinator Agent (uAgent)
The primary agent exposed to ASI:One.
Implements Agent Chat Protocol (ACP), intent parsing via ASI:One LLM, multi-agent orchestration,
card rendering with plain-text fallbacks, and stateful conversation workflows.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timezone
import uuid
from typing import Dict, Any, Optional, List, Tuple

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent
)
from dotenv import load_dotenv

from core.models import (
    BloodRequestIntent,
    InventoryCheckRequest, InventoryCheckResponse,
    DonorMatchQuery, DonorMatchResult,
    BroadcastAlertRequest, BroadcastAlertStatus,
    MaskedContactRequest, MaskedContactResponse
)
from core.llm import LLMClient
from core.intent import parse_blood_request
from core.cards import (
    build_donor_carousel_card,
    build_request_review_card,
    build_live_status_card,
    build_backup_inventory_card
)
from tools.geocode import geocode_location
from tools.overpass import find_nearby_facilities
from agents.donor_outreach import donor_agent, DONORS_DB
from agents.inventory import inventory_agent

load_dotenv()
logger = logging.getLogger("lifelink.agent.coordinator")

COORDINATOR_SEED = os.getenv("COORDINATOR_SEED", "lifelink_coordinator_agent_seed_phrase_demo_2026")
COORDINATOR_PORT = int(os.getenv("COORDINATOR_PORT", "8001"))
DEMO_CITY = os.getenv("DEMO_CITY", "Jaipur, Rajasthan, India")

# Initialize Coordinator Agent (preserves seed, address, and ACP)
coordinator_agent = Agent(
    name="lifelink_coordinator",
    port=COORDINATOR_PORT,
    seed=COORDINATOR_SEED,
    endpoint=[f"http://127.0.0.1:{COORDINATOR_PORT}/submit"]
)

# Chat Protocol Specification (ACP v0.3.0)
chat_protocol = Protocol(name="AgentChatProtocol", version="0.3.0")

# LLM Client connected to official ASI:One API
llm_client = LLMClient()

# Session state store
SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "state": "IDLE",
            "intent": None,
            "matched_donors": [],
            "facilities": [],
            "confirmed_donor": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    return SESSIONS[session_id]


async def orchestrate_inventory_and_donors(intent: BloodRequestIntent) -> Tuple[List[Dict[str, Any]], List[Any]]:
    """
    Direct multi-agent orchestration helper with graceful failure degradation (F20).
    Coordinates inventory lookup and donor matching.
    """
    lat, lon = await geocode_location(intent.hospital or intent.city or "Jaipur")
    intent.latitude = lat
    intent.longitude = lon

    # 1. Nearby facilities & stock lookup
    facilities = []
    try:
        facilities = await asyncio.wait_for(
            find_nearby_facilities(lat, lon, radius_km=15.0, auto_expand=True),
            timeout=5.0
        )
    except Exception as e:
        logger.warning(f"Inventory lookup error or timeout ({e}). Using degraded baseline.")

    # 2. Donor match query
    matched_donors = []
    try:
        from core.compatibility import get_compatible_donor_types
        from core.eligibility import is_donor_eligible
        from core.ranking import rank_donors
        from tools.geocode import haversine_distance

        comp_types = get_compatible_donor_types(intent.blood_type) if intent.blood_type else []
        eligible = []
        for d in DONORS_DB.values():
            if d.blood_type in comp_types:
                is_el, _ = is_donor_eligible(d)
                if is_el:
                    d.distance_km = haversine_distance(lat, lon, d.latitude, d.longitude)
                    eligible.append(d)

        ranked = rank_donors(eligible)
        for item in ranked[:5]:
            d = item["donor"]
            matched_donors.append({
                "id": d.id,
                "name": d.name,
                "blood_type": d.blood_type,
                "masked_phone": d.masked_phone,
                "distance_km": item["distance_km"],
                "score": item["score"],
                "badge": item["badge"],
                "est_eta_minutes": item["est_eta_minutes"],
                "donor": d,
                "donor_obj": d
            })
    except Exception as e:
        logger.warning(f"Donor matching error ({e}).")

    return matched_donors, facilities


async def process_user_turn(session_id: str, user_text: str) -> Dict[str, Any]:
    """
    Core conversational state machine processing user turns.
    Integrates ASI:One LLM for intent understanding and conversational grounding.
    """
    session = get_or_create_session(session_id)
    state = session.get("state", "IDLE")
    lower = user_text.strip().lower()

    # Handle confirmation in AWAITING_CONFIRMATION state
    if state == "AWAITING_CONFIRMATION":
        if any(w in lower for w in ["confirm", "yes", "broadcast", "send", "haan", "ha", "proceed", "ok"]):
            session["state"] = "BROADCASTING"
            matched = session.get("matched_donors", [])
            intent = session.get("intent")

            # 1. Broadcast wave 1 alerts (nearest donors first, per-donor cap)
            donor_ids = [m["id"] for m in matched[:3]]
            wave_status_card = build_live_status_card(
                wave=1,
                contacted=len(donor_ids),
                accepted=0,
                declined=0
            )

            # 2. Simulate donor response (Donor #1 accepts!)
            accepted_donor = matched[0] if matched else None
            active_donor_summary = None

            if accepted_donor:
                donor_obj = accepted_donor.get("donor_obj")
                donor_obj.response_status = "accepted"
                donor_obj.eta_minutes = accepted_donor.get("est_eta_minutes", 20)

                # Privacy Gate check: release masked contact
                from core.privacy import release_masked_contact
                masked_contact = release_masked_contact(
                    request_id=session_id,
                    donor=donor_obj,
                    has_accepted=True
                )

                active_donor_summary = {
                    "name": accepted_donor["name"],
                    "eta_minutes": masked_contact.eta_minutes,
                    "masked_phone": masked_contact.masked_phone,
                    "call_relay_token": masked_contact.call_relay_token,
                    "badge": accepted_donor.get("badge")
                }
                session["confirmed_donor"] = active_donor_summary

            # 3. Live status card with confirmed donor
            updated_status_card = build_live_status_card(
                wave=1,
                contacted=len(donor_ids),
                accepted=1 if accepted_donor else 0,
                declined=1,
                active_donor_summary=active_donor_summary
            )

            # 4. Final summary
            final_summary_lines = [
                f"✅ **Emergency Blood Dispatch Update**",
                f"Donor **{active_donor_summary['name']}** accepted and is en route to **{intent.hospital or 'SMS Hospital'}**.",
                f"• **ETA**: ~{active_donor_summary['eta_minutes']} mins",
                f"• **Masked Contact**: `{active_donor_summary['masked_phone']}`",
                f"• **Secure Call Bridge**: `{active_donor_summary['call_relay_token']}`",
                "",
                f"🏥 **Backup Blood Bank**: SMS Hospital Blood Bank (Phone: `+91 141 2560291`)",
                "",
                "🛡️ *LifeLink Safety Guarantee*: All donors are verified volunteers. Paid blood donation is strictly prohibited."
            ]
            final_summary_text = "\n".join(final_summary_lines)

            session["state"] = "COMPLETED"

            return {
                "text": final_summary_text,
                "status_card": updated_status_card,
                "state": "COMPLETED",
                "confirmed_donor": active_donor_summary
            }
        else:
            if "cancel" in lower:
                session["state"] = "IDLE"
                return {"text": "Broadcast cancelled. Let me know if you need any other assistance.", "state": "IDLE"}
            state = "IDLE"

    # Parse user blood request using ASI:One LLM (with deterministic fallback)
    parsed_intent = await parse_blood_request(user_text, llm_client=llm_client)
    
    # If prior intent existed, merge missing fields
    if session.get("intent"):
        prior = session["intent"]
        if not parsed_intent.blood_type and prior.blood_type:
            parsed_intent.blood_type = prior.blood_type
        if parsed_intent.units is None and prior.units is not None:
            parsed_intent.units = prior.units
        if not parsed_intent.hospital and prior.hospital:
            parsed_intent.hospital = prior.hospital

    # Recalculate missing
    missing = []
    if not parsed_intent.blood_type:
        missing.append("blood_type")
    if parsed_intent.units is None:
        missing.append("units")
    if not parsed_intent.hospital:
        missing.append("hospital")
    parsed_intent.missing_fields = missing

    # F3: If missing required fields, ask at most ONE clarifying question
    if missing:
        field = missing[0]
        if parsed_intent.language == "hi":
            if field == "blood_type":
                q = "कृपया आवश्यक रक्त समूह (Blood Type, जैसे O+, B+, A+) बताएं?"
            elif field == "units":
                q = "आपको रक्त की कितनी यूनिट (1 से 10) की आवश्यकता है?"
            else:
                q = "कृपया अस्पताल या स्थान का नाम बताएं?"
        else:
            if field == "blood_type":
                q = "Could you please specify which blood group is required (e.g. O+, A+, B-, AB+)?"
            elif field == "units":
                q = "How many units of blood are needed (between 1 and 10)?"
            else:
                q = "Which hospital or location is the patient admitted at?"

        session["intent"] = parsed_intent
        return {
            "text": q,
            "clarifying_question": q,
            "state": "AWAITING_CLARIFICATION",
            "missing_field": field
        }

    # Intent is complete! Execute multi-agent orchestration
    matched_donors, facilities = await orchestrate_inventory_and_donors(parsed_intent)
    session["intent"] = parsed_intent
    session["matched_donors"] = matched_donors
    session["facilities"] = facilities
    session["state"] = "AWAITING_CONFIRMATION"

    # Build rich cards and fallbacks
    carousel = build_donor_carousel_card(matched_donors, parsed_intent.blood_type)
    review = build_request_review_card(parsed_intent)
    backup = build_backup_inventory_card(facilities, parsed_intent.blood_type)

    combined_response_text = (
        f"{carousel['text_fallback']}\n\n"
        f"{backup['text_fallback']}\n\n"
        f"{review['text_fallback']}"
    )

    return {
        "text": combined_response_text,
        "carousel_card": carousel,
        "review_card": review,
        "backup_card": backup,
        "state": "AWAITING_CONFIRMATION",
        "matched_count": len(matched_donors),
        "facilities_count": len(facilities)
    }


# ==========================================================
# Agent Chat Protocol (ACP) Message Handlers
# ==========================================================

@chat_protocol.on_message(model=ChatMessage, replies=ChatAcknowledgement)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """
    Handle incoming ACP ChatMessage from ASI:One.
    Always reply immediately with ChatAcknowledgement, then send reply ChatMessage.
    """
    # 1. Send immediate ChatAcknowledgement
    ack = ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc),
        acknowledged_msg_id=msg.msg_id
    )
    await ctx.send(sender, ack)
    ctx.logger.info(f"Acknowledged message {msg.msg_id} from {sender}")

    # 2. Extract text from message content
    user_text = ""
    for item in msg.content:
        if hasattr(item, "text") and item.text:
            user_text += item.text + " "
    user_text = user_text.strip()
    ctx.logger.info(f"Received user text: '{user_text}'")

    # 3. Process turn via conversation engine with ASI:One LLM
    session_id = str(sender)
    result = await process_user_turn(session_id, user_text)

    # 4. Reply with ChatMessage containing text and interactive cards
    reply_content = [
        TextContent(type="text", text=result["text"])
    ]

    reply_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid.uuid4(),
        content=reply_content
    )
    await ctx.send(sender, reply_msg)
    ctx.logger.info(f"Replied to {sender} with state: {result.get('state')}")


coordinator_agent.include(chat_protocol, publish_manifest=True)


@coordinator_agent.on_event("startup")
async def startup_handler(ctx: Context):
    ctx.logger.info("=" * 60)
    ctx.logger.info(f"LifeLink Coordinator Agent online!")
    ctx.logger.info(f"Address: {coordinator_agent.address}")
    ctx.logger.info(f"Agent Chat Protocol (ACP) v0.3.0 registered.")
    ctx.logger.info(f"ASI:One LLM Configured: {llm_client.is_configured} (Model: {llm_client.model})")
    ctx.logger.info("=" * 60)


if __name__ == "__main__":
    coordinator_agent.run()
