"""
LifeLink: Multi-Factor Donor Ranking Engine
Ranks eligible donors by composite score: Distance, Reliability, Availability, Verification Tier.
"""

from typing import List, Dict, Any
from core.models import Donor

TIER_MULTIPLIERS = {
    "blood_bank_confirmed": 1.25,
    "id_verified": 1.10,
    "phone_verified": 1.00,
}

TIER_BADGES = {
    "blood_bank_confirmed": "🏥 Blood-Bank Confirmed",
    "id_verified": "🪪 Govt ID Verified",
    "phone_verified": "📱 Phone Verified",
}


def calculate_donor_score(donor: Donor, max_radius_km: float = 25.0) -> float:
    """
    Calculate composite priority score for donor ranking.
    Closer distance, higher past reliability, and stronger verification yield higher scores.
    """
    dist = donor.distance_km if donor.distance_km is not None else 10.0
    # Distance decay score [0.0 - 1.0]
    distance_score = 1.0 / (1.0 + (dist / 8.0))

    # Reliability factor [0.0 - 1.0]
    reliability = max(0.1, min(1.0, donor.reliability_score))

    # Availability factor
    availability = 1.0 if donor.is_available_now else 0.2

    # Verification tier multiplier [1.0 - 1.25]
    tier_mult = TIER_MULTIPLIERS.get(donor.verification_tier, 1.0)

    # Composite weighted formula
    # 45% distance, 30% reliability, 15% verification, 10% availability
    raw_score = (
        (0.45 * distance_score) +
        (0.30 * reliability) +
        (0.15 * (tier_mult - 1.0) * 4.0) +  # scaled 0.0 to 1.0
        (0.10 * availability)
    )

    return round(raw_score * tier_mult * 100, 2)


def rank_donors(donors: List[Donor], max_radius_km: float = 25.0) -> List[Dict[str, Any]]:
    """
    Rank eligible donors and attach score, badges, and estimated response metrics.
    """
    ranked = []
    for d in donors:
        score = calculate_donor_score(d, max_radius_km)
        badge = TIER_BADGES.get(d.verification_tier, "📱 Phone Verified")
        dist = round(d.distance_km, 1) if d.distance_km is not None else 5.0
        
        # Estimate ETA based on distance (approx 3 mins/km + 10 mins prep)
        est_eta = int(10 + (dist * 3.2))

        ranked.append({
            "donor": d,
            "score": score,
            "badge": badge,
            "distance_km": dist,
            "est_eta_minutes": est_eta,
        })

    # Sort descending by composite score, tie-break by distance
    ranked.sort(key=lambda item: (item["score"], -item["distance_km"]), reverse=True)
    return ranked
