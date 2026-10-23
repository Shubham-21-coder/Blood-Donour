"""
LifeLink: Core Data Models and uAgents Message Protocol Models
Strict Pydantic models for request validation, donor data, inventory stock, and agent communication.
"""

from datetime import datetime, date, timezone
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator
from uagents import Model

# Blood types supported
BloodType = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
UrgencyLevel = Literal["CRITICAL", "URGENT", "NORMAL"]
VerificationTier = Literal["blood_bank_confirmed", "id_verified", "phone_verified"]
DonorResponseStatus = Literal["pending", "accepted", "declined", "unresponsive"]


class BloodRequestIntent(BaseModel):
    """Parsed blood request from user conversation."""
    blood_type: Optional[BloodType] = None
    units: Optional[int] = Field(default=None, ge=1, le=10)
    urgency: UrgencyLevel = "URGENT"
    hospital: Optional[str] = None
    city: Optional[str] = "Jaipur"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: str = "en"
    raw_text: str = ""
    missing_fields: List[str] = Field(default_factory=list)
    clarifying_question: Optional[str] = None

    @field_validator("units")
    @classmethod
    def validate_units(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 10):
            raise ValueError("Requested blood units must be between 1 and 10.")
        return v


class Donor(BaseModel):
    """Synthetic registered blood donor model."""
    id: str
    name: str
    blood_type: BloodType
    phone: str
    latitude: float
    longitude: float
    distance_km: Optional[float] = None
    last_donation_date: str  # YYYY-MM-DD
    gender: Literal["M", "F", "Other"] = "M"
    age: int = Field(ge=18, le=65)
    is_available_now: bool = True
    reliability_score: float = Field(default=0.90, ge=0.0, le=1.0)
    verification_tier: VerificationTier = "phone_verified"
    response_status: DonorResponseStatus = "pending"
    eta_minutes: Optional[int] = None
    alerts_today: int = 0

    @property
    def masked_phone(self) -> str:
        """Masked phone number for privacy preservation."""
        p = self.phone.replace(" ", "")
        if len(p) >= 10:
            return f"{p[:5]}****{p[-2:]}"
        return "+91 98*** **421"


class FacilityStock(BaseModel):
    """Hospital or Blood Bank facility with inventory stock levels."""
    id: str
    name: str
    facility_type: Literal["hospital", "blood_bank", "clinic"]
    address: str
    latitude: float
    longitude: float
    distance_km: float = 0.0
    stock: Dict[str, int] = Field(default_factory=dict)
    phone: str = "+91 141 2560291"
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    is_demo_data: bool = True


# ==========================================================
# uAgents Typed Inter-Agent Message Protocols (Model)
# ==========================================================

class InventoryCheckRequest(Model):
    """Request from Coordinator to Inventory Agent."""
    request_id: str
    latitude: float
    longitude: float
    hospital_name: Optional[str] = None
    blood_type: str
    radius_km: float = 15.0


class InventoryCheckResponse(Model):
    """Response from Inventory Agent to Coordinator."""
    request_id: str
    facilities: List[Dict[str, Any]]
    search_radius_km: float
    compatible_units_total: int
    status: str
    timestamp: str


class DonorMatchQuery(Model):
    """Request from Coordinator to Donor Outreach Agent to rank eligible donors."""
    request_id: str
    blood_type: str
    units: int
    latitude: float
    longitude: float
    urgency: str = "URGENT"
    max_donors: int = 10


class DonorMatchResult(Model):
    """Response from Donor Outreach Agent with ranked donors."""
    request_id: str
    blood_type: str
    compatible_types: List[str]
    matched_donors: List[Dict[str, Any]]
    total_eligible: int
    status: str


class BroadcastAlertRequest(Model):
    """Request to initiate alert wave dispatch to matched donors."""
    request_id: str
    hospital_name: str
    blood_type: str
    units: int
    urgency: str
    donor_ids: List[str]
    wave_number: int = 1


class BroadcastAlertStatus(Model):
    """Update streamed during broadcast wave."""
    request_id: str
    wave_number: int
    contacted_count: int
    accepted_count: int
    declined_count: int
    donors_status: List[Dict[str, Any]]
    status_summary: str
    is_wave_complete: bool


class MaskedContactRequest(Model):
    """Request to securely retrieve masked contact for an accepted donor."""
    request_id: str
    donor_id: str


class MaskedContactResponse(Model):
    """Safe relay contact info released only after donor acceptance."""
    request_id: str
    donor_id: str
    donor_name: str
    masked_phone: str
    call_relay_token: str
    eta_minutes: int
    unlocked: bool
    notice: str
