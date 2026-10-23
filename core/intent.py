"""
LifeLink: Intent Understanding & Parsing
Extracts blood type, units (1-10), urgency, hospital, and location from free text.
Supports English and Hindi.
Asks at most one clarifying question at a time.
"""

import re
import json
import logging
from typing import Optional, Tuple
from core.models import BloodRequestIntent, BloodType, UrgencyLevel
from core.compatibility import normalize_blood_type
from core.llm import LLMClient

logger = logging.getLogger("lifelink.intent")

# Hindi blood keywords mapping
HINDI_BLOOD_MAPPING = {
    "ओ पॉजिटिव": "O+",
    "ओ नेगेटिव": "O-",
    "ए पॉजिटिव": "A+",
    "ए नेगेटिव": "A-",
    "बी पॉजिटिव": "B+",
    "बी नेगेटिव": "B-",
    "एबी पॉजिटिव": "AB+",
    "एबी नेगेटिव": "AB-",
}

# Hindi digits mapping
HINDI_NUMBERS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "१": 1, "२": 2, "३": 3, "४": 4, "५": 5, "६": 6, "७": 7, "८": 8, "९": 9, "१०": 10
}


def detect_language(text: str) -> str:
    """Detect if input text contains Devanagari (Hindi) script."""
    for char in text:
        if '\u0900' <= char <= '\u097F':
            return "hi"
    return "en"


def parse_intent_deterministic(text: str) -> BloodRequestIntent:
    """
    Deterministic regex/rule-based NLP parser.
    Zero hallucination, high speed, handles both English and Hindi.
    """
    lang = detect_language(text)
    lower = text.lower()
    
    # 1. Blood type extraction
    blood_type = None
    for hi_phrase, b_type in HINDI_BLOOD_MAPPING.items():
        if hi_phrase in text:
            blood_type = b_type
            break

    if not blood_type:
        match = re.search(r'\b(ab|a|b|o)\s*(\+|\-|\+\s*ve|\-\s*ve|positive|negative|pos|neg)\b', lower)
        if match:
            blood_type = normalize_blood_type(match.group(0))
        else:
            standalone = re.search(r'\b(A|B|AB|O)[\+\-]', text, re.IGNORECASE)
            if standalone:
                blood_type = normalize_blood_type(standalone.group(0))

    # 2. Units extraction (1 to 10)
    units = None
    for word, val in HINDI_NUMBERS.items():
        if word in text:
            units = val
            break

    if units is None:
        unit_match = re.search(r'\b([1-9]|10)\s*(?:unit|units|bottle|bottles|bag|bags|यूनिट)?\b', lower)
        if unit_match:
            try:
                candidate = int(unit_match.group(1))
                if 1 <= candidate <= 10:
                    units = candidate
            except ValueError:
                pass

    if units is None:
        if "unit" in lower or "यूनिट" in text:
            single = re.search(r'\b(\d+)\s*(?:unit|यूनिट)', text, re.IGNORECASE)
            if single:
                try:
                    c = int(single.group(1))
                    if 1 <= c <= 10:
                        units = c
                except ValueError:
                    pass

    # 3. Urgency detection
    urgency: UrgencyLevel = "URGENT"
    if any(k in lower for k in ["critical", "emergency", "immediately", "dying", "icu", "गंभीर", "आपातकालीन"]):
        urgency = "CRITICAL"
    elif any(k in lower for k in ["urgent", "asap", "soon", "fast", "जल्दी", "तुरंत"]):
        urgency = "URGENT"
    else:
        urgency = "NORMAL"

    # 4. Hospital & Location extraction
    hospital = None
    hosp_match = re.search(r'(?:at|in|hospital|अस्पताल)\s+([A-Za-z0-9\.\s]+?(?:hospital|clinic|center|centre|अस्पताल))', text, re.IGNORECASE)
    if hosp_match:
        hospital = hosp_match.group(1).strip()
    elif "sms hospital" in lower or "sms" in lower or "एसएमएस" in text:
        hospital = "SMS Hospital, Jaipur"
    elif "fortis" in lower:
        hospital = "Fortis Escorts Hospital, Jaipur"
    elif "santokba" in lower or "sdmh" in lower:
        hospital = "Santokba Durlabhji Memorial Hospital, Jaipur"
    elif "narayana" in lower:
        hospital = "Narayana Multispeciality Hospital, Jaipur"
    elif "hospital" in lower or "अस्पताल" in text:
        m = re.search(r'([A-Za-z\s]+hospital)', text, re.IGNORECASE)
        if m:
            hospital = m.group(1).strip().title()

    city = "Jaipur"
    if "jaipur" in lower or "जयपुर" in text:
        city = "Jaipur"

    missing = []
    if not blood_type:
        missing.append("blood_type")
    if units is None:
        missing.append("units")
    if not hospital:
        missing.append("hospital")

    # Formulate strictly at most ONE clarifying question
    clarifying_question = None
    if missing:
        field_to_ask = missing[0]
        if lang == "hi":
            if field_to_ask == "blood_type":
                clarifying_question = "कृपया आवश्यक रक्त समूह (Blood Type, जैसे O+, B+, A+) बताएं?"
            elif field_to_ask == "units":
                clarifying_question = "आपको रक्त की कितनी यूनिट (1 से 10) चाहिए?"
            elif field_to_ask == "hospital":
                clarifying_question = "रक्त किस अस्पताल या स्थान पर चाहिए?"
        else:
            if field_to_ask == "blood_type":
                clarifying_question = "Which blood type is needed (e.g. O+, A+, B-, AB+)? "
            elif field_to_ask == "units":
                clarifying_question = "How many units of blood are required (between 1 and 10)?"
            elif field_to_ask == "hospital":
                clarifying_question = "Which hospital or location is the patient admitted at?"

    return BloodRequestIntent(
        blood_type=blood_type,
        units=units,
        urgency=urgency,
        hospital=hospital,
        city=city,
        language=lang,
        raw_text=text,
        missing_fields=missing,
        clarifying_question=clarifying_question
    )


async def parse_blood_request(text: str, llm_client: Optional[LLMClient] = None) -> BloodRequestIntent:
    """
    Primary intent parser. Uses ASI:One LLM if available, otherwise deterministic parser.
    Ensures strict validation according to F1, F2, F3, F4.
    """
    if llm_client is None:
        llm_client = LLMClient()

    # 1. Deterministic extraction first for reliable grounding
    parsed = parse_intent_deterministic(text)

    # 2. If all required fields present, return immediately
    if not parsed.missing_fields and parsed.blood_type and parsed.units:
        return parsed

    # 3. If ASI:One LLM client is configured, enhance parsing without inventing missing units
    if llm_client and llm_client.is_configured:
        prompt = (
            f"Extract emergency blood request fields from: \"{text}\"\n"
            "Return valid JSON with keys: blood_type (e.g. O+, A-), units (integer 1-10, or null if not explicitly stated in the text), "
            "urgency (CRITICAL, URGENT, NORMAL), hospital (string), city (string), language ('en' or 'hi').\n"
            "CRITICAL: If the user did not specify the number of units, set units to null. Do not invent units."
        )
        try:
            resp = await llm_client.complete(
                prompt,
                system_prompt="You are a medical dispatch parsing engine. Return only JSON format without markdown ticks."
            )
            if resp:
                data = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group(0))
                bt = normalize_blood_type(data.get("blood_type"))
                u = data.get("units")
                
                # Only accept units if user text has a number or unit keyword
                has_number_in_text = bool(re.search(r'\b([1-9]|10)\b', text)) or any(w in text for w in HINDI_NUMBERS)
                if u and isinstance(u, int) and 1 <= u <= 10 and has_number_in_text:
                    parsed.units = u
                elif not has_number_in_text:
                    parsed.units = None

                if bt:
                    parsed.blood_type = bt
                if data.get("hospital"):
                    parsed.hospital = data.get("hospital")
                if data.get("urgency") in ["CRITICAL", "URGENT", "NORMAL"]:
                    parsed.urgency = data.get("urgency")
                
                # Recalculate missing
                parsed.missing_fields = []
                if not parsed.blood_type:
                    parsed.missing_fields.append("blood_type")
                if not parsed.units:
                    parsed.missing_fields.append("units")
                if not parsed.hospital:
                    parsed.missing_fields.append("hospital")
                
                if parsed.missing_fields:
                    f = parsed.missing_fields[0]
                    parsed.clarifying_question = (
                        f"Please specify the {f.replace('_', ' ')}." if parsed.language == "en" 
                        else f"कृपया {f} बताएं।"
                    )
                else:
                    parsed.clarifying_question = None
        except Exception as e:
            logger.debug(f"LLM parsing fallback to deterministic: {e}")

    return parsed
