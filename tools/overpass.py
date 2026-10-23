"""
LifeLink: Overpass API (OpenStreetMap) Facility Search
Queries live OSM Overpass API for hospitals, clinics, and blood donation centers.
Caches responses and provides reliable offline demo fallbacks.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.models import FacilityStock
from tools.geocode import haversine_distance

logger = logging.getLogger("lifelink.overpass")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "jaipur_facilities.json")

# Verified base facilities in Jaipur with baseline synthetic stock
BASELINE_FACILITIES = [
    {
        "id": "osm-hosp-001",
        "name": "Sawai Man Singh (SMS) Hospital Blood Bank",
        "facility_type": "blood_bank",
        "address": "Jawahar Lal Nehru Marg, Ashok Nagar, Jaipur",
        "latitude": 26.8973,
        "longitude": 75.8167,
        "phone": "+91 141 2560291",
        "stock": {"O+": 3, "O-": 0, "A+": 6, "A-": 1, "B+": 8, "B-": 2, "AB+": 4, "AB-": 0}
    },
    {
        "id": "osm-hosp-002",
        "name": "Santokba Durlabhji Memorial Hospital Blood Center",
        "facility_type": "hospital",
        "address": "Bhawani Singh Road, Near Rambagh Circle, Jaipur",
        "latitude": 26.8943,
        "longitude": 75.8075,
        "phone": "+91 141 2566251",
        "stock": {"O+": 2, "O-": 1, "A+": 4, "A-": 0, "B+": 5, "B-": 1, "AB+": 3, "AB-": 1}
    },
    {
        "id": "osm-hosp-003",
        "name": "Fortis Escorts Hospital Blood Bank",
        "facility_type": "hospital",
        "address": "Jawaharlal Nehru Marg, Malviya Nagar, Jaipur",
        "latitude": 26.8488,
        "longitude": 75.8037,
        "phone": "+91 141 2547000",
        "stock": {"O+": 1, "O-": 0, "A+": 5, "A-": 1, "B+": 6, "B-": 0, "AB+": 2, "AB-": 0}
    },
    {
        "id": "osm-hosp-004",
        "name": "Narayana Multispeciality Hospital Blood Bank",
        "facility_type": "hospital",
        "address": "Sector 28, Kumbha Marg, Pratap Nagar, Jaipur",
        "latitude": 26.8123,
        "longitude": 75.8245,
        "phone": "+91 141 7122222",
        "stock": {"O+": 0, "O-": 0, "A+": 3, "A-": 0, "B+": 4, "B-": 1, "AB+": 2, "AB-": 0}
    },
    {
        "id": "osm-hosp-005",
        "name": "Jaipur Rotary Blood Bank Center",
        "facility_type": "blood_bank",
        "address": "Bapu Nagar, Near Gandhi Nagar Railway Station, Jaipur",
        "latitude": 26.8850,
        "longitude": 75.8120,
        "phone": "+91 141 2701100",
        "stock": {"O+": 5, "O-": 2, "A+": 7, "A-": 2, "B+": 9, "B-": 3, "AB+": 4, "AB-": 1}
    }
]


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=3),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    reraise=False
)
async def query_overpass_api(latitude: float, longitude: float, radius_meters: int = 15000) -> Optional[List[Dict[str, Any]]]:
    """Execute live Overpass query for hospitals and clinics."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json][timeout:5];
    (
      node["amenity"="hospital"](around:{radius_meters},{latitude},{longitude});
      node["healthcare"="blood_donation"](around:{radius_meters},{latitude},{longitude});
      node["amenity"="clinic"](around:{radius_meters},{latitude},{longitude});
    );
    out body 15;
    """
    async with httpx.AsyncClient(timeout=6.0) as client:
        resp = await client.post(overpass_url, data={"data": overpass_query})
        if resp.status_code == 200:
            data = resp.json()
            elements = data.get("elements", [])
            facilities = []
            for el in elements:
                tags = el.get("tags", {})
                name = tags.get("name")
                if not name:
                    continue
                f_type = "blood_bank" if tags.get("healthcare") == "blood_donation" else "hospital"
                facilities.append({
                    "id": f"osm-{el.get('id')}",
                    "name": name,
                    "facility_type": f_type,
                    "address": tags.get("addr:street", "Jaipur, Rajasthan"),
                    "latitude": el.get("lat"),
                    "longitude": el.get("lon"),
                    "phone": tags.get("phone", "+91 141 2560291"),
                    "stock": {"O+": 2, "O-": 0, "A+": 3, "A-": 1, "B+": 4, "B-": 1, "AB+": 2, "AB-": 0}
                })
            return facilities
    return None


async def find_nearby_facilities(
    latitude: float,
    longitude: float,
    radius_km: float = 15.0,
    auto_expand: bool = True
) -> List[FacilityStock]:
    """
    Search nearby hospitals and blood banks.
    F7: Expands radius automatically if few results are found.
    """
    results: List[FacilityStock] = []
    
    # 1. Load baseline / cache
    cached_list = BASELINE_FACILITIES
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached_list = json.load(f)
        except Exception as e:
            logger.debug(f"Cache read error: {e}")

    # 2. Try live Overpass search
    try:
        live_data = await query_overpass_api(latitude, longitude, radius_meters=int(radius_km * 1000))
        if live_data and len(live_data) > 0:
            # Save to cache
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(live_data, f, indent=2)
            cached_list = live_data
    except Exception as e:
        logger.info(f"Overpass live query skipped or failed ({e}); using cached facilities.")

    # 3. Calculate distance and filter by radius
    for item in cached_list:
        dist = haversine_distance(latitude, longitude, item["latitude"], item["longitude"])
        if dist <= radius_km:
            facility = FacilityStock(
                id=item["id"],
                name=item["name"],
                facility_type=item.get("facility_type", "hospital"),
                address=item.get("address", "Jaipur"),
                latitude=item["latitude"],
                longitude=item["longitude"],
                distance_km=dist,
                stock=item.get("stock", {}),
                phone=item.get("phone", "+91 141 2560291")
            )
            results.append(facility)

    # 4. F7: Auto-expand radius if results are few (< 2)
    if len(results) < 2 and auto_expand and radius_km < 35.0:
        expanded_radius = min(35.0, radius_km + 15.0)
        logger.info(f"Few results ({len(results)}), auto-expanding radius to {expanded_radius} km")
        return await find_nearby_facilities(latitude, longitude, radius_km=expanded_radius, auto_expand=False)

    # Sort by nearest
    results.sort(key=lambda f: f.distance_km)
    return results
