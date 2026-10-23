"""
Unit Tests for Blood Compatibility Engine
"""

import pytest
from core.compatibility import (
    can_donate,
    get_compatible_donor_types,
    normalize_blood_type
)


def test_normalize_blood_type():
    assert normalize_blood_type("o+") == "O+"
    assert normalize_blood_type("O positive") == "O+"
    assert normalize_blood_type("O +ve") == "O+"
    assert normalize_blood_type("B-ve") == "B-"
    assert normalize_blood_type("ab negative") == "AB-"
    assert normalize_blood_type("invalid_type") is None


def test_universal_donor_o_negative():
    recipients = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
    for r in recipients:
        assert can_donate("O-", r), f"O- should donate to {r}"


def test_universal_recipient_ab_positive():
    donors = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
    for d in donors:
        assert can_donate(d, "AB+"), f"{d} should donate to AB+"


def test_o_positive_compatibility():
    # O+ can donate to O+, A+, B+, AB+
    assert can_donate("O+", "O+") is True
    assert can_donate("O+", "A+") is True
    assert can_donate("O+", "B+") is True
    assert can_donate("O+", "AB+") is True
    # O+ cannot donate to negative Rh
    assert can_donate("O+", "O-") is False
    assert can_donate("O+", "A-") is False
    assert can_donate("O+", "B-") is False


def test_recipient_donor_resolution():
    # Recipient needing O+ can receive from O- and O+
    o_pos_donors = get_compatible_donor_types("O+")
    assert set(o_pos_donors) == {"O-", "O+"}

    # Recipient needing O- can only receive from O-
    o_neg_donors = get_compatible_donor_types("O-")
    assert set(o_neg_donors) == {"O-"}

    # Recipient needing A+ can receive from O-, O+, A-, A+
    a_pos_donors = get_compatible_donor_types("A+")
    assert set(a_pos_donors) == {"O-", "O+", "A-", "A+"}
