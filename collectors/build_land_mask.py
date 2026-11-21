
import json
import os
import zipfile
from datetime import datetime, timezone

import requests
import shapefile
import folium

from folium.plugins import MarkerCluster
from shapely.geometry import shape, mapping
from shapely.ops import unary_union


# ==================================================
# 1. KHAI BAO DUONG DAN
# ==================================================

BOUNDARY_FILE = "data/raw/danang_old_boundary.geojson"

# Natural Earth cu - chi dung de doi chieu
NATURAL_EARTH_MASK_FILE = (
    "data/raw/danang_old_land_mask.geojson"
)

# OSM Land Polygons
OSM_LAND_DIR = "data/raw/osm_land_polygons"
OSM_LAND_ZIP = "data/raw/land-polygons-split-4326.zip"
OSM_LAND_SHP = os.path.join(
    OSM_LAND_DIR,
    "land_polygons.shp"
)

# POI
POI_FILE = (
    "data/processed/osm_places_danang_old_full_inside.json"
)

# Dau ra moi - KHONG ghi de Natural Earth
OUTPUT_FILE = (
    "data/raw/danang_old_land_mask_osm.geojson"
)

INTERSECTION_FILE = (
    "data/processed/osm_land_polygon_intersections.geojson"
)

DIAGNOSTIC_MAP_FILE = (
    "data/processed/osm_land_mask_diagnostic.html"
)

OSM_LAND_URL = (
    "https://osmdata.openstreetmap.de/download/"
    "land-polygons-split-4326.zip"
)

HEADERS = {
    "User-Agent": (
        "DaNangSmartTravel/1.0 "
        "(student research project)"
    )
}

DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024


# ==================================================
# 2. TAI DU LIEU OSM LAND POLYGONS
# ==================================================

def find_shapefile(directory):

    if not os.path.isdir(directory):
        return None

    for root, _, files in os.walk(directory):

        for filename in files:

            if filename.lower() == "land_polygons.shp":

                return os.path.join(root, filename)

    return None


def download_osm_land_data():

    existing_shp = find_shapefile(OSM_LAND_DIR)

    if existing_shp:

        print("Da co OSM Land Polygons.")
        print("Shapefile:", existing_shp)

        return existing_shp

    os.makedirs(OSM_LAND_DIR, exist_ok=True)

    print("\n========== TAI OSM LAND POLYGONS ==========")
    print("Nguon:", OSM_LAND_URL)

    temp_zip = OSM_LAND_ZIP + ".part"

    try:

        with requests.get(
            OSM_LAND_URL,
            headers=HEADERS,
            stream=True,
            timeout=(30, 600)
        ) as response:

            response.raise_for_status()

            total_size = int(
                response.headers.get("Content-Length", 0)
            )

            downloaded = 0

            with open(temp_zip, "wb") as file:

                for chunk in response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE
                ):

                    if not chunk:
                        continue

                    file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:

                        percent = (
                            downloaded / total_size
                        ) * 100

                        print(
                            f"\rDa tai: {percent:.1f}% "
                            f"({downloaded / (1024 ** 2):.1f} MB)",
                            end=""
                        )

                    else:

                        print(
                            f"\rDa tai: "
                            f"{downloaded / (1024 ** 2):.1f} MB",
                            end=""
                        )

        print()

        if os.path.getsize(temp_zip) == 0:
            raise ValueError("File ZIP tai ve rong.")

        os.replace(temp_zip, OSM_LAND_ZIP)

        print("Da tai file:", OSM_LAND_ZIP)
        print(
            "Dung luong:",
            round(
                os.path.getsize(OSM_LAND_ZIP) / (1024 ** 2),
                2
            ),
            "MB"
        )

        print("\nDang kiem tra va giai nen Shapefile...")

        with zipfile.ZipFile(OSM_LAND_ZIP, "r") as zip_ref:

            members = zip_ref.namelist()

            shp_members = [
                name for name in members
                if name.lower().endswith("/land_polygons.shp")
                or name.lower() == "land_polygons.shp"
            ]

            if len(shp_members) != 1:

                raise FileNotFoundError(
                    "Khong tim thay duy nhat land_polygons.shp "
                    "trong file ZIP."
                )

            shp_member = shp_members[0]

            base_name = os.path.splitext(shp_member)[0]

            required_extensions = {
                ".shp",
                ".shx",
                ".dbf",
                ".prj",
                ".cpg"
            }

            extracted = []

            for member in members:

                member_base, extension = os.path.splitext(member)

                if (
                    member_base == base_name
                    and extension.lower() in required_extensions
                ):

                    target_path = os.path.join(
                        OSM_LAND_DIR,
                        "land_polygons" + extension.lower()
                    )

                    with zip_ref.open(member) as source:
                        with open(target_path, "wb") as target:

                            while True:

                                chunk = source.read(
                                    DOWNLOAD_CHUNK_SIZE
                                )

                                if not chunk:
                                    break

                                target.write(chunk)

                    extracted.append(
                        os.path.basename(target_path)
                    )

        print("Cac file da giai nen:", extracted)

        required_files = [
            OSM_LAND_SHP,
            os.path.join(OSM_LAND_DIR, "land_polygons.shx"),
            os.path.join(OSM_LAND_DIR, "land_polygons.dbf")
        ]

        for path in required_files:

            if not os.path.exists(path):

                raise FileNotFoundError(
                    f"Thieu thanh phan Shapefile: {path}"
                )

        print("Giai nen thanh cong.")

        return OSM_LAND_SHP

    except Exception as error:

        print("\nLOI TAI OSM LAND POLYGONS:", error)

        if os.path.exists(temp_zip):
            os.remove(temp_zip)

        raise


# ==================================================
# 3. DOC BOUNDARY
# ==================================================

def load_boundary():

    print("\nDang doc boundary...")

    if not os.path.exists(BOUNDARY_FILE):

        raise FileNotFoundError(
            f"Khong tim thay: {BOUNDARY_FILE}"
        )

    with open(
        BOUNDARY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    final_features = [
        feature
        for feature in data.get("features", [])
        if feature.get("properties", {}).get("layer") == "final"
    ]

    if len(final_features) != 1:

        raise ValueError(
            "Boundary phai co dung mot feature layer='final'."
        )

    feature = final_features[0]

    boundary = shape(feature["geometry"])

    if boundary.is_empty or not boundary.is_valid:

        raise ValueError(
            "Boundary rong hoac khong hop le."
        )

    if boundary.geom_type not in [
        "Polygon",
        "MultiPolygon"
    ]:

        raise ValueError(
            "Boundary khong phai Polygon/MultiPolygon."
        )

    print("Ten:", feature["properties"].get("name"))
    print("Geometry:", boundary.geom_type)
    print("Bounds:", boundary.bounds)
    print("Area:", boundary.area)

    return boundary, feature["properties"]


# ==================================================
# 4. HAM HO TRO HINH HOC
# ==================================================

def extract_polygons(geometry):

    polygons = []

    if geometry.is_empty:
        return polygons

    if geometry.geom_type == "Polygon":

        polygons.append(geometry)

    elif geometry.geom_type == "MultiPolygon":

        polygons.extend(list(geometry.geoms))

    elif geometry.geom_type == "GeometryCollection":

        for item in geometry.geoms:

            polygons.extend(
                extract_polygons(item)
            )

    return polygons


def repair_geometry(geometry):

    if geometry.is_empty:
        return geometry

    if not geometry.is_valid:

        geometry = geometry.buffer(0)

    return geometry


def count_components(geometry):

    if geometry.geom_type == "Polygon":
        return 1

    if geometry.geom_type == "MultiPolygon":
        return len(geometry.geoms)

    if geometry.geom_type == "GeometryCollection":

        return sum(
            count_components(item)
            for item in geometry.geoms
        )

    return 0


# ==================================================
# 5. DOC OSM LAND POLYGONS TRONG KHU VUC
# ==================================================

def load_osm_land_polygons(boundary, shp_path):

    print("\n========== DOC OSM LAND POLYGONS ==========")

    reader = shapefile.Reader(
        shp_path,
        encoding="utf-8"
    )

    print("Shape type:", reader.shapeType)
    print("Tong so records:", len(reader))

    min_lon, min_lat, max_lon, max_lat = boundary.bounds

    candidate_count = 0
    intersection_count = 0
    invalid_count = 0
    empty_count = 0
    failed_count = 0

    clipped_polygons = []
    intersection_features = []

    for index, item in enumerate(reader.iterShapes()):

        # Bo qua polygon khong giao bounding box
        if not item.bbox:
            continue

        item_min_lon, item_min_lat, item_max_lon, item_max_lat = (
            item.bbox
        )

        if (
            item_max_lon < min_lon
            or item_min_lon > max_lon
            or item_max_lat < min_lat
            or item_min_lat > max_lat
        ):

            continue

        candidate_count += 1

        try:

            polygon = shape(item.__geo_interface__)

            if polygon.is_empty:

                empty_count += 1
                continue

            if not polygon.is_valid:

                invalid_count += 1
                polygon = repair_geometry(polygon)

            if polygon.is_empty:
                empty_count += 1
                continue

            source_polygons = extract_polygons(polygon)

            if not source_polygons:
                continue

            # Cat tung polygon theo boundary truoc khi union
            clipped_parts = []

            for source_polygon in source_polygons:

                intersection = source_polygon.intersection(
                    boundary
                )

                if intersection.is_empty:
                    continue

                clipped_parts.extend(
                    extract_polygons(intersection)
                )

            if not clipped_parts:
                continue

            clipped_geometry = unary_union(clipped_parts)

            if clipped_geometry.is_empty:
                continue

            if not clipped_geometry.is_valid:

                clipped_geometry = repair_geometry(
                    clipped_geometry
                )

            clipped_parts = extract_polygons(
                clipped_geometry
            )

            if not clipped_parts:
                continue

            intersection_count += 1

            clipped_polygons.extend(clipped_parts)

            intersection_features.append({
                "type": "Feature",
                "properties": {
                    "source_record": index,
                    "polygon_count": len(clipped_parts),
                    "clipped_area": clipped_geometry.area
                },
                "geometry": mapping(clipped_geometry)
            })

        except Exception as error:

            failed_count += 1

            print(
                f"Canh bao record {index}: {error}"
            )

    reader.close()

    print("\n--- THONG KE DOC DU LIEU ---")
    print("Records trong bounding box:", candidate_count)
    print("Records co phan giao voi boundary:", intersection_count)
    print("So polygon sau khi cat:", len(clipped_polygons))
    print("Geometry khong hop le ban dau:", invalid_count)
    print("Geometry rong:", empty_count)
    print("Records gap loi:", failed_count)
    print("==========================================")

    if not clipped_polygons:

        raise ValueError(
            "Khong tim thay land polygon giao voi boundary. "
            "Can kiem tra CRS va du lieu Shapefile."
        )

    return clipped_polygons, intersection_features


# ==================================================
# 6. GHEP LAND MASK
# ==================================================

def build_land_mask(boundary, clipped_polygons):

    print("\nDang ghep cac polygon da cat...")

    land_mask = unary_union(clipped_polygons)

    if land_mask.is_empty:

        raise ValueError(
            "Land mask rong sau khi union."
        )

    if not land_mask.is_valid:

        land_mask = repair_geometry(land_mask)

    polygons = extract_polygons(land_mask)

    if not polygons:

        raise ValueError(
            "Khong tim thay Polygon trong land mask."
        )

    land_mask = unary_union(polygons)

    if land_mask.is_empty or not land_mask.is_valid:

        raise ValueError(
            "Land mask cuoi cung khong hop le."
        )

    # Kiem tra lai sau union
    outside = land_mask.difference(boundary)

    print("\n========== KET QUA LAND MASK ==========")
    print("Geometry:", land_mask.geom_type)
    print("Components:", count_components(land_mask))
    print("Area:", land_mask.area)
    print("Bounds:", land_mask.bounds)
    print("Valid:", land_mask.is_valid)
    print("Empty:", land_mask.is_empty)

    print("\n--- KIEM TRA VOI BOUNDARY ---")
    print("Outside empty:", outside.is_empty)
    print("Outside area:", outside.area)
    print(
        "Boundary covers land mask:",
        boundary.covers(land_mask)
    )
    print(
        "Boundary buffered covers:",
        boundary.buffer(1e-9).covers(land_mask)
    )

    print("======================================")

    return land_mask


# ==================================================
# 7. LUU GEOJSON
# ==================================================

def save_geojson(
    output_path,
    geometry,
    properties
):

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geometry)
            }
        ]
    }

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            geojson,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Da luu:", output_path)


def save_intersection_features(features):

    geojson = {
        "type": "FeatureCollection",
        "name": "OSM Land Polygon Intersections",
        "features": features
    }

    os.makedirs(
        os.path.dirname(INTERSECTION_FILE),
        exist_ok=True
    )

    with open(
        INTERSECTION_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            geojson,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Da luu:", INTERSECTION_FILE)


# ==================================================
# 8. DOC NATURAL EARTH DE DOI CHIEU
# ==================================================

def load_natural_earth_mask():

    if not os.path.exists(NATURAL_EARTH_MASK_FILE):

        print(
            "\nKhong co Natural Earth mask de doi chieu."
        )

        return None

    try:

        with open(
            NATURAL_EARTH_MASK_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        features = data.get("features", [])

        if not features:
            return None

        geometry = shape(features[0]["geometry"])

        if geometry.is_empty:
            return None

        return geometry

    except Exception as error:

        print(
            "Khong doc duoc Natural Earth mask:",
            error
        )

        return None


# ==================================================
# 9. DOC POI
# ==================================================

def load_pois():

    if not os.path.exists(POI_FILE):

        print("Khong tim thay POI file.")
        return []

    with open(
        POI_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if isinstance(data, list):

        return data

    if isinstance(data, dict):

        return data.get("places", [])

    return []


def get_poi_coordinates(poi):

    lat = poi.get(
        "lat",
        poi.get("latitude")
    )

    lon = poi.get(
        "lon",
        poi.get(
            "lng",
            poi.get("longitude")
        )
    )

    if lat is not None and lon is not None:

        return lat, lon

    center = poi.get("center")

    if isinstance(center, dict):

        return (
            center.get("lat"),
            center.get("lon")
        )

    return None, None


# ==================================================
# 10. TAO BAN DO SO SANH
# ==================================================

def create_diagnostic_map(
    boundary,
    osm_mask,
    natural_earth_mask
):

    print("\nDang tao ban do so sanh...")

    center = boundary.centroid

    map_object = folium.Map(
        location=[center.y, center.x],
        zoom_start=11,
        tiles="OpenStreetMap"
    )

    # Boundary
    boundary_layer = folium.FeatureGroup(
        name="Old Da Nang Boundary",
        show=True
    )

    folium.GeoJson(
        data=mapping(boundary),
        name="Old Da Nang Boundary",
        style_function=lambda feature: {
            "color": "red",
            "weight": 3,
            "fill": False,
            "fillOpacity": 0
        }
    ).add_to(boundary_layer)

    boundary_layer.add_to(map_object)

    # OSM mask
    osm_layer = folium.FeatureGroup(
        name="OSM Land Mask",
        show=True
    )

    folium.GeoJson(
        data=mapping(osm_mask),
        name="OSM Land Mask",
        style_function=lambda feature: {
            "color": "#0066ff",
            "weight": 3,
            "fillColor": "#3388ff",
            "fillOpacity": 0.25
        }
    ).add_to(osm_layer)

    osm_layer.add_to(map_object)

    # Natural Earth mask
    if natural_earth_mask is not None:

        natural_layer = folium.FeatureGroup(
            name="Natural Earth Land Mask",
            show=False
        )

        folium.GeoJson(
            data=mapping(natural_earth_mask),
            name="Natural Earth Land Mask",
            style_function=lambda feature: {
                "color": "#ff8c00",
                "weight": 2,
                "fillColor": "#ff8c00",
                "fillOpacity": 0.25
            }
        ).add_to(natural_layer)

        natural_layer.add_to(map_object)

    # POI
    pois = load_pois()

    poi_layer = folium.FeatureGroup(
        name="POI",
        show=True
    )

    cluster = MarkerCluster()

    total_poi = 0
    inside_osm = 0
    outside_osm = 0
    invalid_poi = 0

    for poi in pois:

        lat, lon = get_poi_coordinates(poi)

        try:

            lat = float(lat)
            lon = float(lon)

        except (TypeError, ValueError):

            invalid_poi += 1
            continue

        if not (
            -90 <= lat <= 90
            and -180 <= lon <= 180
        ):

            invalid_poi += 1
            continue

        from shapely.geometry import Point

        point = Point(lon, lat)

        if osm_mask.covers(point):
            inside_osm += 1
        else:
            outside_osm += 1

        name = (
            poi.get("name")
            or poi.get("tags", {}).get("name")
            or "Unnamed POI"
        )

        folium.Marker(
            location=[lat, lon],
            popup=str(name),
            tooltip=str(name)
        ).add_to(cluster)

        total_poi += 1

    cluster.add_to(poi_layer)
    poi_layer.add_to(map_object)

    folium.LayerControl(
        collapsed=False
    ).add_to(map_object)

    map_object.fit_bounds([
        [boundary.bounds[1], boundary.bounds[0]],
        [boundary.bounds[3], boundary.bounds[2]]
    ])

    os.makedirs(
        os.path.dirname(DIAGNOSTIC_MAP_FILE),
        exist_ok=True
    )

    map_object.save(DIAGNOSTIC_MAP_FILE)

    print("\n========== THONG KE POI ==========")
    print("Tong POI:", total_poi)
    print("POI trong OSM land mask:", inside_osm)
    print("POI ngoai OSM land mask:", outside_osm)
    print("POI toa do khong hop le:", invalid_poi)
    print("==================================")

    print(
        "Da luu ban do:",
        DIAGNOSTIC_MAP_FILE
    )


# ==================================================
# 11. MAIN
# ==================================================

def main():

    print("========== BUILD OSM LAND MASK ==========")

    # Buoc 1: Tai va giai nen OSM Land Polygons
    shp_path = download_osm_land_data()

    # Buoc 2: Doc boundary
    boundary, boundary_properties = load_boundary()

    # Buoc 3: Doc va cat OSM land polygons
    (
        clipped_polygons,
        intersection_features
    ) = load_osm_land_polygons(
        boundary,
        shp_path
    )

    # Buoc 4: Ghep land mask
    osm_mask = build_land_mask(
        boundary,
        clipped_polygons
    )

    # Buoc 5: Luu OSM mask moi
    metadata = {
        "name": boundary_properties.get("name"),
        "relation_id": boundary_properties.get("relation_id"),
        "source": "OpenStreetMap contributors",
        "source_dataset": "OSM Land Polygons Split WGS84",
        "source_url": OSM_LAND_URL,
        "license": "ODbL",
        "boundary_source": "OpenStreetMap",
        "layer": "land_mask_osm",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "description": (
            "OSM land polygons clipped by the old Da Nang "
            "study boundary. Includes mapped mainland and islands."
        ),
        "attribution": "© OpenStreetMap contributors"
    }

    save_geojson(
        OUTPUT_FILE,
        osm_mask,
        metadata
    )

    # Buoc 6: Luu tung polygon giao voi boundary
    save_intersection_features(
        intersection_features
    )

    # Buoc 7: Doc Natural Earth de so sanh
    natural_earth_mask = load_natural_earth_mask()

    # Buoc 8: Tao ban do
    create_diagnostic_map(
        boundary,
        osm_mask,
        natural_earth_mask
    )

    print("\n========== KET QUA ==========")
    print("Trang thai: Thanh cong")
    print("OSM Land Mask:", OUTPUT_FILE)
    print("Intersections:", INTERSECTION_FILE)
    print("Diagnostic map:", DIAGNOSTIC_MAP_FILE)
    print("Natural Earth goc duoc giu nguyen.")
    print("=============================")


if __name__ == "__main__":
    main()
