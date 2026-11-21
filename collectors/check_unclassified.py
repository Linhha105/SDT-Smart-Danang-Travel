
import json
from collections import Counter

INPUT_FILE = "data/processed/osm_places_danang_old_land.json"
CLASSIFIED_FILE = "data/processed/osm_places_categorized.json"

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    original = json.load(file)

with open(CLASSIFIED_FILE, "r", encoding="utf-8") as file:
    categorized = json.load(file)

classified_ids = {
    (poi.get("osm_type"), poi.get("osm_id"))
    for poi in categorized
}

unclassified = [
    poi for poi in original
    if (poi.get("osm_type"), poi.get("osm_id"))
    not in classified_ids
]

print("========== POI CHUA PHAN LOAI ==========")
print("Tong:", len(unclassified))

for poi in unclassified:
    print({
        "osm_id": poi.get("osm_id"),
        "osm_type": poi.get("osm_type"),
        "name": poi.get("name"),
        "amenity": poi.get("amenity"),
        "tourism": poi.get("tourism"),
        "natural": poi.get("natural"),
        "shop": poi.get("shop")
    })

print("\n========== NHOM PHU ==========")

secondary_counter = Counter(
    category
    for poi in categorized
    for category in poi.get("category_secondary", [])
)

print("Tong POI co nhom phu:",
      sum(bool(poi.get("category_secondary")) for poi in categorized))

for category, count in secondary_counter.most_common():
    print(category, ":", count)
