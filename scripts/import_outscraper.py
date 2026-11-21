
import json
import math
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

# ---------------------------------------------------------
# PROJECT PATH
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

EXCEL_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "outscraper_pois_cleaned.xlsx"
)

SHEET_NAME = "unique_pois"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.connection import SessionLocal, init_db
from database.models import POI, Category, POICategory, POIDetail


# ---------------------------------------------------------
# CATEGORY CONFIGURATION
# ---------------------------------------------------------

CATEGORIES = {
    "sightseeing": "Tham quan",
    "hotel": "Khách sạn",
    "food_drink": "Ăn uống",
    "beach": "Bãi biển",
    "shopping": "Mua sắm",
    "entertainment": "Giải trí",
}


# ---------------------------------------------------------
# DATA CONVERSION HELPERS
# ---------------------------------------------------------

def clean_value(value):
    """
    Chuyển NaN, None, NaT thành None.
    Giữ nguyên các giá trị hợp lệ.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def to_string(value):
    value = clean_value(value)

    if value is None:
        return None

    return str(value).strip()


def to_float(value):
    value = clean_value(value)

    if value is None:
        return None

    try:
        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (ValueError, TypeError):
        return None


def to_integer(value):
    value = clean_value(value)

    if value is None:
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError, OverflowError):
        return None


def to_json_list(value):
    """
    Chuyển secondary_categories thành list Python.
    Hỗ trợ dữ liệu dạng JSON string hoặc list.
    """

    value = clean_value(value)

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            result = json.loads(value)

            if isinstance(result, list):
                return result

        except json.JSONDecodeError:
            return []

    return []


def to_boolean_integer(value):
    """
    Chuẩn hóa boolean thành 1 hoặc 0.
    Giá trị thiếu giữ None.
    """

    value = clean_value(value)

    if value is None:
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return int(value != 0)

    value = str(value).strip().lower()

    if value in ("true", "1", "yes"):
        return 1

    if value in ("false", "0", "no"):
        return 0

    return None


# ---------------------------------------------------------
# CATEGORY INITIALIZATION
# ---------------------------------------------------------

def initialize_categories(session: Session):
    """
    Tạo sáu danh mục nếu chưa tồn tại.
    """

    category_map = {}

    for code, name in CATEGORIES.items():

        category = (
            session.query(Category)
            .filter(Category.code == code)
            .first()
        )

        if category is None:
            category = Category(
                code=code,
                name=name
            )

            session.add(category)
            session.flush()

        else:
            category.name = name

        category_map[code] = category

    return category_map


# ---------------------------------------------------------
# POI CATEGORY IMPORT
# ---------------------------------------------------------

def import_poi_categories(
    session: Session,
    poi: POI,
    primary_category: str,
    secondary_categories: list,
    category_map: dict
):
    """
    Gắn danh mục chính và phụ cho một POI.
    """

    session.query(POICategory).filter(
        POICategory.poi_id == poi.id
    ).delete(synchronize_session=False)

    category_codes = []

    if primary_category in category_map:
        category_codes.append(primary_category)

    for code in secondary_categories:

        code = str(code).strip()

        if code in category_map and code not in category_codes:
            category_codes.append(code)

    for code in category_codes:

        category = category_map[code]

        session.add(
            POICategory(
                poi_id=poi.id,
                category_id=category.id,
                is_primary=int(code == primary_category)
            )
        )


# ---------------------------------------------------------
# POI DETAIL IMPORT
# ---------------------------------------------------------

def import_poi_detail(session: Session, poi: POI, row):
    """
    Nhập các thông tin bổ sung từ Outscraper.
    """

    detail = (
        session.query(POIDetail)
        .filter(POIDetail.poi_id == poi.id)
        .first()
    )

    if detail is None:
        detail = POIDetail(poi_id=poi.id)
        session.add(detail)

    detail.subtype = to_string(row.get("subtypes"))
    detail.place_type = to_string(row.get("type"))

    detail.rating = to_float(row.get("rating"))
    detail.reviews = to_integer(row.get("reviews"))

    detail.photos_count = to_integer(row.get("photos_count"))

    detail.photo = to_string(row.get("photo"))
    detail.street_view = to_string(row.get("street_view"))
    detail.logo = to_string(row.get("logo"))

    detail.business_status = to_string(
        row.get("business_status")
    )

    detail.working_hours = to_string(
        row.get("working_hours")
    )

    detail.working_hours_csv = to_string(
        row.get("working_hours_csv_compatible")
    )

    detail.reviews_per_score = to_string(
        row.get("reviews_per_score")
    )

    detail.popular_times = to_string(
        row.get("popular_times")
    )

    detail.prices = to_string(row.get("prices"))
    detail.range = to_string(row.get("range"))

    detail.menu_link = to_string(row.get("menu_link"))

    detail.reservation_links = to_string(
        row.get("reservation_links")
    )

    detail.booking_appointment_link = to_string(
        row.get("booking_appointment_link")
    )

    detail.order_links = to_string(row.get("order_links"))

    detail.verified = to_boolean_integer(
        row.get("verified")
    )


# ---------------------------------------------------------
# MAIN POI IMPORT
# ---------------------------------------------------------

def import_pois(session: Session, dataframe: pd.DataFrame):
    category_map = initialize_categories(session)

    imported_count = 0
    updated_count = 0
    skipped_count = 0

    errors = []

    for index, row in dataframe.iterrows():

        try:
            place_id = to_string(row.get("place_id"))
            name = to_string(row.get("name"))

            latitude = to_float(row.get("latitude"))
            longitude = to_float(row.get("longitude"))

            primary_category = to_string(
                row.get("primary_category")
            )

            if not place_id or not name:
                skipped_count += 1
                errors.append(
                    f"Row {index}: Missing place_id or name"
                )
                continue

            if latitude is None or longitude is None:
                skipped_count += 1
                errors.append(
                    f"Row {index}: Missing coordinates"
                )
                continue

            if primary_category not in category_map:
                skipped_count += 1
                errors.append(
                    f"Row {index}: Invalid category "
                    f"{primary_category}"
                )
                continue

            poi = (
                session.query(POI)
                .filter(POI.place_id == place_id)
                .first()
            )

            is_new = poi is None

            if is_new:
                poi = POI(place_id=place_id)
                session.add(poi)

            # Basic information
            poi.name = name
            poi.name_for_emails = to_string(
                row.get("name_for_emails")
            )

            poi.address = to_string(row.get("address"))
            poi.street = to_string(row.get("street"))
            poi.city = to_string(row.get("city"))
            poi.county = to_string(row.get("county"))
            poi.state = to_string(row.get("state"))
            poi.country = to_string(row.get("country"))

            poi.latitude = latitude
            poi.longitude = longitude

            poi.phone = to_string(row.get("phone"))
            poi.website = to_string(row.get("website"))
            poi.description = to_string(
                row.get("description")
            )

            poi.google_id = to_string(row.get("google_id"))

            # CID is stored as text, not a numeric identifier.
            cid = clean_value(row.get("cid"))

            if cid is not None:
                if isinstance(cid, float) and cid.is_integer():
                    poi.cid = format(cid, ".0f")
                else:
                    poi.cid = str(cid)
            else:
                poi.cid = None

            poi.location_link = to_string(
                row.get("location_link")
            )

            poi.source_file = to_string(
                row.get("source_files")
            ) or to_string(row.get("source_file"))

            poi.cleaning_action = to_string(
                row.get("cleaning_action")
            )

            poi.cleaning_note = to_string(
                row.get("cleaning_note")
            )

            # Flush to get POI ID
            session.flush()

            # Categories
            secondary_categories = to_json_list(
                row.get("secondary_categories")
            )

            import_poi_categories(
                session=session,
                poi=poi,
                primary_category=primary_category,
                secondary_categories=secondary_categories,
                category_map=category_map
            )

            # Additional Outscraper details
            import_poi_detail(
                session=session,
                poi=poi,
                row=row
            )

            if is_new:
                imported_count += 1
            else:
                updated_count += 1

        except Exception as exc:
            skipped_count += 1
            errors.append(
                f"Row {index}: {type(exc).__name__}: {exc}"
            )

            raise

    return imported_count, updated_count, skipped_count, errors


# ---------------------------------------------------------
# DATABASE REPORT
# ---------------------------------------------------------

def print_database_report(session: Session):

    print("\n========== DATABASE REPORT ==========")

    total_pois = session.query(POI).count()
    total_categories = session.query(Category).count()
    total_poi_categories = session.query(POICategory).count()
    total_details = session.query(POIDetail).count()

    print("Total POIs:", total_pois)
    print("Total categories:", total_categories)
    print("Total POI-category relations:", total_poi_categories)
    print("Total POI details:", total_details)

    print("\nCATEGORY DISTRIBUTION:")

    for code, name in CATEGORIES.items():

        category = (
            session.query(Category)
            .filter(Category.code == code)
            .first()
        )

        count = 0

        if category:
            count = (
                session.query(POICategory)
                .filter(
                    POICategory.category_id == category.id,
                    POICategory.is_primary == 1
                )
                .count()
            )

        print(f"{code}: {count}")

    print("\n=====================================")


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

def main():

    print("=====================================")
    print("OUTSCRAPER POI IMPORT")
    print("=====================================")

    print("Input file:", EXCEL_PATH)

    if not EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find input file: {EXCEL_PATH}"
        )

    # Load Excel
    dataframe = pd.read_excel(
        EXCEL_PATH,
        sheet_name=SHEET_NAME
    )

    print("Input records:", len(dataframe))

    # Validate input
    if len(dataframe) != 438:
        raise ValueError(
            f"Expected 438 records, got {len(dataframe)}"
        )

    if dataframe["place_id"].isna().any():
        raise ValueError("Missing Place ID detected")

    if dataframe["place_id"].nunique() != len(dataframe):
        raise ValueError("Duplicate Place ID detected")

    # Initialize database tables
    init_db()

    session = SessionLocal()

    try:
        imported, updated, skipped, errors = import_pois(
            session,
            dataframe
        )

        session.commit()

        print("\n========== IMPORT RESULT ==========")
        print("New POIs imported:", imported)
        print("Existing POIs updated:", updated)
        print("Skipped records:", skipped)

        if errors:
            print("\nERRORS:")
            for error in errors:
                print("-", error)

        print_database_report(session)

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()
