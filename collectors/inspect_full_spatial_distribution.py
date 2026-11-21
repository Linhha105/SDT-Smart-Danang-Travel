
import json
from collections import Counter

INPUT_FILE = "data/processed/osm_places_danang_old_full_inside.json"


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    pois = data["places"]

    latitudes = [float(p["latitude"]) for p in pois]
    longitudes = [float(p["longitude"]) for p in pois]

    print("\n========== PHAM VI TOA DO POI ==========")
    print("Latitude min:", min(latitudes))
    print("Latitude max:", max(latitudes))
    print("Longitude min:", min(longitudes))
    print("Longitude max:", max(longitudes))

    # Chia khu vuc thanh cac o luoi 0.05 do
    grid = Counter()

    for poi in pois:
        lat = float(poi["latitude"])
        lon = float(poi["longitude"])

        cell_lat = round(lat / 0.05) * 0.05
        cell_lon = round(lon / 0.05) * 0.05

        grid[(cell_lat, cell_lon)] += 1

    print("\n========== PHAN BO THEO O LUOI ==========")
    print("So o luoi co POI:", len(grid))

    print("\n10 o luoi co nhieu POI nhat:")

    for (lat, lon), count in grid.most_common(10):
        print(
            f"Lat {lat:.2f}, Lon {lon:.2f}: {count} POI"
        )

    print("\n========================================")


if __name__ == "__main__":
    main()
