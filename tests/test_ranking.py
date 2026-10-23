"""
Unit Tests for Multi-Factor Donor Ranking Engine
"""

import pytest
from core.models import Donor
from core.ranking import calculate_donor_score, rank_donors


def test_ranking_prefers_closer_distance():
    d_close = Donor(
        id="d-close",
        name="Close Donor",
        blood_type="O+",
        phone="+91 98290 11111",
        latitude=26.89,
        longitude=75.81,
        distance_km=1.0,
        last_donation_date="2026-01-01",
        age=30,
        reliability_score=0.90,
        verification_tier="phone_verified"
    )
    d_far = Donor(
        id="d-far",
        name="Far Donor",
        blood_type="O+",
        phone="+91 98290 11112",
        latitude=26.89,
        longitude=75.81,
        distance_km=15.0,
        last_donation_date="2026-01-01",
        age=30,
        reliability_score=0.90,
        verification_tier="phone_verified"
    )
    score_close = calculate_donor_score(d_close)
    score_far = calculate_donor_score(d_far)
    assert score_close > score_far


def test_ranking_prefers_higher_verification_tier():
    d_standard = Donor(
        id="d-std",
        name="Phone Verified Donor",
        blood_type="O+",
        phone="+91 98290 11111",
        latitude=26.89,
        longitude=75.81,
        distance_km=2.0,
        last_donation_date="2026-01-01",
        age=30,
        reliability_score=0.90,
        verification_tier="phone_verified"
    )
    d_hospital_verified = Donor(
        id="d-hosp",
        name="Blood Bank Confirmed Donor",
        blood_type="O+",
        phone="+91 98290 11112",
        latitude=26.89,
        longitude=75.81,
        distance_km=2.0,
        last_donation_date="2026-01-01",
        age=30,
        reliability_score=0.90,
        verification_tier="blood_bank_confirmed"
    )
    score_std = calculate_donor_score(d_standard)
    score_hosp = calculate_donor_score(d_hospital_verified)
    assert score_hosp > score_std


def test_rank_donors_sort_order():
    d1 = Donor(id="1", name="D1", blood_type="O+", phone="1234567890", latitude=0, longitude=0, distance_km=10.0, last_donation_date="2026-01-01", age=25, reliability_score=0.7)
    d2 = Donor(id="2", name="D2", blood_type="O+", phone="1234567891", latitude=0, longitude=0, distance_km=1.0, last_donation_date="2026-01-01", age=25, reliability_score=0.95, verification_tier="blood_bank_confirmed")
    ranked = rank_donors([d1, d2])
    assert ranked[0]["donor"].id == "2"
    assert ranked[0]["score"] > ranked[1]["score"]
