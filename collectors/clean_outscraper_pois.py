
import json
import re
import sys
from pathlib import Path

import pandas as pd


# ============================================================
# 1. PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "outscraper_geography_validation.xlsx"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "outscraper_pois_cleaned.xlsx"
)

VALID_STATUS = "VALID"

CATEGORIES = [
    "sightseeing",
    "hotel",
    "food_drink",
    "beach",
    "shopping",
    "entertainment",
]

CATEGORY_TARGETS = {
    "sightseeing": 160,
    "hotel": 50,
    "food_drink": 175,
    "beach": 15,
    "shopping": 50,
    "entertainment": 50,
}


# ============================================================
# 2. MANUAL CLASSIFICATION
# ============================================================
# Key: tên địa điểm
# Value:
#   primary_category: danh mục chính
#   secondary_categories: danh mục phụ
#   exclude: có loại khỏi tập POI chính không
#   reason: lý do xử lý

MANUAL_CLASSIFICATION = {
    "Cỏ May Coffee & Souvenir Shop": {
        "primary_category": "food_drink",
        "secondary_categories": ["shopping"],
        "exclude": False,
        "reason": "Địa điểm kinh doanh kết hợp cà phê và cửa hàng lưu niệm.",
    },
    "The Marble Mountains": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Điểm tham quan.",
    },
    "Danang Riverwalk": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Địa điểm tham quan, dạo bộ.",
    },
    "Danang Fine Arts Museum": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Bảo tàng, điểm tham quan văn hóa.",
    },
    "Da Nang Visitor Center": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Điểm thông tin và hỗ trợ khách tham quan.",
    },
    "Trình coffee beans AEON MALL Đà Nẵng Thanh Khê": {
        "primary_category": "shopping",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Cửa hàng bán sản phẩm cà phê.",
    },
    "Công ty Du lịch Bản Địa Đà Nẵng": {
        "primary_category": None,
        "secondary_categories": [],
        "exclude": True,
        "reason": "Đơn vị cung cấp dịch vụ tour, không phải POI du lịch.",
    },
    "Da Nang Food Tour": {
        "primary_category": None,
        "secondary_categories": [],
        "exclude": True,
        "reason": "Đơn vị/dịch vụ tour, không phải địa điểm POI cụ thể.",
    },
    "Dragon Bridge": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Công trình biểu tượng và điểm tham quan.",
    },
    "Tuong Theater Nguyen Hien Dinh": {
        "primary_category": "entertainment",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Địa điểm biểu diễn nghệ thuật.",
    },
    "Min Min House Da Nang": {
        "primary_category": "shopping",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Cửa hàng quà tặng và sản phẩm lưu niệm.",
    },
    "Diamond Time Complex": {
        "primary_category": None,
        "secondary_categories": [],
        "exclude": True,
        "reason": "Loại hình chính là coworking space, không phù hợp 6 danh mục POI.",
    },
    "BREWHAHA Central - Local Craft Beer House": {
        "primary_category": "food_drink",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Địa điểm kinh doanh ăn uống.",
    },
    "Da Nang Fresco Village": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Không gian nghệ thuật và điểm tham quan.",
    },
    "Bloom Night Club": {
        "primary_category": "entertainment",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Địa điểm giải trí về đêm.",
    },
    "APEC Park": {
        "primary_category": "sightseeing",
        "secondary_categories": [],
        "exclude": False,
        "reason": "Công viên công cộng và điểm tham quan.",
    },
}


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def normalize_name(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def json_list(values):
    cleaned = []
    for value in values:
        if pd.notna(value) and str(value).strip():
            item = str(value).strip()
            if item not in cleaned:
                cleaned.append(item)
    return json.dumps(cleaned, ensure_ascii=False)


def get_manual_rule(name):
    normalized = normalize_name(name)

    for key, rule in MANUAL_CLASSIFICATION.items():
        if normalize_name(key) == normalized:
            return rule

    return None


def ensure_columns(df, required_columns):
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(
            "File đầu vào thiếu các cột bắt buộc: "
            + ", ".join(missing)
        )


# ============================================================
# 4. LOAD DATA
# ============================================================

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file đầu vào:\n{INPUT_FILE}"
        )

    print("=" * 65)
    print("DOC DU LIEU KIEM DINH OUTSCRAPER")
    print("=" * 65)

    df = pd.read_excel(INPUT_FILE, sheet_name="all_records")

    ensure_columns(
        df,
        [
            "name",
            "place_id",
            "project_category",
            "validation_status",
        ],
    )

    print(f"Tong so ban ghi: {len(df)}")

    return df


# ============================================================
# 5. SPLIT VALID / OUTSIDE / REVIEW
# ============================================================

def split_validation_data(df):
    valid = df[
        df["validation_status"]
        .astype(str)
        .str.upper()
        .eq(VALID_STATUS)
    ].copy()

    outside = df[
        df["validation_status"]
        .astype(str)
        .str.upper()
        .eq("OUTSIDE_BOUNDARY")
    ].copy()

    review = df[
        ~df.index.isin(valid.index)
        & ~df.index.isin(outside.index)
    ].copy()

    print("\nKET QUA PHAN LOAI DIA LY")
    print(f"VALID: {len(valid)}")
    print(f"OUTSIDE_BOUNDARY: {len(outside)}")
    print(f"REVIEW_REQUIRED: {len(review)}")

    return valid, outside, review


# ============================================================
# 6. REMOVE NON-POI SERVICES
# ============================================================

def separate_excluded_services(valid):
    keep_rows = []
    excluded_rows = []

    for _, row in valid.iterrows():
        rule = get_manual_rule(row["name"])

        if rule and rule["exclude"]:
            item = row.to_dict()
            item["exclusion_reason"] = rule["reason"]
            item["cleaning_action"] = "EXCLUDED_FROM_MAIN_POI"
            excluded_rows.append(item)
        else:
            keep_rows.append(row.to_dict())

    kept = pd.DataFrame(keep_rows)
    excluded = pd.DataFrame(excluded_rows)

    print("\nTACH CAC DIA DIEM KHONG PHU HOP")
    print(f"POI tiep tuc xu ly: {len(kept)}")
    print(f"Dia diem/dich vu tach rieng: {len(excluded)}")

    return kept, excluded


# ============================================================
# 7. DEDUPLICATE BY PLACE ID
# ============================================================

def consolidate_duplicates(valid):
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()

    valid = valid.copy()

    valid["place_id"] = valid["place_id"].fillna("").astype(str).str.strip()

    # Không tự động gộp bản ghi thiếu Place ID.
    missing_id = valid["place_id"].eq("")
    with_id = valid[~missing_id].copy()
    without_id = valid[missing_id].copy()

    unique_rows = []
    duplicate_review_rows = []

    duplicate_groups = with_id.groupby("place_id", sort=False)

    for place_id, group in duplicate_groups:
        group = group.copy()

        categories = (
            group["project_category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        names = (
            group["name"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        # Chọn quy tắc phân loại dựa trên tên địa điểm.
        rule = None
        for name in names:
            rule = get_manual_rule(name)
            if rule:
                break

        if len(group) > 1:
            if rule is None:
                # Không tự suy đoán danh mục chính nếu gặp nhóm trùng
                # chưa có quy tắc phân loại thủ công.
                for _, row in group.iterrows():
                    item = row.to_dict()
                    item["cleaning_decision"] = "NEEDS_MANUAL_REVIEW"
                    item["review_reason"] = (
                        "Place ID bị trùng nhưng chưa có quy tắc phân loại."
                    )
                    duplicate_review_rows.append(item)

                continue

            if rule["exclude"]:
                # Thông thường đã được tách ở bước trước.
                continue

            primary_category = rule["primary_category"]
            secondary_categories = rule["secondary_categories"]

            primary_rows = group[
                group["project_category"].astype(str).eq(primary_category)
            ]

            if primary_rows.empty:
                selected = group.iloc[0]
            else:
                selected = primary_rows.iloc[0]

            item = selected.to_dict()

            item["primary_category"] = primary_category
            item["secondary_categories"] = json_list(
                secondary_categories
            )
            item["source_categories"] = json_list(categories)
            item["source_files"] = json_list(
                group["source_file"].tolist()
                if "source_file" in group.columns
                else []
            )
            item["duplicate_count"] = len(group)
            item["cleaning_action"] = "MERGED_BY_PLACE_ID"
            item["cleaning_note"] = rule["reason"]

            unique_rows.append(item)

            for _, row in group.iterrows():
                review_item = row.to_dict()
                review_item["selected_primary_category"] = primary_category
                review_item["secondary_categories"] = json_list(
                    secondary_categories
                )
                review_item["cleaning_decision"] = (
                    "KEPT_AS_CANONICAL"
                    if str(row["project_category"]) == primary_category
                    else "MERGED_INTO_CANONICAL"
                )
                review_item["cleaning_reason"] = rule["reason"]

                duplicate_review_rows.append(review_item)

        else:
            selected = group.iloc[0]
            item = selected.to_dict()

            category = str(item.get("project_category", "")).strip()

            item["primary_category"] = category
            item["secondary_categories"] = json_list([])
            item["source_categories"] = json_list(categories)
            item["source_files"] = json_list(
                group["source_file"].tolist()
                if "source_file" in group.columns
                else []
            )
            item["duplicate_count"] = 1
            item["cleaning_action"] = "KEPT_UNIQUE"
            item["cleaning_note"] = "Place ID không bị trùng."

            unique_rows.append(item)

    # Các bản ghi không có Place ID được giữ lại riêng,
    # không tự động gộp theo tên.
    for _, row in without_id.iterrows():
        item = row.to_dict()
        category = str(item.get("project_category", "")).strip()

        item["primary_category"] = category
        item["secondary_categories"] = json_list([])
        item["source_categories"] = json_list([category])
        item["source_files"] = json_list(
            [item.get("source_file", "")]
        )
        item["duplicate_count"] = 1
        item["cleaning_action"] = "KEPT_WITHOUT_PLACE_ID"
        item["cleaning_note"] = (
            "Thiếu Place ID, cần kiểm tra bổ sung trước khi sử dụng."
        )

        unique_rows.append(item)

    unique_pois = pd.DataFrame(unique_rows)
    duplicate_review = pd.DataFrame(duplicate_review_rows)

    return unique_pois, duplicate_review


# ============================================================
# 8. CATEGORY SUMMARY
# ============================================================

def build_category_summary(valid_before, unique_pois):
    before_counts = (
        valid_before["project_category"]
        .value_counts()
        .to_dict()
    )

    after_counts = (
        unique_pois["primary_category"]
        .value_counts()
        .to_dict()
    )

    rows = []

    for category in CATEGORIES:
        before = int(before_counts.get(category, 0))
        after = int(after_counts.get(category, 0))
        target = CATEGORY_TARGETS[category]

        rows.append({
            "category": category,
            "target": target,
            "valid_before_cleaning": before,
            "final_unique_pois": after,
            "difference_from_target": after - target,
            "target_completion_percent": (
                round(after / target * 100, 2)
                if target
                else 0
            ),
        })

    summary = pd.DataFrame(rows)

    total_row = {
        "category": "TOTAL",
        "target": sum(CATEGORY_TARGETS.values()),
        "valid_before_cleaning": len(valid_before),
        "final_unique_pois": len(unique_pois),
        "difference_from_target": (
            len(unique_pois) - sum(CATEGORY_TARGETS.values())
        ),
        "target_completion_percent": round(
            len(unique_pois)
            / sum(CATEGORY_TARGETS.values())
            * 100,
            2,
        ),
    }

    summary = pd.concat(
        [summary, pd.DataFrame([total_row])],
        ignore_index=True,
    )

    return summary


# ============================================================
# 9. EXPORT EXCEL
# ============================================================

def export_result(
    unique_pois,
    duplicate_review,
    excluded_services,
    outside_boundary,
    review_required,
    category_summary,
):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:

        unique_pois.to_excel(
            writer,
            sheet_name="unique_pois",
            index=False,
        )

        duplicate_review.to_excel(
            writer,
            sheet_name="duplicate_review",
            index=False,
        )

        excluded_services.to_excel(
            writer,
            sheet_name="excluded_services",
            index=False,
        )

        outside_boundary.to_excel(
            writer,
            sheet_name="outside_boundary",
            index=False,
        )

        review_required.to_excel(
            writer,
            sheet_name="review_required",
            index=False,
        )

        category_summary.to_excel(
            writer,
            sheet_name="category_summary",
            index=False,
        )

        # Định dạng độ rộng cột và cố định dòng tiêu đề.
        for worksheet in writer.sheets.values():
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions

            for column_cells in worksheet.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter

                for cell in column_cells[:200]:
                    value = cell.value
                    if value is not None:
                        max_length = max(
                            max_length,
                            len(str(value)),
                        )

                worksheet.column_dimensions[column_letter].width = min(
                    max(max_length + 2, 12),
                    45,
                )

    print("\nDA XUAT FILE THANH CONG:")
    print(OUTPUT_FILE)


# ============================================================
# 10. MAIN
# ============================================================

def main():
    try:
        df = load_data()

        valid, outside, review = split_validation_data(df)

        valid_for_cleaning, excluded = separate_excluded_services(
            valid
        )

        unique_pois, duplicate_review = consolidate_duplicates(
            valid_for_cleaning
        )

        # Nếu còn nhóm Place ID trùng chưa được xử lý,
        # dừng để tránh xuất dữ liệu chưa chuẩn hóa.
        unresolved = duplicate_review[
            duplicate_review["cleaning_decision"]
            .astype(str)
            .eq("NEEDS_MANUAL_REVIEW")
        ] if (
            not duplicate_review.empty
            and "cleaning_decision" in duplicate_review.columns
        ) else pd.DataFrame()

        if not unresolved.empty:
            print("\nCAN KIEM TRA THEM CAC NHOM TRUNG CHUA PHAN LOAI:")
            print(
                unresolved[
                    ["name", "place_id", "project_category"]
                ].to_string(index=False)
            )
            raise ValueError(
                "Con Place ID trung chua co quy tac phan loai. "
                "Chua xuat file ket qua."
            )

        category_summary = build_category_summary(
            valid_for_cleaning,
            unique_pois,
        )

        export_result(
            unique_pois=unique_pois,
            duplicate_review=duplicate_review,
            excluded_services=excluded,
            outside_boundary=outside,
            review_required=review,
            category_summary=category_summary,
        )

        print("\n" + "=" * 65)
        print("TONG KET SAU CHUAN HOA")
        print("=" * 65)

        print(f"Ban ghi VALID ban dau: {len(valid)}")
        print(f"Ngoai pham vi: {len(outside)}")
        print(f"Dich vu/POI bi loai: {len(excluded)}")
        print(f"POI duy nhat cuoi cung: {len(unique_pois)}")
        print(f"Ban ghi trong duplicate_review: {len(duplicate_review)}")

        print("\nSO LUONG THEO DANH MUC:")
        print(
            category_summary.to_string(index=False)
        )

        print("\nHOAN TAT.")

    except Exception as error:
        print("\nLOI:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
