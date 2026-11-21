
import json
import os

from shapely.geometry import LineString, mapping
from shapely.ops import unary_union, polygonize


# ==========================================
# 1. KHAI BAO DUONG DAN
# ==========================================

INPUT_FILE = "data/raw/danang_old_boundary.json"
OUTPUT_FILE = "data/raw/danang_old_boundary.geojson"


# ==========================================
# 2. DOC DU LIEU RELATION
# ==========================================

def load_relation():

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    elements = data.get("elements", [])

    relation = next(
        (
            element for element in elements
            if element.get("type") == "relation"
        ),
        None
    )

    if relation is None:
        raise ValueError("Khong tim thay Relation trong file JSON.")

    return relation


# ==========================================
# 3. TAO DUONG LINESTRING
# ==========================================

def create_lines(members, role):

    lines = []

    for member in members:

        if member.get("type") != "way":
            continue

        if member.get("role") != role:
            continue

        geometry = member.get("geometry", [])

        coordinates = [
            (point["lon"], point["lat"])
            for point in geometry
        ]

        if len(coordinates) >= 2:

            line = LineString(coordinates)

            if line.is_valid and not line.is_empty:
                lines.append(line)

    return lines


# ==========================================
# 4. TAO POLYGON
# ==========================================

def build_polygon(lines, label):

    if not lines:
        print(f"Khong co duong bao {label}.")
        return []

    merged = unary_union(lines)
    polygons = list(polygonize(merged))

    print(f"So polygon {label} tao duoc:", len(polygons))

    return polygons


# ==========================================
# 5. KIEM TRA HINH HOC
# ==========================================

def inspect_geometry(
    outer_area,
    inner_area,
    outer_polygons,
    inner_polygons,
    final_geometry
):

    print("\n========== KIEM TRA CHI TIET ==========")

    print("So polygon outer:", len(outer_polygons))
    print("So polygon inner:", len(inner_polygons))

    print("\n--- Outer ---")
    print("Geometry type:", outer_area.geom_type)
    print("Is valid:", outer_area.is_valid)
    print("Is empty:", outer_area.is_empty)
    print("Area:", outer_area.area)

    print("\n--- Inner ---")

    if inner_area is not None:

        print("Geometry type:", inner_area.geom_type)
        print("Is valid:", inner_area.is_valid)
        print("Is empty:", inner_area.is_empty)
        print("Area:", inner_area.area)
        print("Inner nam trong outer:", outer_area.covers(inner_area))
        print("Inner giao voi outer:", outer_area.intersects(inner_area))

        outside_inner = inner_area.difference(outer_area)

        print("Dien tich inner nam ngoai outer:", outside_inner.area)

    else:

        print("Khong co polygon inner.")

    print("\n--- Final Geometry ---")

    print("Geometry type:", final_geometry.geom_type)
    print("Is valid:", final_geometry.is_valid)
    print("Is empty:", final_geometry.is_empty)
    print("Area:", final_geometry.area)
    print("Bounds:", final_geometry.bounds)

    if final_geometry.geom_type == "Polygon":

        print("So polygon thanh phan: 1")
        print("So lo:", len(final_geometry.interiors))

    elif final_geometry.geom_type == "MultiPolygon":

        print("So polygon thanh phan:", len(final_geometry.geoms))

        print(
            "Tong so lo:",
            sum(len(polygon.interiors) for polygon in final_geometry.geoms)
        )

    print("========================================")


# ==========================================
# 6. XUAT GEOJSON
# ==========================================

def save_geojson(
    relation,
    final_geometry,
    outer_area,
    inner_area,
    outer_lines,
    inner_lines
):

    tags = relation.get("tags", {})

    common_properties = {
        "relation_id": relation.get("id"),
        "name": tags.get("name"),
        "source": "OpenStreetMap",
        "boundary": tags.get("boundary"),
        "end_date": tags.get("end_date"),
        "outer_way_count": len(outer_lines),
        "inner_way_count": len(inner_lines)
    }

    features = [
        {
            "type": "Feature",
            "properties": {
                **common_properties,
                "layer": "final",
                "description": "Polygon sau khi loai tru inner"
            },
            "geometry": mapping(final_geometry)
        },
        {
            "type": "Feature",
            "properties": {
                **common_properties,
                "layer": "outer",
                "description": "Vung outer ban dau"
            },
            "geometry": mapping(outer_area)
        }
    ]

    if inner_area is not None:

        features.append({
            "type": "Feature",
            "properties": {
                **common_properties,
                "layer": "inner",
                "description": "Vung inner bi loai tru"
            },
            "geometry": mapping(inner_area)
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    os.makedirs("data/raw", exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            geojson,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\nDa luu polygon tai:", OUTPUT_FILE)
    print("So feature trong GeoJSON:", len(features))


# ==========================================
# 7. MAIN
# ==========================================

def main():

    print("Dang doc du lieu ranh gioi...")

    relation = load_relation()
    members = relation.get("members", [])

    print("\n========== THONG TIN RELATION ==========")

    print("Relation ID:", relation.get("id"))
    print("Ten:", relation.get("tags", {}).get("name"))
    print("Boundary:", relation.get("tags", {}).get("boundary"))
    print("End date:", relation.get("tags", {}).get("end_date"))

    outer_lines = create_lines(members, "outer")
    inner_lines = create_lines(members, "inner")

    print("\n========== THONG KE DUONG BAO ==========")

    print("So duong outer:", len(outer_lines))
    print("So duong inner:", len(inner_lines))

    outer_polygons = build_polygon(outer_lines, "outer")
    inner_polygons = build_polygon(inner_lines, "inner")

    if not outer_polygons:
        print("Khong tao duoc polygon outer.")
        return

    outer_area = unary_union(outer_polygons)

    if not outer_area.is_valid or outer_area.is_empty:
        print("Outer geometry khong hop le.")
        return

    inner_area = None

    if inner_polygons:

        inner_area = unary_union(inner_polygons)

        if not inner_area.is_valid or inner_area.is_empty:
            print("Inner geometry khong hop le.")
            return

        # Khong tiep tuc neu inner nam ngoai outer
        if not outer_area.covers(inner_area):
            print("LOI: Inner khong nam hoan toan trong outer.")
            print("Khong xuat GeoJSON de tranh sai lech ranh gioi.")
            return

        final_geometry = outer_area.difference(inner_area)

    else:

        final_geometry = outer_area

    inspect_geometry(
        outer_area,
        inner_area,
        outer_polygons,
        inner_polygons,
        final_geometry
    )

    if not final_geometry.is_valid:
        print("Loi: Final geometry khong hop le.")
        return

    if final_geometry.is_empty:
        print("Loi: Final geometry rong.")
        return

    if final_geometry.geom_type not in ["Polygon", "MultiPolygon"]:
        print("Loi: Geometry khong phai Polygon/MultiPolygon.")
        return

    save_geojson(
        relation,
        final_geometry,
        outer_area,
        inner_area,
        outer_lines,
        inner_lines
    )

    print("\n========== KET QUA ==========")
    print("Dien tich:", final_geometry.area)
    print("Bounds:", final_geometry.bounds)
    print("Geometry type:", final_geometry.geom_type)
    print("Trang thai: Thanh cong")
    print("=============================")


if __name__ == "__main__":
    main()
