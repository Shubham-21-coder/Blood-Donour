"""
Unit Tests for Intent Understanding & Parsing (F1, F2, F3, F4)
"""

import pytest
from core.intent import parse_intent_deterministic, detect_language


def test_complete_intent_extraction_english():
    text = "Need 2 units of O+ at SMS Hospital, Jaipur, urgent"
    intent = parse_intent_deterministic(text)
    assert intent.blood_type == "O+"
    assert intent.units == 2
    assert "SMS Hospital" in intent.hospital
    assert intent.urgency in ["URGENT", "CRITICAL"]
    assert intent.language == "en"
    assert len(intent.missing_fields) == 0
    assert intent.clarifying_question is None


def test_complete_intent_extraction_hindi():
    text = "एसएमएस अस्पताल जयपुर में 2 यूनिट ओ पॉजिटिव की तुरंत जरूरत है"
    intent = parse_intent_deterministic(text)
    assert intent.blood_type == "O+"
    assert intent.units == 2
    assert "SMS Hospital" in intent.hospital or "एसएमएस" in text
    assert intent.language == "hi"
    assert len(intent.missing_fields) == 0


def test_missing_units_clarification_f3():
    # Only blood type and hospital provided
    text = "Urgent O- blood needed at Fortis Hospital Jaipur"
    intent = parse_intent_deterministic(text)
    assert intent.blood_type == "O-"
    assert intent.units is None
    assert intent.missing_fields == ["units"]
    assert intent.clarifying_question is not None
    assert "units" in intent.clarifying_question.lower()


def test_missing_blood_type_clarification_f3():
    text = "Need 3 units urgently at SMS Hospital"
    intent = parse_intent_deterministic(text)
    assert intent.units == 3
    assert intent.blood_type is None
    assert intent.missing_fields == ["blood_type"]
    assert intent.clarifying_question is not None
    assert "blood" in intent.clarifying_question.lower()


def test_units_validation_boundary():
    # Valid 1 to 10
    intent_valid = parse_intent_deterministic("Need 10 units of A+ blood at SMS Hospital")
    assert intent_valid.units == 10

    # Over 10 is rejected
    intent_invalid = parse_intent_deterministic("Need 25 units of A+ blood at SMS Hospital")
    # Should not accept 25 as units
    assert intent_invalid.units != 25
