
import json
import os
import re
import csv
import unicodedata

from collections import Counter, defaultdict
from math import radians, sin, cos, sqrt, atan2

from shapely.geometry import shape, Point


# ==================================================
# 1. CAU HINH
# ==================================================

CATEGORIZED_FILE = (
    "data/processed/osm_places_danang_old_full_categorized.json"
)

UNCLASSIFIED_FILE = (
    "data/processed/osm_places_danang_old_full_unclassified.json"
)

BOUNDARY_FILE = (
    "data/raw/danang_old_boundary.geojson"
)

OUTPUT_DIR = "data/processed"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "data_quality_report.json"
)

DUPLICATE_FILE = os.path.join(
    OUTPUT_DIR,
    "possible_duplicate_pois.json"
)

MISSING_FILE = os.path.join(
    OUTPUT_DIR,
    "poi_missing_attributes.csv"
)

DUPLICATE_DISTANCE = 50  # meters

VALID_CATEGORIES = {
    "sightseeing",
    "hotel",
    "food_drink",
    "beach",
    "shopping",
    "entertainment"
}

OPTIONAL_FIELDS = [
    "address",
    "opening_hours",
    "website",
    "phone"
]


# ==================================================
# 2. HAM HO TRO
# ==================================================

def normalize_name(name):
    """Chuan hoa ten POI de so sanh."""

    if not name:
        return ""

    name = str(name).strip().lower()

    name = unicodedata.normalize("NFD", name)

    name = "".join(
        char
        for char in name
        if unicodedata.category(char) != "Mn"
    )

    name = re.sub(r"[^a-z0-9]+", " ", name)

    return " ".join(name.split())


def calculate_distance(lat1, lon1, lat2, lon2):
    """Tinh khoang cach Haversine, don vi met."""

    earth_radius = 6371000

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return 2 * earth_radius * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


def get_coordinates(poi):
    """Lay toa do neu hop le."""

    try:
        lat = float(poi.get("latitude"))
        lon = float(poi.get("longitude"))

        if not (-90 <= lat <= 90):
            return None

        if not (-180 <= lon <= 180):
            return None

        return lat, lon

    except (TypeError, ValueError):
        return None


def poi_identity(poi):
    """Tao dinh danh OSM cua POI."""

    return (
        poi.get("osm_type"),
        poi.get("osm_id")
    )


def poi_summary(poi):
    """Tao ban ghi tom tat de dua vao bao cao."""

    return {
        "osm_id": poi.get("osm_id"),
        "osm_type": poi.get("osm_type"),
        "name": poi.get("name"),
        "latitude": poi.get("latitude"),
        "longitude": poi.get("longitude"),
        "category": poi.get("category"),
        "category_name": poi.get("category_name"),
        "secondary_categories": poi.get(
            "secondary_categories", []
        ),
        "secondary_category_names": poi.get(
            "secondary_category_names", []
        )
    }


def is_missing(value):
    """Kiem tra gia tri bi thieu."""

    return (
        value is None
        or not str(value).strip()
    )


def load_json_list(file_path):
    """
    Doc JSON dang list hoac wrapper co truong places.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Khong tim thay file: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        places = data.get("places")

        if isinstance(places, list):
            return places

    raise ValueError(
        f"Khong doc duoc danh sach POI tu: {file_path}"
    )


# ==================================================
# 3. DOC RANH GIOI NGHIEN CUU
# ==================================================

def load_boundary(file_path):
    """
    Chi doc feature layer=final.
    Khong gop outer va inner vao polygon cuoi.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Khong tim thay file ranh gioi: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    geojson_type = data.get("type")

    if geojson_type == "FeatureCollection":

        features = data.get("features", [])

        final_features = [
            feature
            for feature in features
            if feature.get(
                "properties", {}
            ).get("layer") == "final"
        ]

        if len(final_features) != 1:
            raise ValueError(
                "Can co duy nhat mot feature layer=final. "
                f"Hien tai tim thay: {len(final_features)}"
            )

        geometry = final_features[0].get("geometry")

        if geometry is None:
            raise ValueError(
                "Feature layer=final khong co geometry."
            )

        boundary = shape(geometry)

    elif geojson_type == "Feature":

        properties = data.get("properties", {})

        if properties.get("layer") != "final":
            raise ValueError(
                "Feature khong phai layer=final."
            )

        if data.get("geometry") is None:
            raise ValueError(
                "Feature khong co geometry."
            )

        boundary = shape(data["geometry"])

    else:

        boundary = shape(data)

    if boundary.is_empty:
        raise ValueError(
            "Geometry ranh gioi rong."
        )

    if not boundary.is_valid:
        raise ValueError(
            "Geometry ranh gioi khong hop le."
        )

    if boundary.geom_type not in [
        "Polygon",
        "MultiPolygon"
    ]:
        raise ValueError(
            f"Geometry khong hop le: {boundary.geom_type}"
        )

    return boundary


# ==================================================
# 4. KIEM TRA TINH DAY DU
# ==================================================

def check_completeness(all_pois):

    missing_name = 0
    missing_coordinates = 0

    missing_fields = Counter()
    missing_samples = defaultdict(list)

    missing_records = []

    for poi in all_pois:

        summary = poi_summary(poi)

        missing_list = []

        # Kiem tra ten
        if is_missing(poi.get("name")):

            missing_name += 1
            missing_list.append("name")

            if len(missing_samples["name"]) < 20:
                missing_samples["name"].append(summary)

        # Kiem tra toa do
        if get_coordinates(poi) is None:

            missing_coordinates += 1
            missing_list.append("coordinates")

            if len(missing_samples["coordinates"]) < 20:
                missing_samples["coordinates"].append(summary)

        # Kiem tra cac thuoc tinh tuy chon
        for field in OPTIONAL_FIELDS:

            if is_missing(poi.get(field)):

                missing_fields[field] += 1
                missing_list.append(field)

                if len(missing_samples[field]) < 20:
                    missing_samples[field].append(summary)

        if missing_list:

            missing_records.append({
                **summary,
                "missing_fields": missing_list
            })

    return {
        "missing_name": missing_name,
        "missing_or_invalid_coordinates": missing_coordinates,
        "missing_optional_fields": dict(missing_fields),
        "samples": dict(missing_samples),
        "missing_records": missing_records
    }


# ==================================================
# 5. KIEM TRA DINH DANH OSM
# ==================================================

def check_missing_osm_identity(all_pois):
    """Phat hien POI thieu osm_type hoac osm_id."""

    missing_identity = []

    for poi in all_pois:

        if (
            is_missing(poi.get("osm_type"))
            or is_missing(poi.get("osm_id"))
        ):

            missing_identity.append(
                poi_summary(poi)
            )

    return missing_identity


def check_duplicate_ids(all_pois):
    """Phat hien cac dinh danh OSM bi trung."""

    identity_counter = Counter()

    for poi in all_pois:

        osm_type = poi.get("osm_type")
        osm_id = poi.get("osm_id")

        if (
            is_missing(osm_type)
            or is_missing(osm_id)
        ):
            continue

        identity_counter[
            (str(osm_type), str(osm_id))
        ] += 1

    duplicate_ids = [
        {
            "osm_type": identity[0],
            "osm_id": identity[1],
            "count": count
        }
        for identity, count in identity_counter.items()
        if count > 1
    ]

    return duplicate_ids


# ==================================================
# 6. PHAT HIEN POI NGHI TRUNG DIA DIEM
# ==================================================

def check_possible_duplicates(all_pois):

    name_groups = defaultdict(list)

    for poi in all_pois:

        normalized_name = normalize_name(
            poi.get("name")
        )

        if normalized_name:
            name_groups[normalized_name].append(poi)

    possible_duplicates = []

    for normalized_name, group in name_groups.items():

        if len(group) < 2:
            continue

        for i in range(len(group)):

            for j in range(i + 1, len(group)):

                poi1 = group[i]
                poi2 = group[j]

                if poi_identity(poi1) == poi_identity(poi2):
                    continue

                coord1 = get_coordinates(poi1)
                coord2 = get_coordinates(poi2)

                if coord1 is None or coord2 is None:
                    continue

                distance = calculate_distance(
                    coord1[0],
                    coord1[1],
                    coord2[0],
                    coord2[1]
                )

                if distance <= DUPLICATE_DISTANCE:

                    possible_duplicates.append({
                        "normalized_name": normalized_name,
                        "distance_m": round(distance, 2),
                        "poi_1": poi_summary(poi1),
                        "poi_2": poi_summary(poi2)
                    })

    return possible_duplicates


# ==================================================
# 7. KIEM TRA TOA DO VA RANH GIOI
# ==================================================

def check_boundary(all_pois, boundary):

    invalid_coordinates = []
    outside_boundary = []

    inside_boundary = 0
    boundary_edge = 0

    for poi in all_pois:

        coordinates = get_coordinates(poi)

        if coordinates is None:

            invalid_coordinates.append(
                poi_summary(poi)
            )

            continue

        lat, lon = coordinates

        # Shapely su dung thu tu X, Y = longitude, latitude
        point = Point(lon, lat)

        if boundary.contains(point):

            inside_boundary += 1

        elif boundary.touches(point):

            inside_boundary += 1
            boundary_edge += 1

        else:

            outside_boundary.append(
                poi_summary(poi)
            )

    return {
        "invalid_coordinates": invalid_coordinates,
        "inside_boundary": inside_boundary,
        "boundary_edge": boundary_edge,
        "outside_boundary": outside_boundary
    }


# ==================================================
# 8. KIEM TRA TINH NHAT QUAN PHAN LOAI
# ==================================================

def check_classification(categorized, unclassified):

    invalid_primary = []
    invalid_secondary = []
    missing_primary = []
    unclassified_has_category = []

    for poi in categorized:

        primary = poi.get("category")

        secondary = poi.get(
            "secondary_categories", []
        )

        # Kiem tra danh muc chinh
        if primary is None:

            missing_primary.append(
                poi_summary(poi)
            )

        elif primary not in VALID_CATEGORIES:

            invalid_primary.append(
                poi_summary(poi)
            )

        # Kiem tra kieu du lieu danh muc phu
        if not isinstance(secondary, list):

            invalid_secondary.append(
                poi_summary(poi)
            )

            continue

        # Kiem tra gia tri danh muc phu
        if any(
            category not in VALID_CATEGORIES
            for category in secondary
        ):

            invalid_secondary.append(
                poi_summary(poi)
            )

        # Danh muc chinh khong duoc trung danh muc phu
        if primary in secondary:

            invalid_secondary.append(
                poi_summary(poi)
            )

    # POI chua phan loai khong duoc co danh muc chinh
    for poi in unclassified:

        if poi.get("category") is not None:

            unclassified_has_category.append(
                poi_summary(poi)
            )

    return {
        "invalid_primary": invalid_primary,
        "invalid_secondary": invalid_secondary,
        "missing_primary": missing_primary,
        "unclassified_with_category": unclassified_has_category
    }


# ==================================================
# 9. THONG KE PHAN LOAI
# ==================================================

def get_category_statistics(categorized):

    primary_counter = Counter()
    secondary_counter = Counter()

    for poi in categorized:

        primary = poi.get("category")

        if primary is not None:
            primary_counter[primary] += 1

        secondary = poi.get(
            "secondary_categories", []
        )

        if isinstance(secondary, list):
            secondary_counter.update(secondary)

    return {
        "primary_category_counts": dict(primary_counter),
        "secondary_category_counts": dict(secondary_counter)
    }


# ==================================================
# 10. CHUONG TRINH CHINH
# ==================================================

def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Dang doc du lieu...")

    categorized = load_json_list(
        CATEGORIZED_FILE
    )

    unclassified = load_json_list(
        UNCLASSIFIED_FILE
    )

    boundary = load_boundary(
        BOUNDARY_FILE
    )

    all_pois = categorized + unclassified

    total = len(all_pois)

    if total == 0:
        raise ValueError(
            "Khong co POI de kiem tra."
        )

    print("\n========== DATA QUALITY ASSESSMENT ==========")

    print("Tong POI:", total)
    print("Da phan loai:", len(categorized))
    print("Chua phan loai:", len(unclassified))

    # --------------------------------------------------
    # 1. COMPLETENESS
    # --------------------------------------------------

    print("\nDang kiem tra tinh day du...")

    completeness = check_completeness(
        all_pois
    )

    print("\n--- 1. TINH DAY DU ---")

    print(
        "POI thieu ten:",
        completeness["missing_name"]
    )

    print(
        "POI thieu/toa do khong hop le:",
        completeness["missing_or_invalid_coordinates"]
    )

    for field in OPTIONAL_FIELDS:

        count = completeness[
            "missing_optional_fields"
        ].get(field, 0)

        ratio = count / total * 100

        print(
            f"Thieu {field}: {count} ({ratio:.2f}%)"
        )

    # --------------------------------------------------
    # 2. OSM ID
    # --------------------------------------------------

    print("\nDang kiem tra dinh danh OSM...")

    missing_identity = check_missing_osm_identity(
        all_pois
    )

    duplicate_ids = check_duplicate_ids(
        all_pois
    )

    print("\n--- 2. DINH DANH OSM ---")

    print(
        "POI thieu dinh danh OSM:",
        len(missing_identity)
    )

    print(
        "So nhom ID bi trung:",
        len(duplicate_ids)
    )

    # --------------------------------------------------
    # 3. POSSIBLE DUPLICATES
    # --------------------------------------------------

    print("\nDang tim POI nghi trung...")

    possible_duplicates = check_possible_duplicates(
        all_pois
    )

    print("\n--- 3. NGHI TRUNG DIA DIEM ---")

    print(
        "So cap nghi trung trong ban kinh",
        DUPLICATE_DISTANCE,
        "m:",
        len(possible_duplicates)
    )

    for item in possible_duplicates[:20]:

        print(
            item["poi_1"]["name"],
            "<->",
            item["poi_2"]["name"],
            "|",
            item["distance_m"],
            "m"
        )

    # --------------------------------------------------
    # 4. BOUNDARY VALIDATION
    # --------------------------------------------------

    print("\nDang kiem tra ranh gioi...")

    boundary_result = check_boundary(
        all_pois,
        boundary
    )

    print("\n--- 4. TINH HOP LE TOA DO ---")

    print(
        "Toa do khong hop le:",
        len(boundary_result["invalid_coordinates"])
    )

    print(
        "POI nam trong ranh gioi:",
        boundary_result["inside_boundary"]
    )

    print(
        "POI nam tren bien ranh gioi:",
        boundary_result["boundary_edge"]
    )

    print(
        "POI nam ngoai ranh gioi:",
        len(boundary_result["outside_boundary"])
    )

    # --------------------------------------------------
    # 5. CLASSIFICATION CONSISTENCY
    # --------------------------------------------------

    print("\nDang kiem tra tinh nhat quan phan loai...")

    classification_result = check_classification(
        categorized,
        unclassified
    )

    print("\n--- 5. TINH NHAT QUAN PHAN LOAI ---")

    print(
        "Nhom chinh khong hop le:",
        len(classification_result["invalid_primary"])
    )

    print(
        "Nhom phu khong hop le:",
        len(classification_result["invalid_secondary"])
    )

    print(
        "Thieu nhom chinh:",
        len(classification_result["missing_primary"])
    )

    print(
        "Chua phan loai nhung co nhom chinh:",
        len(classification_result["unclassified_with_category"])
    )

    # --------------------------------------------------
    # 6. CATEGORY STATISTICS
    # --------------------------------------------------

    category_statistics = get_category_statistics(
        categorized
    )

    print("\n--- 6. THONG KE DANH MUC ---")

    for category, count in category_statistics[
        "primary_category_counts"
    ].items():

        ratio = count / len(categorized) * 100

        print(
            f"{category}: {count} ({ratio:.2f}%)"
        )

    # --------------------------------------------------
    # 7. DATASET INTEGRITY
    # --------------------------------------------------

    input_count = len(categorized) + len(unclassified)

    dataset_integrity = {
        "total_pois": total,
        "categorized_count": len(categorized),
        "unclassified_count": len(unclassified),
        "count_consistent": input_count == total,
        "all_retained_pois_classified": (
            len(categorized) > 0
            and len(unclassified) == 0
        )
    }

    # --------------------------------------------------
    # 8. BUILD REPORT
    # --------------------------------------------------

    report = {

        "total_pois": total,

        "input_files": {
            "categorized": CATEGORIZED_FILE,
            "unclassified": UNCLASSIFIED_FILE,
            "boundary": BOUNDARY_FILE,
            "boundary_layer_used": "final"
        },

        "dataset_integrity": dataset_integrity,

        "classification": {
            "categorized": len(categorized),
            "unclassified": len(unclassified),
            **category_statistics
        },

        "completeness": {
            key: value
            for key, value in completeness.items()
            if key != "missing_records"
        },

        "identity_validity": {
            "missing_osm_identity": missing_identity,
            "duplicate_osm_ids": duplicate_ids
        },

        "duplicate_detection": {
            "duplicate_distance_threshold_m": DUPLICATE_DISTANCE,
            "possible_duplicate_pairs": possible_duplicates
        },

        "coordinate_validity": boundary_result,

        "classification_consistency": classification_result
    }

    # --------------------------------------------------
    # 9. SAVE JSON REPORT
    # --------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------
    # 10. SAVE POSSIBLE DUPLICATES
    # --------------------------------------------------

    with open(
        DUPLICATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            possible_duplicates,
            file,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------
    # 11. SAVE MISSING ATTRIBUTES CSV
    # --------------------------------------------------

    with open(
        MISSING_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        fieldnames = [
            "osm_type",
            "osm_id",
            "name",
            "latitude",
            "longitude",
            "category",
            "missing_fields"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for record in completeness["missing_records"]:

            writer.writerow({
                "osm_type": record["osm_type"],
                "osm_id": record["osm_id"],
                "name": record["name"],
                "latitude": record["latitude"],
                "longitude": record["longitude"],
                "category": record["category"],
                "missing_fields": ", ".join(
                    record["missing_fields"]
                )
            })

    # --------------------------------------------------
    # 12. FINAL RESULT
    # --------------------------------------------------

    print("\n========== KET QUA ==========")

    print("Tong POI:", total)

    print(
        "Da phan loai:",
        len(categorized)
    )

    print(
        "Chua phan loai:",
        len(unclassified)
    )

    print(
        "POI thieu dinh danh OSM:",
        len(missing_identity)
    )

    print(
        "Nhom ID OSM bi trung:",
        len(duplicate_ids)
    )

    print(
        "Cap POI nghi trung:",
        len(possible_duplicates)
    )

    print(
        "POI ngoai ranh gioi:",
        len(boundary_result["outside_boundary"])
    )

    print(
        "Loi phan loai:",
        len(classification_result["invalid_primary"])
        + len(classification_result["invalid_secondary"])
        + len(classification_result["missing_primary"])
        + len(classification_result["unclassified_with_category"])
    )

    print("\nCac file da tao:")

    print("-", OUTPUT_FILE)
    print("-", DUPLICATE_FILE)
    print("-", MISSING_FILE)

    print("\nHoan thanh kiem tra chat luong du lieu.")


if __name__ == "__main__":
    main()
