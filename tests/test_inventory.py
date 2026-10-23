"""
Unit & Integration Tests for Inventory & Nearby Facilities (F5, F6, F7)
"""

import pytest
import asyncio
from tools.overpass import find_nearby_facilities
from tools.geocode import haversine_distance, geocode_location


@pytest.mark.asyncio
async def test_haversine_distance():
    # Distance between SMS Hospital and Santokba Durlabhji in Jaipur is ~1.0 km
    d = haversine_distance(26.8973, 75.8167, 26.8943, 75.8075)
    assert 0.5 <= d <= 2.0


@pytest.mark.asyncio
async def test_find_nearby_facilities_jaipur():
    # Jaipur center: 26.8973, 75.8167
    facilities = await find_nearby_facilities(26.8973, 75.8167, radius_km=15.0)
    assert len(facilities) >= 3
    # Check that facilities have stock and timestamps
    first = facilities[0]
    assert first.name is not None
    assert isinstance(first.stock, dict)
    assert first.is_demo_data is True


@pytest.mark.asyncio
async def test_auto_expand_radius_f7():
    # If search radius is tiny e.g. 0.05 km, auto-expand automatically increases radius
    facilities = await find_nearby_facilities(26.8973, 75.8167, radius_km=0.05, auto_expand=True)
    assert len(facilities) >= 2
