
import json
from pathlib import Path

import pandas as pd
from shapely.geometry import shape, Point
from shapely.ops import unary_union


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Thu muc chua 7 file Excel Outscraper
SOURCE_DIR = PROJECT_ROOT / "data" / "raw" / "outscraper"

# Cac file ranh gioi va land mask
BOUNDARY_FILE = (
    PROJECT_ROOT / "data" / "raw" / "danang_old_boundary.geojson"
)

OSM_MASK_FILE = (
    PROJECT_ROOT / "data" / "raw" / "danang_old_land_mask_osm.geojson"
)

NATURAL_EARTH_MASK_FILE = (
    PROJECT_ROOT / "data" / "raw" / "danang_old_land_mask.geojson"
)

# Thu muc va file ket qua
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = (
    OUTPUT_DIR / "outscraper_geography_validation.xlsx"
)

# Chi xu ly dung 7 file nguon da thong nhat
EXPECTED_FILES = [
    "Outscraper-20261121033650s3a0a.xlsx",
    "Outscraper-20261121035449s0d2f.xlsx",
    "Outscraper-20261121035543s9bd0.xlsx",
    "Outscraper-20261121035841s73dd.xlsx",
    "Outscraper-20261121035944s3a75.xlsx",
    "Outscraper-20261121040115s58e3.xlsx",
    "Outscraper-20261121040254s44a6.xlsx",
]

# Anh xa file nguon vao 6 danh muc backend
FILE_CATEGORIES = {
    "Outscraper-20261121033650s3a0a.xlsx": "food_drink",
    "Outscraper-20261121035449s0d2f.xlsx": "sightseeing",
    "Outscraper-20261121035543s9bd0.xlsx": "hotel",
    "Outscraper-20261121035841s73dd.xlsx": "food_drink",
    "Outscraper-20261121035944s3a75.xlsx": "beach",
    "Outscraper-20261121040115s58e3.xlsx": "shopping",
    "Outscraper-20261121040254s44a6.xlsx": "entertainment",
}


# ============================================================
# 2. LOAD AND REPAIR GEOJSON GEOMETRY
# ============================================================

def repair_geometry(geometry):
    """Kiem tra va sua geometry khong hop le neu can."""

    if geometry is None or geometry.is_empty:
        raise ValueError("Geometry rong.")

    if not geometry.is_valid:
        try:
            from shapely import make_valid
            geometry = make_valid(geometry)
        except (ImportError, AttributeError):
            geometry = geometry.buffer(0)

    if geometry.is_empty:
        raise ValueError("Geometry rong sau khi sua.")

    return geometry


def load_geojson_geometry(file_path, boundary_mode=False):
    """
    Doc GeoJSON dang FeatureCollection, Feature hoac Geometry.

    Neu la boundary va co feature layer='final',
    uu tien su dung feature nay.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay file: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        geojson = json.load(file)

    geometries = []

    if geojson.get("type") == "FeatureCollection":

        features = geojson.get("features", [])

        if boundary_mode:
            final_features = [
                feature
                for feature in features
                if str(
                    feature.get("properties", {}).get("layer", "")
                ).lower() == "final"
            ]

            if final_features:
                features = final_features

        for feature in features:
            geometry_data = feature.get("geometry")

            if geometry_data:
                geometries.append(shape(geometry_data))

    elif geojson.get("type") == "Feature":

        if geojson.get("geometry"):
            geometries.append(shape(geojson["geometry"]))

    else:
        geometries.append(shape(geojson))

    if not geometries:
        raise ValueError(
            f"Khong tim thay geometry trong {file_path.name}"
        )

    geometries = [
        repair_geometry(geometry)
        for geometry in geometries
    ]

    merged_geometry = unary_union(geometries)
    merged_geometry = repair_geometry(merged_geometry)

    print(f"\nDa nap: {file_path.name}")
    print(f"  So geometry: {len(geometries)}")
    print(f"  Geometry type: {merged_geometry.geom_type}")
    print(f"  Bounds: {merged_geometry.bounds}")

    return merged_geometry


# ============================================================
# 3. LOAD 7 OUTSCRAPER SOURCE FILES
# ============================================================

def load_source_data():

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Khong tim thay thu muc nguon:\n{SOURCE_DIR}"
        )

    all_data = []

    print("\n========== DOC FILE OUTSCRAPER ==========")

    for filename in EXPECTED_FILES:

        file_path = SOURCE_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Thieu file nguon:\n{file_path}"
            )

        df = pd.read_excel(file_path)

        # Kiem tra cot toa do
        required_columns = [
            "latitude",
            "longitude"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"File {filename} thieu cot: "
                f"{missing_columns}"
            )

        # Gan thong tin nguon va danh muc
        df["source_file"] = filename

        df["project_category"] = (
            FILE_CATEGORIES[filename]
        )

        all_data.append(df)

        print(
            f"{filename}: {len(df)} records"
        )

    data = pd.concat(
        all_data,
        ignore_index=True
    )

    print("-----------------------------------------")
    print(f"Tong so records: {len(data)}")
    print("=========================================")

    if len(data) != 500:
        print(
            f"CANH BAO: Tong so records hien tai la "
            f"{len(data)}, khong phai 500."
        )

    return data


# ============================================================
# 4. GEOGRAPHIC VALIDATION
# ============================================================

def validate_coordinates(
    df,
    boundary,
    osm_mask,
    natural_earth_mask
):

    results = []

    print("\n========== KIEM TRA TOA DO ==========")

    for index, row in df.iterrows():

        lat = pd.to_numeric(
            row.get("latitude"),
            errors="coerce"
        )

        lon = pd.to_numeric(
            row.get("longitude"),
            errors="coerce"
        )

        inside_boundary = None
        inside_osm_land = None
        inside_ne_land = None

        reason = ""

        # Truong hop thieu toa do
        if pd.isna(lat) or pd.isna(lon):

            status = "MISSING_COORDINATES"

            reason = (
                "Thieu latitude hoac longitude"
            )

        # Truong hop toa do khong hop le
        elif not (
            -90 <= lat <= 90
            and -180 <= lon <= 180
        ):

            status = "INVALID_COORDINATES"

            reason = (
                "Toa do nam ngoai pham vi hop le"
            )

        else:

            # Shapely su dung thu tu (longitude, latitude)
            point = Point(
                float(lon),
                float(lat)
            )

            # Kiem tra ranh gioi Da Nang cu
            inside_boundary = boundary.covers(point)

            # Kiem tra OSM Land Mask
            inside_osm_land = osm_mask.covers(point)

            # Doi chieu them voi Natural Earth
            if natural_earth_mask is not None:
                inside_ne_land = (
                    natural_earth_mask.covers(point)
                )

            # Phan loai ket qua
            if not inside_boundary:

                status = "OUTSIDE_BOUNDARY"

                reason = (
                    "Diem nam ngoai ranh gioi Da Nang cu"
                )

            elif not inside_osm_land:

                status = "INSIDE_BOUNDARY_NOT_LAND"

                reason = (
                    "Nam trong ranh gioi nhung "
                    "ngoai OSM land mask"
                )

            else:

                status = "VALID"

                reason = (
                    "Nam trong ranh gioi va tren "
                    "dat lien theo OSM"
                )

        results.append({
            "inside_boundary": inside_boundary,
            "inside_osm_land_mask": inside_osm_land,
            "inside_natural_earth_mask": inside_ne_land,
            "validation_status": status,
            "validation_reason": reason,
        })

        if (index + 1) % 100 == 0:
            print(
                f"Da kiem tra {index + 1}/{len(df)} POIs"
            )

    result_df = pd.DataFrame(
        results,
        index=df.index
    )

    return pd.concat(
        [df, result_df],
        axis=1
    )


# ============================================================
# 5. BUILD VALIDATION SUMMARY
# ============================================================

def build_summary(df):

    status_summary = (
        df.groupby(
            [
                "project_category",
                "source_file",
                "validation_status"
            ],
            dropna=False
        )
        .size()
        .reset_index(name="record_count")
    )

    category_summary = (
        df.groupby("project_category")
        .agg(
            total_records=(
                "validation_status",
                "count"
            ),

            valid=(
                "validation_status",
                lambda x: (
                    x == "VALID"
                ).sum()
            ),

            outside_boundary=(
                "validation_status",
                lambda x: (
                    x == "OUTSIDE_BOUNDARY"
                ).sum()
            ),

            outside_land=(
                "validation_status",
                lambda x: (
                    x == "INSIDE_BOUNDARY_NOT_LAND"
                ).sum()
            ),

            missing_coordinates=(
                "validation_status",
                lambda x: (
                    x == "MISSING_COORDINATES"
                ).sum()
            ),

            invalid_coordinates=(
                "validation_status",
                lambda x: (
                    x == "INVALID_COORDINATES"
                ).sum()
            )
        )
        .reset_index()
    )

    return status_summary, category_summary


# ============================================================
# 6. DUPLICATE PLACE ID REPORT
# ============================================================

def build_duplicate_report(df):

    # Outscraper thuong su dung place_id
    # Neu khong co thi thu tim Google Place ID
    possible_columns = [
        "place_id",
        "Place ID",
        "google_place_id"
    ]

    place_id_column = next(
        (
            column
            for column in possible_columns
            if column in df.columns
        ),
        None
    )

    if place_id_column is None:
        print(
            "\nCANH BAO: Khong tim thay cot Place ID."
        )
        return pd.DataFrame()

    valid_ids = (
        df[place_id_column].notna()
        &
        (
            df[place_id_column]
            .astype(str)
            .str.strip()
            != ""
        )
    )

    duplicates = df.loc[valid_ids].duplicated(
        subset=[place_id_column],
        keep=False
    )

    duplicate_report = df.loc[
        valid_ids
    ].loc[duplicates].copy()

    if not duplicate_report.empty:
        duplicate_report = duplicate_report.sort_values(
            by=place_id_column
        )

    return duplicate_report


# ============================================================
# 7. EXPORT EXCEL REPORT
# ============================================================

def export_report(
    validated,
    status_summary,
    category_summary,
    duplicate_report
):

    outside_boundary = validated[
        validated["validation_status"]
        == "OUTSIDE_BOUNDARY"
    ]

    outside_land = validated[
        validated["validation_status"]
        == "INSIDE_BOUNDARY_NOT_LAND"
    ]

    review_records = validated[
        validated["validation_status"]
        != "VALID"
    ]

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        validated.to_excel(
            writer,
            sheet_name="all_records",
            index=False
        )

        category_summary.to_excel(
            writer,
            sheet_name="category_summary",
            index=False
        )

        status_summary.to_excel(
            writer,
            sheet_name="status_summary",
            index=False
        )

        outside_boundary.to_excel(
            writer,
            sheet_name="outside_boundary",
            index=False
        )

        outside_land.to_excel(
            writer,
            sheet_name="outside_land",
            index=False
        )

        review_records.to_excel(
            writer,
            sheet_name="review_required",
            index=False
        )

        duplicate_report.to_excel(
            writer,
            sheet_name="duplicate_place_ids",
            index=False
        )

        # Dinh dang cac sheet Excel
        for worksheet in writer.book.worksheets:

            worksheet.freeze_panes = "A2"

            worksheet.auto_filter.ref = (
                worksheet.dimensions
            )

            for column_cells in worksheet.columns:

                max_length = 0

                column_letter = (
                    column_cells[0].column_letter
                )

                for cell in column_cells[:200]:

                    value = (
                        str(cell.value)
                        if cell.value is not None
                        else ""
                    )

                    max_length = max(
                        max_length,
                        len(value)
                    )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max(max_length + 2, 12),
                    45
                )


# ============================================================
# 8. PRINT FINAL SUMMARY
# ============================================================

def print_final_summary(
    validated,
    category_summary,
    duplicate_report
):

    print("\n")
    print("=" * 65)
    print("OUTSCRAPER GEOGRAPHY VALIDATION RESULT")
    print("=" * 65)

    print(
        f"\nTong so POIs: {len(validated)}"
    )

    print("\n--- KET QUA THEO TRANG THAI ---")

    print(
        validated["validation_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\n--- KET QUA THEO DANH MUC ---")

    print(
        category_summary.to_string(
            index=False
        )
    )

    print(
        "\nSo dong trung Place ID: "
        f"{len(duplicate_report)}"
    )

    print("\n--- FILE KET QUA ---")

    print(OUTPUT_FILE)

    print("\n--- GIAI THICH TRANG THAI ---")

    print(
        "VALID: Nam trong ranh gioi "
        "va tren OSM land mask."
    )

    print(
        "OUTSIDE_BOUNDARY: Nam ngoai "
        "ranh gioi Da Nang cu."
    )

    print(
        "INSIDE_BOUNDARY_NOT_LAND: Nam trong "
        "ranh gioi nhung ngoai OSM land mask."
    )

    print(
        "MISSING_COORDINATES: Thieu toa do."
    )

    print(
        "INVALID_COORDINATES: Toa do khong hop le."
    )

    print("\nLuu y:")
    print(
        "- Khong tu dong xoa bat ky POI nao."
    )
    print(
        "- Cac truong hop khong VALID can duoc "
        "kiem tra truoc khi quyet dinh."
    )
    print(
        "- Natural Earth chi dung de doi chieu, "
        "OSM Land Mask la tieu chuan chinh."
    )

    print("=" * 65)


# ============================================================
# 9. MAIN
# ============================================================

def main():

    print("=" * 65)
    print("OUTSCRAPER GEOGRAPHY VALIDATION")
    print("=" * 65)

    # Tao thu muc ket qua neu chua ton tai
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # STEP 1: Load boundary and land masks
    # --------------------------------------------------------

    print("\n[1] LOADING GEOJSON DATA")

    boundary = load_geojson_geometry(
        BOUNDARY_FILE,
        boundary_mode=True
    )

    osm_mask = load_geojson_geometry(
        OSM_MASK_FILE
    )

    natural_earth_mask = None

    if NATURAL_EARTH_MASK_FILE.exists():

        natural_earth_mask = load_geojson_geometry(
            NATURAL_EARTH_MASK_FILE
        )

    else:

        print(
            "Khong co Natural Earth mask. "
            "Bo qua doi chieu."
        )

    # --------------------------------------------------------
    # STEP 2: Load exactly 7 source files
    # --------------------------------------------------------

    print("\n[2] LOADING OUTSCRAPER DATA")

    df = load_source_data()

    # --------------------------------------------------------
    # STEP 3: Validate coordinates
    # --------------------------------------------------------

    print("\n[3] VALIDATING GEOGRAPHIC COORDINATES")

    validated = validate_coordinates(
        df=df,
        boundary=boundary,
        osm_mask=osm_mask,
        natural_earth_mask=natural_earth_mask
    )

    # --------------------------------------------------------
    # STEP 4: Build summaries
    # --------------------------------------------------------

    print("\n[4] BUILDING REPORTS")

    status_summary, category_summary = (
        build_summary(validated)
    )

    duplicate_report = build_duplicate_report(
        validated
    )

    # --------------------------------------------------------
    # STEP 5: Export Excel
    # --------------------------------------------------------

    print("\n[5] EXPORTING EXCEL")

    export_report(
        validated=validated,
        status_summary=status_summary,
        category_summary=category_summary,
        duplicate_report=duplicate_report
    )

    # --------------------------------------------------------
    # STEP 6: Print final results
    # --------------------------------------------------------

    print_final_summary(
        validated=validated,
        category_summary=category_summary,
        duplicate_report=duplicate_report
    )


if __name__ == "__main__":
    main()
