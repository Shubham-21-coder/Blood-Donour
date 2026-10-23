"""
Unit Tests for Privacy Gate and Contact Masking (F14)
"""

import pytest
from core.models import Donor
from core.privacy import mask_phone_number, release_masked_contact, generate_relay_token


def test_phone_masking():
    assert mask_phone_number("+91 98290 14821") == "+91 98*** ***21"
    assert mask_phone_number("+91 94140 88219") == "+91 94*** ***19"


def test_privacy_gate_unaccepted_donor():
    donor = Donor(
        id="d-001",
        name="John Doe",
        blood_type="O+",
        phone="+91 98290 12345",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-01-01",
        age=30,
        response_status="pending"
    )
    result = release_masked_contact("req-123", donor, has_accepted=False)
    assert result.unlocked is False
    assert result.masked_phone == "[LOCKED until acceptance]"
    assert result.call_relay_token == "[UNAUTHORIZED]"


def test_privacy_gate_accepted_donor():
    donor = Donor(
        id="d-002",
        name="Rohan Mehra",
        blood_type="O+",
        phone="+91 98290 54321",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-01-01",
        age=28,
        response_status="accepted",
        eta_minutes=15
    )
    result = release_masked_contact("req-456", donor, has_accepted=True)
    assert result.unlocked is True
    assert result.masked_phone == "+91 98*** ***21"
    assert result.call_relay_token.startswith("RELAY-LL-")
    assert result.eta_minutes == 15
