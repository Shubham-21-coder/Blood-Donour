"""
LifeLink: Clinical Donor Eligibility Engine
Deterministic rules following National Blood Transfusion Council (NBTC, India) guidelines.
Never decided by the LLM.
"""

from datetime import datetime, date
from typing import Tuple, Optional
from core.models import Donor

MIN_AGE = 18
MAX_AGE = 65
MIN_DONATION_INTERVAL_DAYS_MALE = 90    # ~3 months
MIN_DONATION_INTERVAL_DAYS_FEMALE = 120  # ~4 months
DAILY_ALERT_CAP = 3                     # Max times a donor can be notified in a single day


def is_donor_eligible(donor: Donor, as_of_date: Optional[date] = None) -> Tuple[bool, Optional[str]]:
    """
    Evaluate strict eligibility of a donor:
    1. Active / available now flag
    2. Age within NBTC guidelines [18, 65]
    3. Minimum donation interval elapsed since last donation (90 days for men, 120 days for women)
    4. Anti-spam alert cap not exceeded today
    """
    if as_of_date is None:
        as_of_date = datetime.utcnow().date()

    # 1. Availability check
    if not donor.is_available_now:
        return False, "Donor is marked currently unavailable"

    # 2. Anti-spam cap check
    if donor.alerts_today >= DAILY_ALERT_CAP:
        return False, f"Donor reached daily alert cap ({DAILY_ALERT_CAP} alerts)"

    # 3. Age verification
    if donor.age < MIN_AGE:
        return False, f"Donor age ({donor.age}) is below minimum eligible age ({MIN_AGE})"
    if donor.age > MAX_AGE:
        return False, f"Donor age ({donor.age}) is above maximum eligible age ({MAX_AGE})"

    # 4. Donation interval check
    if donor.last_donation_date:
        try:
            last_date = datetime.strptime(donor.last_donation_date, "%Y-%m-%d").date()
            days_elapsed = (as_of_date - last_date).days
            min_required = MIN_DONATION_INTERVAL_DAYS_FEMALE if donor.gender.upper() == "F" else MIN_DONATION_INTERVAL_DAYS_MALE
            if days_elapsed < min_required:
                days_left = min_required - days_elapsed
                return False, f"Donation interval not met: {days_elapsed} days elapsed, {min_required} required (wait {days_left} more days)"
        except ValueError:
            return False, "Invalid last donation date format"

    return True, None
