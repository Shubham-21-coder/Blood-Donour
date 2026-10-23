"""
LifeLink: ASI1 Interactive Cards & Plain-Text Fallback Builders
Builds rich card JSON payloads and guaranteed human-readable plain-text fallbacks
for ASI:One chat interfaces.
"""

from typing import List, Dict, Any, Optional
from core.models import BloodRequestIntent, FacilityStock


def build_donor_carousel_card(ranked_donors: List[Dict[str, Any]], blood_type: str) -> Dict[str, Any]:
    """
    F15: Donor carousel card displaying ranked donors with verification badges, distance, and availability.
    Includes text fallback (F18).
    """
    items = []
    text_lines = [
        f"🩸 **Top Matching Donors Found for {blood_type}** (Verified & Eligible):",
        ""
    ]

    for idx, item in enumerate(ranked_donors[:5], start=1):
        d = item.get("donor") or item.get("donor_obj") or item
        name = d.name if hasattr(d, "name") else d.get("name", f"Donor #{idx}")
        badge = item.get("badge", "📱 Phone Verified")
        dist = item.get("distance_km", 0.0)
        score = item.get("score", 0.0)
        b_type = d.blood_type if hasattr(d, "blood_type") else d.get("blood_type", blood_type)

        card_item = {
            "title": f"#{idx} {name} ({b_type})",
            "subtitle": f"{badge} • {dist} km away",
            "details": {
                "Distance": f"{dist} km",
                "Reliability Score": f"{score}/100",
                "Verification": badge,
                "Status": "Available Now 🟢"
            },
            "actions": [
                {"label": "Select for Alert", "action_id": f"select_donor_{d.id if hasattr(d, 'id') else d.get('id')}"}
            ]
        }
        items.append(card_item)
        text_lines.append(f"{idx}. **{name}** ({b_type}) — `{dist} km away` | {badge} | Score: **{score}** | 🟢 Available")

    text_fallback = "\n".join(text_lines)

    card_payload = {
        "type": "carousel",
        "title": f"Matched Donors ({len(ranked_donors)} Eligible)",
        "items": items,
        "metadata": {
            "blood_type": blood_type,
            "count": len(ranked_donors)
        }
    }

    return {
        "card": card_payload,
        "text_fallback": text_fallback
    }


def build_request_review_card(intent: BloodRequestIntent) -> Dict[str, Any]:
    """
    F16: Request review/confirm form card allowing user confirmation before broadcasting alerts.
    Includes text fallback (F18).
    """
    text_fallback = (
        "📋 **Please Confirm Emergency Blood Broadcast Request**\n\n"
        f"• **Blood Type Needed**: `{intent.blood_type}`\n"
        f"• **Units Required**: `{intent.units} unit(s)`\n"
        f"• **Hospital**: `{intent.hospital or 'SMS Hospital, Jaipur'}`\n"
        f"• **Urgency Level**: `{intent.urgency}`\n"
        f"• **Location**: `{intent.city or 'Jaipur'}`\n\n"
        "⚠️ *Safety & Ethics Notice*: Paid donation is strictly prohibited by law. "
        "Alerts will be sent via anonymized waves to nearest verified volunteer donors.\n\n"
        "Reply **CONFIRM** to broadcast alerts now, or type any changes."
    )

    card_payload = {
        "type": "form_review",
        "title": "Emergency Blood Request Confirmation",
        "fields": [
            {"key": "blood_type", "label": "Blood Type", "value": intent.blood_type, "editable": True},
            {"key": "units", "label": "Units Needed", "value": str(intent.units), "editable": True},
            {"key": "hospital", "label": "Target Hospital", "value": intent.hospital or "SMS Hospital, Jaipur", "editable": True},
            {"key": "urgency", "label": "Urgency", "value": intent.urgency, "editable": False},
        ],
        "disclaimer": "Emergency dispatch will notify volunteer donors. Donor contact remains masked until accept.",
        "actions": [
            {"label": "Confirm & Dispatch Broadcast", "action_id": "confirm_broadcast", "style": "primary"},
            {"label": "Cancel", "action_id": "cancel_request", "style": "secondary"}
        ]
    }

    return {
        "card": card_payload,
        "text_fallback": text_fallback
    }


def build_live_status_card(
    wave: int,
    contacted: int,
    accepted: int,
    declined: int,
    active_donor_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    F17: Live status card tracking broadcast waves, responses, and confirmed donor ETA.
    Includes text fallback (F18).
    """
    donor_str = ""
    if active_donor_summary:
        name = active_donor_summary.get("name", "Confirmed Donor")
        eta = active_donor_summary.get("eta_minutes", 25)
        masked_phone = active_donor_summary.get("masked_phone", "+91 98*** **421")
        relay = active_donor_summary.get("call_relay_token", "RELAY-LL-ACTIVE")
        donor_str = (
            f"\n\n🎉 **Donor Confirmed!**\n"
            f"• **Donor**: {name}\n"
            f"• **Estimated Arrival (ETA)**: ~{eta} minutes\n"
            f"• **Masked Contact**: `{masked_phone}`\n"
            f"• **Secure Call Bridge**: `{relay}`"
        )

    text_fallback = (
        f"📡 **Live Outreach Status — Wave {wave}**\n"
        f"• Alerts Sent: **{contacted}**\n"
        f"• Responses: 🟢 **{accepted} Accepted** | 🔴 **{declined} Declined**\n"
        f"• State: {'✅ Fulfilled' if accepted > 0 else '⏳ Awaiting responses...'}"
        f"{donor_str}"
    )

    card_payload = {
        "type": "live_status",
        "title": f"Dispatch Status: Wave {wave}",
        "metrics": {
            "wave": wave,
            "contacted": contacted,
            "accepted": accepted,
            "declined": declined,
            "status": "Donor Accepted" if accepted > 0 else "Broadcasting"
        },
        "confirmed_donor": active_donor_summary or None
    }

    return {
        "card": card_payload,
        "text_fallback": text_fallback
    }


def build_backup_inventory_card(facilities: List[FacilityStock], blood_type: str) -> Dict[str, Any]:
    """
    Builds a summary card of nearby hospital blood banks and backup stocks.
    """
    lines = [
        f"🏥 **Nearby Blood Banks & Backup Stock ({blood_type})**:",
        ""
    ]
    items = []
    for f in facilities[:4]:
        units = f.stock.get(blood_type, 0)
        units_label = f"🟢 {units} units" if units > 0 else "🔴 0 units"
        lines.append(f"• **{f.name}** ({f.distance_km:.1f} km away): {units_label} | Phone: `{f.phone}`")
        items.append({
            "name": f.name,
            "distance_km": f.distance_km,
            "stock_units": units,
            "phone": f.phone,
            "last_updated": f.last_updated
        })

    lines.append("\n*(Hospital stock data timestamped for demo verification)*")
    text_fallback = "\n".join(lines)

    return {
        "card": {
            "type": "backup_inventory",
            "title": f"Nearby Blood Banks Stock ({blood_type})",
            "facilities": items
        },
        "text_fallback": text_fallback
    }
