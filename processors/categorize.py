
import json
from pathlib import Path
from collections import Counter


# ============================================================
# 1. CAU HINH DUONG DAN
# ============================================================

INPUT_FILE = Path(
    "data/processed/osm_places_danang_old_full_inside.json"
)

CATEGORIZED_FILE = Path(
    "data/processed/osm_places_danang_old_full_categorized.json"
)

UNCLASSIFIED_FILE = Path(
    "data/processed/osm_places_danang_old_full_unclassified.json"
)

EXCLUDED_FILE = Path(
    "data/processed/osm_places_danang_old_full_excluded.json"
)


# ============================================================
# 2. CAC DANH MUC
# ============================================================

CATEGORY_NAMES = {
    "sightseeing": "Tham quan",
    "hotel": "Khách sạn",
    "food_drink": "Ăn uống",
    "beach": "Bãi biển",
    "shopping": "Mua sắm",
    "entertainment": "Giải trí"
}

# Thu tu uu tien khi mot POI phu hop nhieu danh muc
CATEGORY_PRIORITY = [
    "beach",
    "hotel",
    "food_drink",
    "shopping",
    "entertainment",
    "sightseeing"
]


# ============================================================
# 3. CAC NHOM POI CAN LOAI
# ============================================================

EXCLUDED_TAGS = {
    ("amenity", "community_centre"),
    ("tourism", "information"),
    ("natural", "water")
}

EXCLUSION_REASONS = {
    ("amenity", "community_centre"):
        "Trung tâm sinh hoạt cộng đồng - không thuộc sáu danh mục",

    ("tourism", "information"):
        "Điểm cung cấp thông tin du lịch - không thuộc sáu danh mục",

    ("natural", "water"):
        "Đối tượng mặt nước tự nhiên - không thuộc sáu danh mục"
}


# ============================================================
# 4. HAM HO TRO DOC TAG
# ============================================================

def get_tag(poi, key):
    """
    Lay gia tri tag tu POI.

    Ho tro hai dang du lieu:
    - Tag nam truc tiep trong POI.
    - Tag nam trong raw_tags.
    """

    value = poi.get(key)

    if value is None:
        raw_tags = poi.get("raw_tags", {})

        if isinstance(raw_tags, dict):
            value = raw_tags.get(key)

    if value is None:
        return None

    return str(value).strip().lower()


def has_shop_tag(poi):
    """
    Kiem tra POI co tag shop hop le hay khong.
    """

    value = get_tag(poi, "shop")

    return value not in (None, "", "no", "none")


# ============================================================
# 5. KIEM TRA POI CAN LOAI
# ============================================================

def is_excluded_poi(poi):
    """
    Kiem tra POI co thuoc nhom can loai tru hay khong.
    """

    for key, value in EXCLUDED_TAGS:

        if get_tag(poi, key) == value:
            return True

    return False


def get_exclusion_reason(poi):
    """
    Tra ve ly do loai POI.
    """

    for key, value in EXCLUDED_TAGS:

        if get_tag(poi, key) == value:
            return EXCLUSION_REASONS[(key, value)]

    return None


# ============================================================
# 6. QUY TAC PHAN LOAI POI
# ============================================================

def get_matching_categories(poi):
    """
    Xac dinh tat ca danh muc ma POI phu hop.

    Mot POI co the phu hop nhieu danh muc.
    """

    categories = set()

    amenity = get_tag(poi, "amenity")
    tourism = get_tag(poi, "tourism")
    natural = get_tag(poi, "natural")
    leisure = get_tag(poi, "leisure")
    historic = get_tag(poi, "historic")

    # --------------------------------------------------------
    # 6.1. THAM QUAN
    # --------------------------------------------------------

    sightseeing_tourism = {
        "attraction",
        "museum",
        "viewpoint",
        "artwork",
        "gallery",
        "zoo"
    }

    sightseeing_natural = {
        "peak",
        "tree",
        "cave_entrance"
    }

    sightseeing_leisure = {
        "park",
        "garden"
    }

    sightseeing_historic = {
        "monument",
        "memorial",
        "ruins",
        "castle",
        "fort"
    }

    if tourism in sightseeing_tourism:
        categories.add("sightseeing")

    if natural in sightseeing_natural:
        categories.add("sightseeing")

    if leisure in sightseeing_leisure:
        categories.add("sightseeing")

    if historic in sightseeing_historic:
        categories.add("sightseeing")

    # Dia diem ton giao, tin nguong
    if amenity == "place_of_worship":
        categories.add("sightseeing")

    # --------------------------------------------------------
    # 6.2. KHACH SAN
    # --------------------------------------------------------

    hotel_tourism = {
        "hotel",
        "guest_house",
        "hostel",
        "motel",
        "apartment",
        "camp_site",
        "chalet"
    }

    if tourism in hotel_tourism:
        categories.add("hotel")

    # --------------------------------------------------------
    # 6.3. AN UONG
    # --------------------------------------------------------

    food_amenity = {
        "restaurant",
        "cafe",
        "fast_food",
        "ice_cream",
        "food_court",
        "internet_cafe",
        "biergarten"
    }

    if amenity in food_amenity:
        categories.add("food_drink")

    # --------------------------------------------------------
    # 6.4. BAI BIEN
    # --------------------------------------------------------

    if natural == "beach":
        categories.add("beach")

    # --------------------------------------------------------
    # 6.5. MUA SAM
    # --------------------------------------------------------

    if has_shop_tag(poi):
        categories.add("shopping")

    if amenity == "marketplace":
        categories.add("shopping")

    # --------------------------------------------------------
    # 6.6. GIAI TRI
    # --------------------------------------------------------

    entertainment_amenity = {
        "cinema",
        "bar",
        "pub",
        "nightclub",
        "casino",
        "theatre"
    }

    entertainment_tourism = {
        "theme_park"
    }

    entertainment_leisure = {
        "water_park",
        "amusement_arcade",
        "sports_centre",
        "stadium",
        "golf_course",
        "playground"
    }

    if amenity in entertainment_amenity:
        categories.add("entertainment")

    if tourism in entertainment_tourism:
        categories.add("entertainment")

    if leisure in entertainment_leisure:
        categories.add("entertainment")

    return categories


# ============================================================
# 7. XAC DINH DANH MUC CHINH VA DANH MUC PHU
# ============================================================

def classify_poi(poi):
    """
    Tra ve:
    - Danh muc chinh.
    - Danh sach danh muc phu.

    Neu khong phu hop danh muc nao, tra ve None.
    """

    matched_categories = get_matching_categories(poi)

    if not matched_categories:
        return None, []

    primary_category = None

    for category in CATEGORY_PRIORITY:

        if category in matched_categories:
            primary_category = category
            break

    secondary_categories = [
        category
        for category in CATEGORY_PRIORITY
        if category in matched_categories
        and category != primary_category
    ]

    return primary_category, secondary_categories


# ============================================================
# 8. DOC DU LIEU POI
# ============================================================

def load_pois(file_path):
    """
    Doc POI tu JSON.

    Ho tro:
    - JSON dang list.
    - JSON dang object co key 'places'.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay file dau vao: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        places = data.get("places", [])

        if isinstance(places, list):
            return places

    raise ValueError(
        "Cau truc JSON khong hop le. "
        "Can danh sach POI hoac object co key 'places'."
    )


# ============================================================
# 9. THONG KE TAG CHUA PHAN LOAI
# ============================================================

def get_unclassified_tag_statistics(unclassified):
    """
    Thong ke cac gia tri tag cua POI chua duoc phan loai.
    """

    tag_fields = [
        "amenity",
        "tourism",
        "natural",
        "shop",
        "leisure",
        "historic"
    ]

    statistics = {
        field: Counter()
        for field in tag_fields
    }

    for poi in unclassified:

        for field in tag_fields:

            value = get_tag(poi, field)

            if value:
                statistics[field][value] += 1

    return statistics


# ============================================================
# 10. LUU DU LIEU JSON
# ============================================================

def save_json(data, file_path):
    """
    Luu du lieu JSON voi ho tro tieng Viet.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(file_path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# 11. HAM CHINH
# ============================================================

def main():

    print("Dang doc du lieu POI...")

    pois = load_pois(INPUT_FILE)

    categorized = []
    unclassified = []
    excluded = []

    category_counts = Counter()
    secondary_counts = Counter()
    exclusion_counts = Counter()

    # --------------------------------------------------------
    # Phan loai va loc POI
    # --------------------------------------------------------

    for poi in pois:

        # Buoc 1: Kiem tra nhom POI can loai
        if is_excluded_poi(poi):

            reason = get_exclusion_reason(poi)

            excluded_poi = poi.copy()
            excluded_poi["exclusion_reason"] = reason

            excluded.append(excluded_poi)

            for key, value in EXCLUDED_TAGS:

                if get_tag(poi, key) == value:
                    exclusion_counts[(key, value)] += 1
                    break

            continue

        # Buoc 2: Phan loai POI khong thuoc nhom loai tru
        primary_category, secondary_categories = classify_poi(
            poi
        )

        # Buoc 3: POI khong phu hop danh muc nao
        if primary_category is None:

            unclassified.append(poi)
            continue

        # Buoc 4: Gan danh muc cho POI
        categorized_poi = poi.copy()

        categorized_poi["category"] = primary_category

        categorized_poi["category_name"] = CATEGORY_NAMES[
            primary_category
        ]

        categorized_poi["secondary_categories"] = (
            secondary_categories
        )

        categorized_poi["secondary_category_names"] = [
            CATEGORY_NAMES[category]
            for category in secondary_categories
        ]

        categorized.append(categorized_poi)

        category_counts[primary_category] += 1

        for category in secondary_categories:
            secondary_counts[category] += 1

    # --------------------------------------------------------
    # Luu ba tap du lieu
    # --------------------------------------------------------

    save_json(categorized, CATEGORIZED_FILE)
    save_json(unclassified, UNCLASSIFIED_FILE)
    save_json(excluded, EXCLUDED_FILE)

    # --------------------------------------------------------
    # Thong ke tong quan
    # --------------------------------------------------------

    total = len(pois)
    total_categorized = len(categorized)
    total_unclassified = len(unclassified)
    total_excluded = len(excluded)

    classification_rate = (
        total_categorized / total * 100
        if total > 0
        else 0
    )

    retention_rate = (
        total_categorized / total * 100
        if total > 0
        else 0
    )

    print("\n========== KET QUA XU LY POI ==========")

    print(f"Tong POI dau vao: {total}")
    print(f"POI duoc giu lai: {total_categorized}")
    print(f"POI bi loai: {total_excluded}")
    print(f"POI chua phan loai: {total_unclassified}")

    print(
        f"Ty le POI duoc phan loai tren dau vao: "
        f"{classification_rate:.2f}%"
    )

    print(
        f"Ty le giu lai tren dau vao: "
        f"{retention_rate:.2f}%"
    )

    # --------------------------------------------------------
    # Thong ke danh muc chinh
    # --------------------------------------------------------

    print("\n========== THONG KE DANH MUC CHINH ==========")

    for category in CATEGORY_PRIORITY:

        count = category_counts[category]

        percentage = (
            count / total_categorized * 100
            if total_categorized > 0
            else 0
        )

        print(
            f"{CATEGORY_NAMES[category]} "
            f"({category}): {count} "
            f"({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # Thong ke danh muc phu
    # --------------------------------------------------------

    print("\n========== THONG KE DANH MUC PHU ==========")

    if secondary_counts:

        for category in CATEGORY_PRIORITY:

            count = secondary_counts[category]

            if count > 0:
                print(
                    f"{CATEGORY_NAMES[category]} "
                    f"({category}): {count}"
                )

    else:
        print("Khong co POI nao co danh muc phu.")

    # --------------------------------------------------------
    # Thong ke POI bi loai
    # --------------------------------------------------------

    print("\n========== THONG KE POI BI LOAI ==========")

    if exclusion_counts:

        for (key, value), count in exclusion_counts.items():

            print(
                f"{key}={value}: {count}"
            )

    else:
        print("Khong co POI nao bi loai.")

    # --------------------------------------------------------
    # Thong ke POI chua phan loai
    # --------------------------------------------------------

    print("\n========== POI CHUA PHAN LOAI ==========")

    if unclassified:

        tag_statistics = get_unclassified_tag_statistics(
            unclassified
        )

        for field, counter in tag_statistics.items():

            if counter:

                print(f"\n{field}:")

                for tag_value, count in counter.most_common():

                    print(f"  {tag_value}: {count}")

    else:
        print("Khong con POI chua phan loai.")

    # --------------------------------------------------------
    # Kiem tra tinh toan ven
    # --------------------------------------------------------

    print("\n========== KIEM TRA DU LIEU ==========")

    processed_total = (
        total_categorized
        + total_unclassified
        + total_excluded
    )

    print(f"Tong dau vao: {total}")
    print(f"Tong dau ra: {processed_total}")

    if total == processed_total:
        print("Kiem tra: THANH CONG - Khong that thoat POI.")
    else:
        print("CANH BAO: So luong POI dau vao va dau ra khong khop.")

    # --------------------------------------------------------
    # Duong dan file ket qua
    # --------------------------------------------------------

    print("\n========== FILE KET QUA ==========")

    print(f"POI duoc giu lai: {CATEGORIZED_FILE}")
    print(f"POI chua phan loai: {UNCLASSIFIED_FILE}")
    print(f"POI bi loai: {EXCLUDED_FILE}")

    print("\nHoan thanh xu ly POI!")


# ============================================================
# 12. CHAY CHUONG TRINH
# ============================================================

if __name__ == "__main__":
    main()
