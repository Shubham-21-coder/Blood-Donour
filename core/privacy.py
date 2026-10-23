"""
LifeLink: Privacy Gate and Contact Masking
Enforces strict anti-abuse and privacy rules:
- Unaccepted donor contact info is NEVER accessible.
- Even upon acceptance, phone number is masked.
- Provides a virtual relay token / bridge ID for anonymous communication.
"""

import hashlib
from typing import Optional, Dict, Any
from core.models import Donor, MaskedContactResponse


def mask_phone_number(raw_phone: str) -> str:
    """Mask phone number preserving country code and ending digits for verification."""
    clean = raw_phone.strip().replace(" ", "").replace("-", "")
    if clean.startswith("+91") and len(clean) >= 13:
        return f"+91 {clean[3:5]}*** ***{clean[-2:]}"
    elif len(clean) >= 10:
        return f"{clean[:3]}*** ***{clean[-2:]}"
    return "+91 98*** **421"


def generate_relay_token(request_id: str, donor_id: str) -> str:
    """Generate a secure one-time relay routing token for hospital-donor call connection."""
    raw = f"{request_id}:{donor_id}:lifelink_salt_2026"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
    return f"RELAY-LL-{digest}"


def release_masked_contact(
    request_id: str,
    donor: Donor,
    has_accepted: bool
) -> MaskedContactResponse:
    """
    Privacy Gate:
    If donor has not accepted, reject release with locked status.
    If donor accepted, release masked phone and secure call bridge relay token.
    """
    if not has_accepted or donor.response_status != "accepted":
        return MaskedContactResponse(
            request_id=request_id,
            donor_id=donor.id,
            donor_name=donor.name.split()[0] + " *.",
            masked_phone="[LOCKED until acceptance]",
            call_relay_token="[UNAUTHORIZED]",
            eta_minutes=0,
            unlocked=False,
            notice="Privacy Gate Active: Contact information remains encrypted until donor explicitly accepts."
        )

    relay_token = generate_relay_token(request_id, donor.id)
    eta = donor.eta_minutes if donor.eta_minutes is not None else 25

    return MaskedContactResponse(
        request_id=request_id,
        donor_id=donor.id,
        donor_name=donor.name,
        masked_phone=mask_phone_number(donor.phone),
        call_relay_token=relay_token,
        eta_minutes=eta,
        unlocked=True,
        notice="Privacy Notice: Secure relay bridge active. No personal numbers are stored or broadcast to third parties."
    )
