import os
import requests

AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY")

RESOURCE_QUERIES = {
    "medical":["hospital"],
    "fire":["fire station"],
    "crime": ["police station"],
    "accident":["hospital", "police station"]
}

def find_nearby_resources(latitude, longitude, emergency_type, radius=5000):
    queries = RESOURCE_QUERIES.get(emergency_type, ["hospital"])
    results = []

    for query in queries:
        url = "https://atlas.microsoft.com/search/poi/category/json"

        params = {
            "api-version": "1.0",
            "subscription-key": AZURE_MAPS_KEY,
            "query": query,
            "lat": latitude,
            "lon": longitude,
            "radius": radius,
            "limit": 5,
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        for item in data.get("results", []):
            position = item.get("position", {})
            poi = item.get("poi", {})
            address = item.get("address", {})


            results.append({
                "type": query,
                "name": poi.get("name"),
                "address": address.get("freeformAddress"),
                "latitude": position.get("lat"),
                "longitude": position.get("lon"),
                "distance_meters": item.get("dist"),
            })
    return results