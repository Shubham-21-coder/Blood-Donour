"""
Unit Tests for NBTC Clinical Donor Eligibility Engine
"""

from datetime import date
import pytest
from core.models import Donor
from core.eligibility import is_donor_eligible


def test_eligible_male_donor():
    donor = Donor(
        id="test-001",
        name="Eligible Male",
        blood_type="O+",
        phone="+91 98290 11111",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-06-01",
        gender="M",
        age=30,
        is_available_now=True
    )
    # Target date: 2026-10-23 (144 days elapsed > 90 required)
    eligible, reason = is_donor_eligible(donor, as_of_date=date(2026, 10, 23))
    assert eligible is True
    assert reason is None


def test_ineligible_male_recent_donation():
    donor = Donor(
        id="test-002",
        name="Recent Male Donor",
        blood_type="O+",
        phone="+91 98290 11112",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-09-15",
        gender="M",
        age=30,
        is_available_now=True
    )
    # Target date: 2026-10-23 (38 days elapsed < 90 required)
    eligible, reason = is_donor_eligible(donor, as_of_date=date(2026, 10, 23))
    assert eligible is False
    assert "Donation interval not met" in reason


def test_ineligible_female_interval_120_days():
    # Female donor who donated 100 days ago (eligible if male 90d, but ineligible for female 120d)
    donor = Donor(
        id="test-003",
        name="Female Donor",
        blood_type="A+",
        phone="+91 98290 11113",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-07-15",
        gender="F",
        age=28,
        is_available_now=True
    )
    # Target date: 2026-10-23 (100 days elapsed < 120 required)
    eligible, reason = is_donor_eligible(donor, as_of_date=date(2026, 10, 23))
    assert eligible is False
    assert "120 required" in reason


def test_ineligible_age_limits():
    # Below 18
    with pytest.raises(ValueError):
        Donor(
            id="test-underage",
            name="Underage",
            blood_type="O+",
            phone="+91 98290 11114",
            latitude=26.89,
            longitude=75.81,
            last_donation_date="2026-01-01",
            gender="M",
            age=16,
            is_available_now=True
        )


def test_unavailable_donor():
    donor = Donor(
        id="test-004",
        name="Unavailable Donor",
        blood_type="O+",
        phone="+91 98290 11115",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-01-01",
        gender="M",
        age=25,
        is_available_now=False
    )
    eligible, reason = is_donor_eligible(donor, as_of_date=date(2026, 10, 23))
    assert eligible is False
    assert "Donor is marked currently unavailable" in reason


def test_daily_alert_cap():
    donor = Donor(
        id="test-005",
        name="Capped Donor",
        blood_type="O+",
        phone="+91 98290 11116",
        latitude=26.89,
        longitude=75.81,
        last_donation_date="2026-01-01",
        gender="M",
        age=25,
        is_available_now=True,
        alerts_today=3
    )
    eligible, reason = is_donor_eligible(donor, as_of_date=date(2026, 10, 23))
    assert eligible is False
    assert "daily alert cap" in reason
