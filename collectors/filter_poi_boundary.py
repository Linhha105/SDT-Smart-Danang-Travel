
import json
import os
import math
from collections import Counter
from datetime import datetime

from shapely.geometry import shape, Point


# ==========================================
# 1. KHAI BAO DUONG DAN
# ==========================================

POI_FILE = "data/raw/osm_places_danang_old_full.json"

BOUNDARY_FILE = "data/raw/danang_old_boundary.geojson"

OUTPUT_DIR = "data/processed"

INSIDE_FILE = os.path.join(
    OUTPUT_DIR,
    "osm_places_danang_old_full_inside.json"
)

OUTSIDE_FILE = os.path.join(
    OUTPUT_DIR,
    "osm_places_danang_old_full_outside.json"
)

REPORT_FILE = os.path.join(
    OUTPUT_DIR,
    "boundary_filter_report.json"
)


# ==========================================
# 2. DOC DU LIEU
# ==========================================

def load_data():

    with open(POI_FILE, "r", encoding="utf-8") as file:
        source_data = json.load(file)

    # Du lieu moi co cau truc wrapper:
    # metadata, statistics, places
    if isinstance(source_data, dict):
        pois = source_data.get("places", [])
    elif isinstance(source_data, list):
        # Ho tro ca cau truc du lieu cu
        pois = source_data
    else:
        raise ValueError("Cau truc file POI khong hop le.")

    if not isinstance(pois, list):
        raise ValueError("Danh sach places khong hop le.")

    with open(BOUNDARY_FILE, "r", encoding="utf-8") as file:
        boundary_data = json.load(file)

    # Ho tro FeatureCollection, Feature va Geometry
    if boundary_data.get("type") == "FeatureCollection":
        geometry_data = boundary_data["features"][0]["geometry"]

    elif boundary_data.get("type") == "Feature":
        geometry_data = boundary_data["geometry"]

    else:
        geometry_data = boundary_data

    boundary = shape(geometry_data)

    return source_data, pois, boundary


# ==========================================
# 3. KIEM TRA TOA DO
# ==========================================

def get_valid_coordinates(poi):

    lat = poi.get("latitude")
    lon = poi.get("longitude")

    try:
        lat = float(lat)
        lon = float(lon)

    except (TypeError, ValueError):
        return None

    if not math.isfinite(lat) or not math.isfinite(lon):
        return None

    if not (-90 <= lat <= 90):
        return None

    if not (-180 <= lon <= 180):
        return None

    return lat, lon


# ==========================================
# 4. PHAN LOAI NHOM TAG OSM
# ==========================================

def get_category(poi):

    tags = poi.get("raw_tags", {})

    # Uu tien raw_tags cua bo du lieu moi
    if tags:
        for key in [
            "tourism",
            "amenity",
            "natural",
            "shop",
            "leisure",
            "historic"
        ]:
            if key in tags:
                return key

    # Tuong thich voi bo du lieu cu
    for key in [
        "tourism",
        "amenity",
        "natural",
        "shop",
        "leisure",
        "historic"
    ]:
        if poi.get(key):
            return key

    return "other"


# ==========================================
# 5. LOC POI THEO RANH GIOI
# ==========================================

def filter_pois(pois, boundary):

    inside_pois = []
    outside_pois = []
    invalid_pois = []

    for poi in pois:

        coordinates = get_valid_coordinates(poi)

        if coordinates is None:
            invalid_pois.append(poi)
            continue

        lat, lon = coordinates

        # Shapely su dung thu tu (longitude, latitude)
        point = Point(lon, lat)

        if boundary.covers(point):
            inside_pois.append(poi)
        else:
            outside_pois.append(poi)

    return inside_pois, outside_pois, invalid_pois


# ==========================================
# 6. THONG KE KET QUA
# ==========================================

def build_report(original, inside, outside, invalid, boundary):

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": POI_FILE,
        "boundary_file": BOUNDARY_FILE,

        "total_input": len(original),
        "total_inside": len(inside),
        "total_outside": len(outside),
        "invalid_coordinates": len(invalid),

        "inside_rate_percent": round(
            len(inside) / len(original) * 100, 2
        ) if original else 0,

        "outside_rate_percent": round(
            len(outside) / len(original) * 100, 2
        ) if original else 0,

        "boundary_valid": boundary.is_valid,
        "boundary_bounds": list(boundary.bounds),

        "inside_by_osm_type": dict(Counter(
            poi.get("osm_type", "unknown")
            for poi in inside
        )),

        "inside_by_osm_tag": dict(Counter(
            get_category(poi)
            for poi in inside
        ))
    }

    return report


def print_statistics(original, inside, outside, invalid):

    print("\n========== KET QUA LOC POI ==========")

    print("Tong POI ban dau:", len(original))
    print("POI trong ranh gioi:", len(inside))
    print("POI ngoai ranh gioi:", len(outside))
    print("POI co toa do khong hop le:", len(invalid))

    total = len(original)

    if total > 0:
        print(
            "Ty le POI trong ranh gioi: "
            f"{len(inside) / total * 100:.2f}%"
        )

    print("\n========== PHAN BO THEO OSM TYPE ==========")

    print("Truoc khi loc:")

    for key, value in Counter(
        poi.get("osm_type", "unknown")
        for poi in original
    ).items():
        print(f"{key}: {value}")

    print("\nSau khi loc:")

    for key, value in Counter(
        poi.get("osm_type", "unknown")
        for poi in inside
    ).items():
        print(f"{key}: {value}")

    print("\n========== PHAN BO THEO NHOM TAG ==========")

    for key, value in Counter(
        get_category(poi)
        for poi in inside
    ).items():
        print(f"{key}: {value}")

    print("========================================")


# ==========================================
# 7. LUU DU LIEU
# ==========================================

def save_data(source_data, inside, outside, report):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Luu POI trong ranh gioi
    inside_data = {
        "metadata": source_data.get("metadata", {})
        if isinstance(source_data, dict) else {},

        "statistics": {
            "total_inside": len(inside)
        },

        "places": inside
    }

    # Luu POI ngoai ranh gioi
    outside_data = {
        "metadata": source_data.get("metadata", {})
        if isinstance(source_data, dict) else {},

        "statistics": {
            "total_outside": len(outside)
        },

        "places": outside
    }

    with open(INSIDE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            inside_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    with open(OUTSIDE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            outside_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\n========== LUU FILE ==========")
    print("POI trong ranh gioi:", INSIDE_FILE)
    print("POI ngoai ranh gioi:", OUTSIDE_FILE)
    print("Bao cao:", REPORT_FILE)
    print("==============================")


# ==========================================
# 8. MAIN
# ==========================================

def main():

    print("Bat dau loc POI theo ranh gioi Da Nang cu...")

    source_data, pois, boundary = load_data()

    print("Da doc POI:", len(pois))
    print("Polygon hop le:", boundary.is_valid)
    print("Polygon rong:", boundary.is_empty)
    print("Loai hinh hoc:", boundary.geom_type)
    print("Bounds:", boundary.bounds)

    if (
        not boundary.is_valid
        or boundary.is_empty
        or boundary.geom_type not in ["Polygon", "MultiPolygon"]
    ):
        print("Loi: Polygon khong hop le.")
        return

    inside, outside, invalid = filter_pois(
        pois,
        boundary
    )

    print_statistics(
        pois,
        inside,
        outside,
        invalid
    )

    report = build_report(
        pois,
        inside,
        outside,
        invalid,
        boundary
    )

    save_data(
        source_data,
        inside,
        outside,
        report
    )


if __name__ == "__main__":
    main()
