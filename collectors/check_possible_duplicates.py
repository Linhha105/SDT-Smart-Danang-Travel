
import json
from math import radians, sin, cos, sqrt, atan2

INPUT_FILE = "data/processed/osm_places_danang_old_land.json"

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

targets = [
    "HI4 COFFEE & WORKSPACE",
    "Hi4 coffee & workspace"
]

selected = [
    poi for poi in data
    if poi.get("name") in targets
]

print("========== KIEM TRA HI4 ==========")

for poi in selected:
    print({
        "osm_id": poi.get("osm_id"),
        "osm_type": poi.get("osm_type"),
        "name": poi.get("name"),
        "latitude": poi.get("latitude"),
        "longitude": poi.get("longitude"),
        "address": poi.get("address"),
        "amenity": poi.get("amenity")
    })

if len(selected) == 2:
    p1, p2 = selected

    lat1, lon1 = p1["latitude"], p1["longitude"]
    lat2, lon2 = p2["latitude"], p2["longitude"]

    earth_radius = 6371000

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    distance = 2 * earth_radius * atan2(
        sqrt(a), sqrt(1 - a)
    )

    print(f"\nKhoang cach giua hai POI: {distance:.2f} met")
else:
    print("\nKhong tim thay du 2 POI de so sanh.")
