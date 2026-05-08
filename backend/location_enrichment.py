import os
import requests
from typing import Optional, Dict

AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY")


def geocode_location(location: Optional[str]) -> Optional[Dict]:
    if not location:
        return None
    
    url = "https://atlas.microsoft.com/geocode"

    params = {
        "api-version": "2026-01-01",
        "query": location,
        "subscription-key": AZURE_MAPS_KEY,
        "limit": 1
    }
    
    response = requests.get(url, params=params, timeout=100)
    response.raise_for_status()

    data = response.json()
    features = data.get("features",[])
    if not features:
        return None
    
    feature = features[0]
    properties = feature.get("properties", {})
    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates", {})

    longitude = coordinates[0] if len(coordinates)>0 else None
    latitude = coordinates[1] if len(coordinates)>1 else None

    return {
        "raw_location":location,
        "formatted_address": properties.get("formattedAddress"),
        "latitude": latitude,
        "longitude": longitude,
        "confidence": properties.get("confidence"),
        "match_type": properties.get("type")
    }
