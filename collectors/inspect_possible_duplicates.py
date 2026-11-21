
import json

REPORT_FILE = "data/processed/data_quality_report.json"
CATEGORIZED_FILE = "data/processed/osm_places_categorized.json"
UNCLASSIFIED_FILE = "data/processed/osm_places_unclassified.json"

with open(REPORT_FILE, "r", encoding="utf-8") as f:
    report = json.load(f)

with open(CATEGORIZED_FILE, "r", encoding="utf-8") as f:
    categorized = json.load(f)

with open(UNCLASSIFIED_FILE, "r", encoding="utf-8") as f:
    unclassified = json.load(f)

all_pois = categorized + unclassified

# Tao bang tra cuu theo dinh danh OSM
poi_lookup = {
    (poi.get("osm_type"), poi.get("osm_id")): poi
    for poi in all_pois
}

pairs = report["duplicate_detection"]["possible_duplicate_pairs"]

print("========== CHI TIET CAC CAP NGHI TRUNG ==========")
print("Tong so cap:", len(pairs))

for index, pair in enumerate(pairs, start=1):

    p1_summary = pair["poi_1"]
    p2_summary = pair["poi_2"]

    key1 = (p1_summary["osm_type"], p1_summary["osm_id"])
    key2 = (p2_summary["osm_type"], p2_summary["osm_id"])

    p1 = poi_lookup.get(key1)
    p2 = poi_lookup.get(key2)

    print(f"\n---------- CAP {index} ----------")
    print("Khoang cach:", pair["distance_m"], "m")

    for label, poi in [("POI 1", p1), ("POI 2", p2)]:

        print(f"\n{label}:")

        if poi is None:
            print("Khong tim thay ban ghi")
            continue

        print({
            "osm_id": poi.get("osm_id"),
            "osm_type": poi.get("osm_type"),
            "name": poi.get("name"),
            "latitude": poi.get("latitude"),
            "longitude": poi.get("longitude"),
            "tourism": poi.get("tourism"),
            "amenity": poi.get("amenity"),
            "natural": poi.get("natural"),
            "shop": poi.get("shop"),
            "category_primary": poi.get("category_primary"),
            "category_secondary": poi.get("category_secondary")
        })

print("\n========== HOAN TAT ==========")
