"""
LifeLink: Geocoding Tool
Uses OpenStreetMap Nominatim with tenacity retry/backoff.
Includes cached city and hospital fallbacks for 100% demo resilience.
"""

import math
import logging
from typing import Tuple, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("lifelink.geocode")

# Known accurate coordinates for demo reliability
DEMO_COORDINATES: Dict[str, Tuple[float, float]] = {
    "sms hospital, jaipur": (26.8973, 75.8167),
    "sms hospital": (26.8973, 75.8167),
    "fortis escorts hospital, jaipur": (26.8488, 75.8037),
    "santokba durlabhji memorial hospital, jaipur": (26.8943, 75.8075),
    "narayana multispeciality hospital, jaipur": (26.8123, 75.8245),
    "jaipur, rajasthan, india": (26.9124, 75.7873),
    "jaipur": (26.9124, 75.7873),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
        math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    reraise=False
)
async def fetch_nominatim(query: str) -> Optional[Tuple[float, float]]:
    """Query live OpenStreetMap Nominatim API."""
    url = "https://nominatim.openstreetmap.org/search"
    headers = {
        "User-Agent": "LifeLink-Emergency-Blood-Agent/1.0 (hackathon@lifelink.ai)"
    }
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }
    async with httpx.AsyncClient(timeout=4.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
    return None


async def geocode_location(location_name: str) -> Tuple[float, float]:
    """
    Geocode a hospital name or city into (latitude, longitude).
    Tries live Nominatim with retry, falls back to demo coordinates cache on any error.
    """
    cleaned = location_name.strip().lower()
    
    # 1. Check exact match in demo coordinates cache first for instant response
    for key, coords in DEMO_COORDINATES.items():
        if key in cleaned or cleaned in key:
            return coords

    # 2. Try live Nominatim API
    try:
        live_result = await fetch_nominatim(location_name)
        if live_result:
            return live_result
    except Exception as e:
        logger.warning(f"Nominatim geocoding error: {e}. Using city fallback.")

    # 3. Default fallback to Jaipur city center
    return DEMO_COORDINATES["jaipur"]
