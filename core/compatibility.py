"""
LifeLink: Blood Compatibility Engine
Strict, deterministic clinical rules for red blood cell compatibility.
Never delegated to LLM hallucinations.
"""

from typing import List, Optional

# Recipient -> list of compatible donor blood types
# Who can give blood to this recipient?
COMPATIBLE_DONORS_FOR_RECIPIENT = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}

# Donor -> list of recipients who can safely receive this donor's blood
DONOR_CAN_GIVE_TO = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],  # Universal RBC donor
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],  # Universal RBC recipient only
}

ALL_BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


def normalize_blood_type(raw: Optional[str]) -> Optional[str]:
    """
    Standardize informal or multilingual representations of blood types:
    e.g. 'O positive', 'o +', 'O-ve', 'b+ve', 'AB negative' -> 'O+', 'O-', 'B+', 'AB-'
    """
    if not raw:
        return None
    s = raw.strip().upper()
    # Normalize words
    s = s.replace("POSITIVE", "+").replace("POS", "+").replace("+VE", "+")
    s = s.replace("NEGATIVE", "-").replace("NEG", "-").replace("-VE", "-")
    # Clean up whitespace
    s = s.replace(" ", "")
    # Check Hindi transliterations if present
    s = s.replace("पॉजिटिव", "+").replace("नेगेटिव", "-")

    if s in ALL_BLOOD_TYPES:
        return s
    return None


def get_compatible_donor_types(recipient_blood_type: str) -> List[str]:
    """Return all blood types that can safely donate to the given recipient blood type."""
    normalized = normalize_blood_type(recipient_blood_type)
    if not normalized:
        raise ValueError(f"Invalid blood type: {recipient_blood_type}")
    return COMPATIBLE_DONORS_FOR_RECIPIENT.get(normalized, [])


def can_donate(donor_blood_type: str, recipient_blood_type: str) -> bool:
    """Check if donor blood type is compatible with recipient blood type."""
    norm_donor = normalize_blood_type(donor_blood_type)
    norm_recip = normalize_blood_type(recipient_blood_type)
    if not norm_donor or not norm_recip:
        return False
    return norm_donor in COMPATIBLE_DONORS_FOR_RECIPIENT.get(norm_recip, [])
