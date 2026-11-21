
import json
from collections import Counter

FILE_PATH = "data/processed/osm_places_danang_old_land.json"

with open(FILE_PATH, "r", encoding="utf-8") as file:
    pois = json.load(file)

TAG_FIELDS = [
    "tourism",
    "amenity",
    "natural",
    "shop"
]

print("========== THONG KE CHI TIET TAG OSM ==========")
print("Tong POI:", len(pois))

for field in TAG_FIELDS:

    counter = Counter(
        poi[field]
        for poi in pois
        if poi.get(field)
    )

    print(f"\n--- {field.upper()} ---")

    if not counter:
        print("Khong co du lieu.")
        continue

    for value, count in counter.most_common():
        print(f"{value}: {count}")

# Kiem tra cac ban ghi co nhieu tag cung luc
multi_tag = []

for poi in pois:

    active_tags = [
        field for field in TAG_FIELDS
        if poi.get(field)
    ]

    if len(active_tags) > 1:
        multi_tag.append({
            "osm_id": poi.get("osm_id"),
            "name": poi.get("name"),
            "osm_type": poi.get("osm_type"),
            "tags": {
                field: poi.get(field)
                for field in active_tags
            }
        })

print("\n========== KIEM TRA TAG CHONG CHEO ==========")
print("POI co tu 2 tag tro len:", len(multi_tag))

for item in multi_tag[:15]:
    print(item)

print("\n=============================================")
