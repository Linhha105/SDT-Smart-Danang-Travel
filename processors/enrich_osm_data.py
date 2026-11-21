
import json
import os
from datetime import datetime, timezone
from collections import Counter


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "osm_places_danang_old_full_categorized.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "osm_places_danang_old_enriched_osm.json"
)

REPORT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "osm_enrichment_report.json"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_value(value):
    """Chuẩn hóa giá trị text, giữ null nếu không có dữ liệu."""

    if value is None:
        return None

    if isinstance(value, (int, float)):
        value = str(value)

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if value.lower() in ["null", "none", "unknown", "n/a", "no"]:
        return None

    return value


def get_first_value(tags, keys):
    """Lấy giá trị đầu tiên có dữ liệu theo thứ tự ưu tiên."""

    for key in keys:
        value = clean_value(tags.get(key))

        if value:
            return value

    return None


def build_address(tags, existing_address=None):
    """Tạo địa chỉ từ các OSM address tags."""

    # Ưu tiên địa chỉ đã có
    address = clean_value(existing_address)

    if address:
        return address

    # Ưu tiên addr:full
    full_address = clean_value(tags.get("addr:full"))

    if full_address:
        return full_address

    parts = []

    house_number = clean_value(tags.get("addr:housenumber"))
    street = clean_value(tags.get("addr:street"))

    if house_number:
        parts.append(house_number)

    if street:
        parts.append(street)

    road_address = " ".join(parts).strip()

    if road_address:
        return road_address

    # Các thành phần địa chỉ hành chính
    administrative_fields = [
        "addr:hamlet",
        "addr:suburb",
        "addr:quarter",
        "addr:neighbourhood",
        "addr:city",
        "addr:district",
        "addr:province",
        "addr:postcode"
    ]

    administrative_parts = []

    for field in administrative_fields:
        value = clean_value(tags.get(field))

        if value and value not in administrative_parts:
            administrative_parts.append(value)

    if administrative_parts:
        return ", ".join(administrative_parts)

    return None


def extract_image_data(tags):
    """Trích xuất tham chiếu hình ảnh từ OSM."""

    image = get_first_value(
        tags,
        [
            "image",
            "contact:image"
        ]
    )

    wikimedia_commons = get_first_value(
        tags,
        [
            "wikimedia_commons"
        ]
    )

    return {
        "image": image,
        "wikimedia_commons": wikimedia_commons
    }


def enrich_poi(poi):
    """Làm giàu thông tin cho một POI."""

    tags = poi.get("raw_tags", {})

    if not isinstance(tags, dict):
        tags = {}

    # --------------------------------------------------------
    # ADDRESS
    # --------------------------------------------------------

    address = build_address(
        tags,
        poi.get("address")
    )

    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------

    phone = get_first_value(
        tags,
        [
            "phone",
            "contact:phone",
            "mobile",
            "contact:mobile"
        ]
    )

    website = get_first_value(
        tags,
        [
            "website",
            "contact:website",
            "url"
        ]
    )

    email = get_first_value(
        tags,
        [
            "email",
            "contact:email"
        ]
    )

    # --------------------------------------------------------
    # OPENING HOURS
    # --------------------------------------------------------

    opening_hours = get_first_value(
        tags,
        [
            "opening_hours",
            "opening_hours:covid19"
        ]
    )

    # --------------------------------------------------------
    # SOCIAL MEDIA
    # --------------------------------------------------------

    facebook = get_first_value(
        tags,
        [
            "contact:facebook",
            "facebook"
        ]
    )

    instagram = get_first_value(
        tags,
        [
            "contact:instagram",
            "instagram"
        ]
    )

    # --------------------------------------------------------
    # IMAGE REFERENCES
    # --------------------------------------------------------

    image_data = extract_image_data(tags)

    # --------------------------------------------------------
    # PRESERVE EXISTING DATA
    # --------------------------------------------------------

    enriched = dict(poi)

    enriched["address"] = address
    enriched["phone"] = phone
    enriched["website"] = website
    enriched["email"] = email
    enriched["opening_hours"] = opening_hours

    enriched["facebook"] = facebook
    enriched["instagram"] = instagram

    enriched["image"] = image_data["image"]
    enriched["wikimedia_commons"] = image_data["wikimedia_commons"]

    # Nguồn dữ liệu của module
    enriched["enrichment"] = {
        "source": "OpenStreetMap",
        "source_id": f'{poi.get("osm_type", "")}/{poi.get("osm_id", "")}',
        "processed_at": datetime.now(timezone.utc).isoformat()
    }

    return enriched


# ============================================================
# QUALITY STATISTICS
# ============================================================

def calculate_statistics(pois):

    total = len(pois)

    fields = [
        "address",
        "phone",
        "website",
        "email",
        "opening_hours",
        "facebook",
        "instagram",
        "image",
        "wikimedia_commons"
    ]

    statistics = {}

    for field in fields:

        available = sum(
            1 for poi in pois
            if clean_value(poi.get(field)) is not None
        )

        missing = total - available

        statistics[field] = {
            "available": available,
            "missing": missing,
            "coverage_percent": round(
                available / total * 100, 2
            ) if total else 0
        }

    category_counts = Counter(
        poi.get("category", "unknown")
        for poi in pois
    )

    return {
        "total_pois": total,
        "field_statistics": statistics,
        "category_statistics": dict(category_counts)
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("OSM POI ENRICHMENT")
    print("=" * 60)

    # --------------------------------------------------------
    # CHECK INPUT
    # --------------------------------------------------------

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Khong tim thay file dau vao: {INPUT_FILE}"
        )

    print("\nDang doc du lieu POI...")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        pois = json.load(file)

    if not isinstance(pois, list):
        raise ValueError(
            "Du lieu dau vao phai la JSON list."
        )

    print(f"Tong POI dau vao: {len(pois)}")

    # --------------------------------------------------------
    # ENRICHMENT
    # --------------------------------------------------------

    print("\nDang trich xuat thong tin tu OSM tags...")

    enriched_pois = []

    for index, poi in enumerate(pois, start=1):

        enriched = enrich_poi(poi)

        enriched_pois.append(enriched)

        if index % 500 == 0:
            print(
                f"Da xu ly: {index}/{len(pois)}"
            )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    report = calculate_statistics(enriched_pois)

    report["metadata"] = {
        "source": "OpenStreetMap",
        "input_file": os.path.relpath(INPUT_FILE, BASE_DIR),
        "output_file": os.path.relpath(OUTPUT_FILE, BASE_DIR),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "processing_method": "Extract and normalize OSM raw_tags",
        "original_pois_preserved": True
    }

    # --------------------------------------------------------
    # SAVE OUTPUT
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            enriched_pois,
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

    # --------------------------------------------------------
    # PRINT REPORT
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("KET QUA OSM ENRICHMENT")
    print("=" * 60)

    print(f"Tong POI: {report['total_pois']}")

    print("\n--- THONG KE THUOC TINH ---")

    for field, stats in report["field_statistics"].items():

        print(
            f"{field:20s}: "
            f"{stats['available']:5d} co du lieu | "
            f"{stats['missing']:5d} thieu | "
            f"{stats['coverage_percent']:6.2f}%"
        )

    print("\n--- PHAN BO DANH MUC ---")

    for category, count in report["category_statistics"].items():

        print(f"{category:20s}: {count}")

    print("\n--- FILE DA TAO ---")

    print(f"POI enriched: {OUTPUT_FILE}")
    print(f"Quality report: {REPORT_FILE}")

    print("\nTrang thai: THANH CONG")
    print("=" * 60)


if __name__ == "__main__":
    main()
