
import json
import html
from pathlib import Path

import folium
from folium.plugins import MarkerCluster

from shapely.geometry import shape, Point
from shapely.ops import transform
from pyproj import Transformer


# ============================================================
# 1. KHAI BÁO ĐƯỜNG DẪN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

BOUNDARY_FILE = (
    BASE_DIR / "data" / "raw" / "danang_old_boundary.geojson"
)

LAND_MASK_FILE = (
    BASE_DIR / "data" / "raw" / "danang_old_land_mask.geojson"
)

POI_FILE = (
    BASE_DIR / "data" / "processed"
    / "osm_places_danang_old_full_inside.json"
)

OUTPUT_MAP = (
    BASE_DIR / "data" / "processed"
    / "danang_old_poi_map.html"
)

OUTPUT_OUTSIDE_LAND = (
    BASE_DIR / "data" / "processed"
    / "poi_outside_land_mask_distance.json"
)

OUTPUT_REPORT = (
    BASE_DIR / "data" / "processed"
    / "land_mask_analysis_report.json"
)


# Hệ tọa độ UTM Zone 48N phù hợp với khu vực Đà Nẵng
TRANSFORMER = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32648",
    always_xy=True
)


# ============================================================
# 2. ĐỌC DỮ LIỆU
# ============================================================

def load_geojson(path):
    """Đọc dữ liệu GeoJSON."""

    if not path.exists():
        raise FileNotFoundError(
            f"Khong tim thay file: {path}"
        )

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_boundary(path):
    """
    Lấy geometry có layer = final từ file boundary GeoJSON.
    """

    geojson = load_geojson(path)

    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})

        if properties.get("layer") == "final":
            return shape(feature["geometry"])

    raise ValueError(
        "Khong tim thay feature co layer = final trong boundary."
    )


def load_land_mask(path):
    """
    Đọc land mask từ GeoJSON.
    """

    geojson = load_geojson(path)

    features = geojson.get("features", [])

    if not features:
        raise ValueError("Land mask GeoJSON khong co feature.")

    for feature in features:
        properties = feature.get("properties", {})

        if properties.get("layer") == "land_mask":
            return shape(feature["geometry"])

    # Trường hợp file chỉ có một feature
    if len(features) == 1:
        return shape(features[0]["geometry"])

    raise ValueError(
        "Khong tim thay feature co layer = land_mask."
    )


def load_pois(path):
    """
    Đọc danh sách POI.

    Hỗ trợ:
    - JSON dạng {"places": [...]}
    - JSON dạng {"data": [...]}
    - JSON dạng danh sách [...]
    """

    data = load_geojson(path)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["places", "data", "pois", "elements"]:
            if isinstance(data.get(key), list):
                return data[key]

    raise ValueError(
        "Khong xac dinh duoc danh sach POI trong file JSON."
    )


# ============================================================
# 3. LẤY THÔNG TIN POI
# ============================================================

def get_coordinates(poi):
    """
    Lấy latitude và longitude.

    Hỗ trợ các dạng dữ liệu phổ biến:
    - lat, lon
    - latitude, longitude
    - center.lat, center.lon
    - geometry.coordinates
    """

    lat = None
    lon = None

    if not isinstance(poi, dict):
        return None, None

    # Trường hợp 1: lat, lon
    if poi.get("lat") is not None and poi.get("lon") is not None:
        lat = poi.get("lat")
        lon = poi.get("lon")

    # Trường hợp 2: latitude, longitude
    elif (
        poi.get("latitude") is not None
        and poi.get("longitude") is not None
    ):
        lat = poi.get("latitude")
        lon = poi.get("longitude")

    # Trường hợp 3: center
    elif isinstance(poi.get("center"), dict):
        center = poi["center"]

        lat = center.get("lat")
        lon = center.get("lon")

    # Trường hợp 4: geometry.coordinates
    elif isinstance(poi.get("geometry"), dict):
        coordinates = poi["geometry"].get("coordinates")

        if (
            isinstance(coordinates, (list, tuple))
            and len(coordinates) >= 2
        ):
            lon = coordinates[0]
            lat = coordinates[1]

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None

    return lat, lon


def get_raw_tags(poi):
    """
    Lấy tags gốc của POI.
    """

    if not isinstance(poi, dict):
        return {}

    tags = poi.get("tags")

    if isinstance(tags, dict):
        return tags

    raw_tags = poi.get("raw_tags")

    if isinstance(raw_tags, dict):
        return raw_tags

    return {}


def get_poi_name(poi):
    return (
        poi.get("name")
        or poi.get("tags", {}).get("name")
        or "Unnamed POI"
    )


def get_osm_identity(poi):
    """
    Lấy OSM type và ID.
    """

    osm_type = (
        poi.get("osm_type")
        or poi.get("type")
        or poi.get("osm", {}).get("type")
    )

    osm_id = (
        poi.get("osm_id")
        or poi.get("id")
        or poi.get("osm", {}).get("id")
    )

    return osm_type, osm_id


def get_poi_group(poi):
    """
    Phân nhóm POI theo tag OSM gốc.

    Thứ tự ưu tiên:
    tourism -> amenity -> shop -> natural -> leisure -> historic
    """

    tags = get_raw_tags(poi)

    priorities = [
        "tourism",
        "amenity",
        "shop",
        "natural",
        "leisure",
        "historic"
    ]

    for key in priorities:
        if tags.get(key):
            return key

    return "other"


# ============================================================
# 4. THÔNG TIN TỔNG QUAN GEOMETRY
# ============================================================

def inspect_geometry(boundary, land_mask):
    print("\n========== THONG TIN BOUNDARY ==========")

    print("Boundary type:", boundary.geom_type)
    print("Boundary valid:", boundary.is_valid)
    print("Boundary area:", boundary.area)
    print("Boundary bounds:", boundary.bounds)

    print("\n========== THONG TIN LAND MASK ==========")

    print("Land mask type:", land_mask.geom_type)
    print("Land mask valid:", land_mask.is_valid)
    print("Land mask area:", land_mask.area)
    print("Land mask bounds:", land_mask.bounds)

    outside_geometry = land_mask.difference(boundary)

    print("\n========== KIEM TRA LAND MASK ==========")

    print("Outside empty:", outside_geometry.is_empty)
    print("Outside type:", outside_geometry.geom_type)
    print("Outside area:", outside_geometry.area)
    print("Outside length:", outside_geometry.length)

    print(
        "Boundary covers land mask:",
        boundary.covers(land_mask)
    )

    print(
        "Boundary buffered covers land mask:",
        boundary.buffer(1e-9).covers(land_mask)
    )


# ============================================================
# 5. KIỂM TRA TỌA ĐỘ POI
# ============================================================

def inspect_poi_positions(boundary, land_mask, pois):
    """
    Thống kê POI trong/ngoài boundary và land mask.
    """

    print("\n========== KIEM TRA VI TRI POI ==========")

    total = len(pois)

    inside_boundary = 0
    outside_boundary = 0

    inside_land = 0
    outside_land = 0

    invalid_coordinates = 0

    outside_land_by_group = {}

    outside_boundary_list = []
    outside_land_list = []

    for poi in pois:
        lat, lon = get_coordinates(poi)

        if lat is None or lon is None:
            invalid_coordinates += 1
            continue

        point = Point(lon, lat)

        # Kiểm tra boundary
        if boundary.covers(point):
            inside_boundary += 1
        else:
            outside_boundary += 1

            outside_boundary_list.append({
                "name": get_poi_name(poi),
                "latitude": lat,
                "longitude": lon
            })

        # Kiểm tra land mask
        if land_mask.covers(point):
            inside_land += 1
        else:
            outside_land += 1

            group = get_poi_group(poi)

            outside_land_by_group[group] = (
                outside_land_by_group.get(group, 0) + 1
            )

            outside_land_list.append(poi)

    print("Total POI:", total)

    print("\n--- Boundary ---")
    print("Inside boundary:", inside_boundary)
    print("Outside boundary:", outside_boundary)

    print("\n--- Land mask ---")
    print("Inside land mask:", inside_land)
    print("Outside land mask:", outside_land)

    print("\n--- Invalid coordinates ---")
    print("Invalid coordinates:", invalid_coordinates)

    print("\n--- Outside land mask by OSM group ---")

    for group, count in sorted(
        outside_land_by_group.items(),
        key=lambda item: item[1],
        reverse=True
    ):
        print(f"{group}: {count}")

    return {
        "total_poi": total,
        "inside_boundary": inside_boundary,
        "outside_boundary": outside_boundary,
        "inside_land_mask": inside_land,
        "outside_land_mask": outside_land,
        "invalid_coordinates": invalid_coordinates,
        "outside_land_by_group": outside_land_by_group,
        "outside_land_pois": outside_land_list,
        "outside_boundary_pois": outside_boundary_list
    }


# ============================================================
# 6. PHÂN TÍCH KHOẢNG CÁCH POI NGOÀI LAND MASK
# ============================================================

def inspect_all_outside_pois(land_mask, pois):
    """
    Tính khoảng cách từ từng POI ngoài land mask
    đến phần đất gần nhất.

    Khoảng cách tính bằng mét trên hệ tọa độ EPSG:32648.
    """

    print(
        "\n========== PHAN TICH KHOANG CACH POI "
        "NGOAI LAND MASK =========="
    )

    # Chuyển land mask sang UTM 48N
    land_mask_utm = transform(
        TRANSFORMER.transform,
        land_mask
    )

    outside_pois = []

    for poi in pois:
        lat, lon = get_coordinates(poi)

        if lat is None or lon is None:
            continue

        point = Point(lon, lat)

        # Chỉ phân tích POI nằm ngoài land mask
        if land_mask.covers(point):
            continue

        point_utm = transform(
            TRANSFORMER.transform,
            point
        )

        distance_m = point_utm.distance(land_mask_utm)

        osm_type, osm_id = get_osm_identity(poi)

        outside_pois.append({
            "name": get_poi_name(poi),
            "osm_type": osm_type,
            "osm_id": osm_id,
            "latitude": lat,
            "longitude": lon,
            "distance_m": round(distance_m, 2),
            "osm_group": get_poi_group(poi),
            "raw_tags": get_raw_tags(poi)
        })

    # Sắp xếp theo khoảng cách tăng dần
    outside_pois.sort(
        key=lambda item: item["distance_m"]
    )

    # Phân nhóm khoảng cách
    distance_groups = {
        "< 100 m": 0,
        "100 - 500 m": 0,
        "500 m - 1 km": 0,
        "1 - 5 km": 0,
        "> 5 km": 0
    }

    for poi in outside_pois:
        distance = poi["distance_m"]

        if distance < 100:
            distance_groups["< 100 m"] += 1

        elif distance < 500:
            distance_groups["100 - 500 m"] += 1

        elif distance < 1000:
            distance_groups["500 m - 1 km"] += 1

        elif distance < 5000:
            distance_groups["1 - 5 km"] += 1

        else:
            distance_groups["> 5 km"] += 1

    print("Total outside land mask:", len(outside_pois))

    print("\n--- Distance distribution ---")

    for group, count in distance_groups.items():
        percentage = (
            count / len(outside_pois) * 100
            if outside_pois else 0
        )

        print(
            f"{group}: {count} POI ({percentage:.2f}%)"
        )

    print("\n--- 30 POI nearest to land mask ---")

    for index, poi in enumerate(outside_pois[:30], start=1):
        print(
            f"{index}. {poi['name']} | "
            f"{poi['latitude']}, {poi['longitude']} | "
            f"{poi['distance_m']} m | "
            f"{poi['osm_group']}"
        )

    print("\n--- 30 POI farthest from land mask ---")

    for index, poi in enumerate(
        reversed(outside_pois[-30:]),
        start=1
    ):
        print(
            f"{index}. {poi['name']} | "
            f"{poi['latitude']}, {poi['longitude']} | "
            f"{poi['distance_m']} m | "
            f"{poi['osm_group']}"
        )

    # Xuất toàn bộ POI ngoài land mask
    OUTPUT_OUTSIDE_LAND.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_OUTSIDE_LAND,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            outside_pois,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nDa xuat danh sach POI ngoai land mask:",
        OUTPUT_OUTSIDE_LAND
    )

    return {
        "total_outside_land_mask": len(outside_pois),
        "distance_distribution": distance_groups,
        "outside_pois": outside_pois
    }


# ============================================================
# 7. TRỰC QUAN HÓA BẢN ĐỒ
# ============================================================

def visualize_map(boundary, land_mask, pois):
    """
    Tạo bản đồ Folium gồm:
    - Boundary
    - Land mask
    - POI theo nhóm OSM
    """

    print("\n========== TAO BAN DO ==========")

    center_lat = (
        boundary.centroid.y
    )

    center_lon = (
        boundary.centroid.x
    )

    map_object = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="OpenStreetMap"
    )

    # --------------------------------------------------------
    # Layer 1: Boundary cuối cùng
    # --------------------------------------------------------

    folium.GeoJson(
        data={
            "type": "Feature",
            "properties": {
                "name": "Da Nang Old Boundary"
            },
            "geometry": boundary.__geo_interface__
        },
        name="Old Da Nang Boundary",
        style_function=lambda feature: {
            "color": "red",
            "weight": 3,
            "fillColor": "red",
            "fillOpacity": 0.03
        },
        tooltip="Ranh gioi Da Nang cu"
    ).add_to(map_object)

    # --------------------------------------------------------
    # Layer 2: Land mask
    # --------------------------------------------------------

    folium.GeoJson(
        data={
            "type": "Feature",
            "properties": {
                "name": "Natural Earth Land Mask"
            },
            "geometry": land_mask.__geo_interface__
        },
        name="Land Mask",
        style_function=lambda feature: {
            "color": "green",
            "weight": 2,
            "fillColor": "green",
            "fillOpacity": 0.15
        },
        tooltip="Natural Earth Land Mask"
    ).add_to(map_object)

    # --------------------------------------------------------
    # Layer 3: POI theo nhóm
    # --------------------------------------------------------

    colors = {
        "tourism": "blue",
        "amenity": "red",
        "shop": "orange",
        "natural": "green",
        "leisure": "purple",
        "historic": "darkred",
        "other": "gray"
    }

    marker_clusters = {}

    for group in colors:
        marker_clusters[group] = MarkerCluster(
            name=f"POI - {group}"
        )

    for poi in pois:
        lat, lon = get_coordinates(poi)

        if lat is None or lon is None:
            continue

        name = get_poi_name(poi)
        group = get_poi_group(poi)

        color = colors.get(group, "gray")

        point = Point(lon, lat)

        inside_land = land_mask.covers(point)

        status = (
            "Inside land mask"
            if inside_land
            else "Outside land mask"
        )

        osm_type, osm_id = get_osm_identity(poi)

        tags = get_raw_tags(poi)

        popup_html = f"""
        <div style="width: 250px;">
            <b>{html.escape(str(name))}</b><br>
            <hr>
            OSM type: {html.escape(str(osm_type))}<br>
            OSM ID: {html.escape(str(osm_id))}<br>
            Group: {html.escape(str(group))}<br>
            Latitude: {lat}<br>
            Longitude: {lon}<br>
            Land mask: {status}<br>
            <hr>
            Raw tags:<br>
            <pre style="white-space: pre-wrap;">
{html.escape(json.dumps(tags, ensure_ascii=False, indent=2))}
            </pre>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=folium.Popup(
                popup_html,
                max_width=350
            ),
            tooltip=str(name)
        ).add_to(marker_clusters.get(group))

    # Thêm các cluster lên bản đồ
    for cluster in marker_clusters.values():
        cluster.add_to(map_object)

    # --------------------------------------------------------
    # Layer control
    # --------------------------------------------------------

    folium.LayerControl(
        collapsed=False
    ).add_to(map_object)

    # --------------------------------------------------------
    # Fit bounds
    # --------------------------------------------------------

    min_lon, min_lat, max_lon, max_lat = boundary.bounds

    map_object.fit_bounds([
        [min_lat, min_lon],
        [max_lat, max_lon]
    ])

    OUTPUT_MAP.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    map_object.save(str(OUTPUT_MAP))

    print("Da tao ban do:", OUTPUT_MAP)


# ============================================================
# 8. XUẤT BÁO CÁO PHÂN TÍCH
# ============================================================

def export_report(position_report, distance_report):
    """
    Xuất báo cáo tổng hợp kết quả kiểm tra.
    """

    report = {
        "boundary_analysis": {
            "total_poi": position_report["total_poi"],
            "inside_boundary": position_report["inside_boundary"],
            "outside_boundary": position_report["outside_boundary"]
        },

        "land_mask_analysis": {
            "inside_land_mask": position_report["inside_land_mask"],
            "outside_land_mask": position_report["outside_land_mask"],
            "outside_by_osm_group": position_report[
                "outside_land_by_group"
            ]
        },

        "distance_analysis": {
            "total_outside_land_mask": distance_report[
                "total_outside_land_mask"
            ],
            "distance_distribution": distance_report[
                "distance_distribution"
            ]
        },

        "notes": [
            (
                "Distance is measured from each outside POI "
                "to the nearest point of the land mask."
            ),
            (
                "Distance is calculated in EPSG:32648 "
                "and expressed in meters."
            ),
            (
                "Outside land mask does not automatically mean "
                "the POI is invalid."
            ),
            (
                "No POI has been automatically deleted "
                "or excluded."
            )
        ]
    }

    OUTPUT_REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\nDa xuat bao cao:", OUTPUT_REPORT)


# ============================================================
# 9. MAIN
# ============================================================

def main():

    print("============================================")
    print("   DANANG OLD - BOUNDARY & POI ANALYSIS")
    print("============================================")

    # 1. Đọc boundary
    print("\nDang doc boundary...")

    boundary = load_boundary(BOUNDARY_FILE)

    # 2. Đọc land mask
    print("\nDang doc land mask...")

    land_mask = load_land_mask(LAND_MASK_FILE)

    # 3. Đọc POI
    print("\nDang doc POI...")

    pois = load_pois(POI_FILE)

    print("Tong POI dau vao:", len(pois))

    # 4. Kiểm tra geometry
    inspect_geometry(
        boundary,
        land_mask
    )

    # 5. Kiểm tra vị trí POI
    position_report = inspect_poi_positions(
        boundary,
        land_mask,
        pois
    )

    # 6. Phân tích khoảng cách toàn bộ POI ngoài land mask
    distance_report = inspect_all_outside_pois(
        land_mask,
        pois
    )

    # 7. Trực quan hóa
    visualize_map(
        boundary,
        land_mask,
        pois
    )

    # 8. Xuất báo cáo
    export_report(
        position_report,
        distance_report
    )

    print("\n============================================")
    print("   HOAN THANH PHAN TICH")
    print("============================================")


if __name__ == "__main__":
    main()
