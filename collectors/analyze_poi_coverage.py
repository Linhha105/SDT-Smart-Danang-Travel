
import json
import os
import math
import pandas as pd

from collections import defaultdict
from pyproj import Transformer
from shapely.geometry import shape, Point, box
from shapely.ops import transform


# =====================================================
# 1. KHAI BÁO ĐƯỜNG DẪN VÀ THAM SỐ
# =====================================================

INPUT_FILE = (
    "data/processed/"
    "osm_places_danang_old_full_categorized.json"
)

BOUNDARY_FILE = (
    "data/raw/danang_old_boundary.geojson"
)

OUTPUT_DIR = "data/processed"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "poi_grid_coverage.csv"
)

# Kích thước ô lưới: 500m x 500m
GRID_SIZE = 500

# Hệ tọa độ WGS84 / UTM zone 48N
SOURCE_CRS = "EPSG:4326"
TARGET_CRS = "EPSG:32648"


# =====================================================
# 2. KHAI BÁO SÁU DANH MỤC
# =====================================================

CATEGORY_NAMES = {
    "sightseeing": "Tham quan",
    "hotel": "Khách sạn",
    "food_drink": "Ăn uống",
    "beach": "Bãi biển",
    "shopping": "Mua sắm",
    "entertainment": "Giải trí"
}

CATEGORY_KEYS = list(CATEGORY_NAMES.keys())


# =====================================================
# 3. KHỞI TẠO HỆ TỌA ĐỘ
# =====================================================

print("Dang khoi tao he toa do...")

to_utm = Transformer.from_crs(
    SOURCE_CRS,
    TARGET_CRS,
    always_xy=True
).transform

to_wgs84 = Transformer.from_crs(
    TARGET_CRS,
    SOURCE_CRS,
    always_xy=True
).transform


# =====================================================
# 4. ĐỌC RANH GIỚI NGHIÊN CỨU
# =====================================================

print("\nDang doc ranh gioi nghien cuu...")

if not os.path.exists(BOUNDARY_FILE):
    raise FileNotFoundError(
        f"Khong tim thay file ranh gioi: {BOUNDARY_FILE}"
    )

with open(
    BOUNDARY_FILE,
    "r",
    encoding="utf-8"
) as file:

    boundary_data = json.load(file)


# Chỉ lấy polygon final, không lấy outer hoặc inner riêng lẻ
features = boundary_data.get("features", [])

final_features = [
    feature
    for feature in features
    if feature.get("properties", {}).get("layer") == "final"
]

if len(final_features) != 1:
    raise ValueError(
        "Can co dung 1 feature co layer='final' "
        f"nhung tim thay {len(final_features)} feature."
    )

boundary_wgs84 = shape(
    final_features[0]["geometry"]
)

if boundary_wgs84.is_empty or not boundary_wgs84.is_valid:
    raise ValueError(
        "Geometry ranh gioi khong hop le."
    )

# Chuyển ranh giới sang hệ tọa độ mét
boundary_utm = transform(
    to_utm,
    boundary_wgs84
)

print("Da doc ranh gioi thanh cong.")
print("Loai geometry:", boundary_utm.geom_type)
print(
    "Dien tich ranh gioi:",
    round(boundary_utm.area / 1_000_000, 3),
    "km2"
)


# =====================================================
# 5. ĐỌC DỮ LIỆU POI ĐÃ PHÂN LOẠI
# =====================================================

print("\nDang doc du lieu POI...")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"Khong tim thay file POI: {INPUT_FILE}"
    )

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


if isinstance(data, dict):
    pois = data.get("places", [])
elif isinstance(data, list):
    pois = data
else:
    raise ValueError(
        "Cau truc file POI khong hop le."
    )

print("Tong POI dau vao:", len(pois))


# =====================================================
# 6. CHUẨN HÓA VÀ CHUYỂN TỌA ĐỘ POI
# =====================================================

print("\nDang chuan hoa du lieu POI...")

records = []

invalid_coordinates = 0
outside_boundary = 0
missing_category = 0
invalid_category = 0

for poi in pois:

    try:
        lat = float(poi["latitude"])
        lon = float(poi["longitude"])

        if (
            not math.isfinite(lat)
            or not math.isfinite(lon)
            or not (-90 <= lat <= 90)
            or not (-180 <= lon <= 180)
        ):
            raise ValueError("Toa do khong hop le")

    except (KeyError, TypeError, ValueError):
        invalid_coordinates += 1
        continue

    # Kiểm tra POI thuộc polygon nghiên cứu
    point_wgs84 = Point(lon, lat)

    if not boundary_wgs84.covers(point_wgs84):
        outside_boundary += 1
        continue

    # Chuyển tọa độ sang UTM
    x, y = to_utm(lon, lat)

    category = poi.get("category")

    if not category:
        missing_category += 1
        category = "other"

    elif category not in CATEGORY_KEYS:
        invalid_category += 1
        category = "other"

    records.append({
        "name": poi.get("name"),
        "latitude": lat,
        "longitude": lon,
        "x": x,
        "y": y,
        "osm_type": poi.get("osm_type"),
        "osm_id": poi.get("osm_id"),
        "category": category
    })


df = pd.DataFrame(records)

print("\n========== KIEM TRA DU LIEU ==========")

print("Tong POI dau vao:", len(pois))
print("POI co toa do hop le:", len(records))
print("Toa do khong hop le:", invalid_coordinates)
print("POI ngoai ranh gioi:", outside_boundary)
print("POI thieu danh muc:", missing_category)
print("POI co danh muc khong hop le:", invalid_category)


if df.empty:
    raise ValueError(
        "Khong co POI hop le de phan tich."
    )


# =====================================================
# 7. XÁC ĐỊNH PHẠM VI LƯỚI
# =====================================================

print("\nDang xac dinh pham vi luoi...")

min_x, min_y, max_x, max_y = boundary_utm.bounds

# Căn lưới theo bội số 500m trong hệ UTM
start_x = math.floor(min_x / GRID_SIZE) * GRID_SIZE
start_y = math.floor(min_y / GRID_SIZE) * GRID_SIZE

end_x = math.ceil(max_x / GRID_SIZE) * GRID_SIZE
end_y = math.ceil(max_y / GRID_SIZE) * GRID_SIZE

print("GRID_SIZE:", GRID_SIZE, "m")
print("So hang luoi du kien:", int((end_y - start_y) / GRID_SIZE))
print("So cot luoi du kien:", int((end_x - start_x) / GRID_SIZE))


# =====================================================
# 8. TẠO LƯỚI VÀ CHỈ GIỮ CÁC Ô GIAO RANH GIỚI
# =====================================================

print("\nDang tao luoi khong gian...")

grid_cells = {}

row_count = int((end_y - start_y) / GRID_SIZE)
col_count = int((end_x - start_x) / GRID_SIZE)

for row in range(row_count):

    for col in range(col_count):

        x1 = start_x + col * GRID_SIZE
        y1 = start_y + row * GRID_SIZE

        x2 = x1 + GRID_SIZE
        y2 = y1 + GRID_SIZE

        cell = box(
            x1,
            y1,
            x2,
            y2
        )

        # Chỉ giữ ô có phần diện tích giao với polygon
        if not cell.intersects(boundary_utm):
            continue

        clipped_cell = cell.intersection(
            boundary_utm
        )

        if clipped_cell.is_empty:
            continue

        cell_id = f"R{row:03d}_C{col:03d}"

        grid_cells[(row, col)] = {
            "cell_id": cell_id,
            "geometry": cell,
            "clipped_geometry": clipped_cell,
            "area_m2": clipped_cell.area,
            "total_poi": 0,
            "category_counts": {
                category: 0
                for category in CATEGORY_KEYS
            },
            "other": 0
        }

print("Tong so o luoi giao ranh gioi:", len(grid_cells))


# =====================================================
# 9. GÁN POI VÀO Ô LƯỚI
# =====================================================

print("\nDang gan POI vao o luoi...")

for _, poi in df.iterrows():

    x = poi["x"]
    y = poi["y"]

    col = math.floor(
        (x - start_x) / GRID_SIZE
    )

    row = math.floor(
        (y - start_y) / GRID_SIZE
    )

    key = (row, col)

    if key not in grid_cells:
        continue

    cell_data = grid_cells[key]

    cell_data["total_poi"] += 1

    category = poi["category"]

    if category in CATEGORY_KEYS:
        cell_data["category_counts"][category] += 1
    else:
        cell_data["other"] += 1


# =====================================================
# 10. TẠO BẢNG THỐNG KÊ CHO TẤT CẢ Ô LƯỚI
# =====================================================

print("\nDang tong hop thong ke...")

grid_records = []

for (row, col), cell_data in grid_cells.items():

    cell = cell_data["geometry"]
    clipped_cell = cell_data["clipped_geometry"]

    centroid = clipped_cell.centroid

    lon, lat = to_wgs84(
        centroid.x,
        centroid.y
    )

    area_km2 = (
        cell_data["area_m2"] / 1_000_000
    )

    total_poi = cell_data["total_poi"]

    if area_km2 > 0:
        density = total_poi / area_km2
    else:
        density = 0

    record = {
        "cell_id": cell_data["cell_id"],
        "grid_row": row,
        "grid_col": col,
        "center_latitude": lat,
        "center_longitude": lon,
        "area_km2": round(area_km2, 6),
        "total_poi": total_poi,
        "poi_density_per_km2": round(density, 2),
        "has_poi": total_poi > 0
    }

    for category in CATEGORY_KEYS:
        record[category] = (
            cell_data["category_counts"][category]
        )

    record["other"] = cell_data["other"]

    grid_records.append(record)


grid_stats = pd.DataFrame(grid_records)


# =====================================================
# 11. PHÂN NHÓM MẬT ĐỘ POI
# =====================================================

def classify_density(total_poi):

    if total_poi == 0:
        return "Khong co POI"

    elif total_poi <= 5:
        return "Thap"

    elif total_poi <= 20:
        return "Trung binh"

    elif total_poi <= 50:
        return "Cao"

    else:
        return "Rat cao"


grid_stats["density_level"] = (
    grid_stats["total_poi"].apply(
        classify_density
    )
)


# =====================================================
# 12. THỐNG KÊ ĐỘ PHỦ KHÔNG GIAN
# =====================================================

total_cells = len(grid_stats)

occupied_cells = (
    grid_stats["total_poi"] > 0
).sum()

empty_cells = (
    grid_stats["total_poi"] == 0
).sum()

coverage_rate = (
    occupied_cells / total_cells * 100
    if total_cells > 0
    else 0
)

total_poi = grid_stats["total_poi"].sum()

mean_poi = (
    total_poi / total_cells
    if total_cells > 0
    else 0
)

print("\n========== DO PHU KHONG GIAN ==========")

print("Tong so o luoi:", total_cells)

print("So o co POI:", occupied_cells)

print("So o khong co POI:", empty_cells)

print(
    "Ty le o co POI:",
    round(coverage_rate, 2),
    "%"
)

print(
    "So POI trung binh tren moi o:",
    round(mean_poi, 2)
)

print("Tong POI duoc gan vao luoi:", total_poi)


# =====================================================
# 13. THỐNG KÊ PHÂN BỐ MẬT ĐỘ
# =====================================================

print("\n========== PHAN BO MAT DO ==========")

density_order = [
    "Khong co POI",
    "Thap",
    "Trung binh",
    "Cao",
    "Rat cao"
]

density_summary = (
    grid_stats["density_level"]
    .value_counts()
)

for level in density_order:

    count = int(
        density_summary.get(level, 0)
    )

    percentage = (
        count / total_cells * 100
        if total_cells > 0
        else 0
    )

    print(
        f"{level}: {count} o "
        f"({percentage:.2f}%)"
    )


# =====================================================
# 14. THỐNG KÊ THEO SÁU DANH MỤC
# =====================================================

print("\n========== POI THEO DANH MUC ==========")

for category, category_name in CATEGORY_NAMES.items():

    category_total = int(
        grid_stats[category].sum()
    )

    category_cells = int(
        (grid_stats[category] > 0).sum()
    )

    print(
        f"{category_name}: "
        f"{category_total} POI, "
        f"phan bo tren {category_cells} o luoi"
    )


# =====================================================
# 15. PHÂN TÍCH MỨC ĐỘ TẬP TRUNG
# =====================================================

print("\n========== MUC DO TAP TRUNG ==========")

ranked_grid = grid_stats.sort_values(
    "total_poi",
    ascending=False
)

top_2 = int(
    ranked_grid.head(2)["total_poi"].sum()
)

top_5 = int(
    ranked_grid.head(5)["total_poi"].sum()
)

if total_poi > 0:

    print(
        "Top 2 o luoi:",
        top_2,
        "POI -",
        round(top_2 / total_poi * 100, 2),
        "%"
    )

    print(
        "Top 5 o luoi:",
        top_5,
        "POI -",
        round(top_5 / total_poi * 100, 2),
        "%"
    )


print("\n========== 10 O LUOI CO NHIEU POI NHAT ==========")

print(
    ranked_grid[
        [
            "cell_id",
            "total_poi",
            "poi_density_per_km2",
            "density_level"
        ]
    ].head(10).to_string(index=False)
)


# =====================================================
# 16. THỐNG KÊ Ô KHÔNG CÓ POI
# =====================================================

print("\n========== O LUOI KHONG CO POI ==========")

empty_grid = grid_stats[
    grid_stats["total_poi"] == 0
]

print("So o khong co POI:", len(empty_grid))

if not empty_grid.empty:

    print(
        empty_grid[
            [
                "cell_id",
                "center_latitude",
                "center_longitude",
                "area_km2"
            ]
        ].head(20).to_string(index=False)
    )


# =====================================================
# 17. LƯU KẾT QUẢ CSV
# =====================================================

print("\nDang luu ket qua...")

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

grid_stats = grid_stats.sort_values(
    "total_poi",
    ascending=False
)

grid_stats.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =====================================================
# 18. KẾT QUẢ CUỐI CÙNG
# =====================================================

print("\n========== KET QUA ==========")

print("Tong POI dau vao:", len(pois))

print("POI hop le:", len(df))

print("Tong so o luoi:", total_cells)

print("O co POI:", occupied_cells)

print("O khong co POI:", empty_cells)

print(
    "Ty le phu:",
    round(coverage_rate, 2),
    "%"
)

print("Kich thuoc o luoi:", GRID_SIZE, "m")

print("He toa do:", TARGET_CRS)

print("File ket qua:", OUTPUT_FILE)

print("=============================")
