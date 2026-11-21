
import requests
import json
import os
import time

# ==========================================
# 1. CAU HINH OPENSTREETMAP
# ==========================================

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

# Relation ranh gioi Da Nang cu
BOUNDARY_RELATION_ID = 19297407

# File dau ra moi, khong ghi de du lieu thu thap ban dau
OUTPUT_FILE = "data/raw/osm_places_danang_old_full.json"

HEADERS = {
    "User-Agent": "DaNangSmartTravel/1.0 (student research project)",
    "Accept": "application/json"
}

REQUEST_TIMEOUT = 240
MAX_ATTEMPTS = 2


# ==========================================
# 2. TRUY VAN POI THEO RANH GIOI
# ==========================================

QUERY = f"""
[out:json][timeout:180];

relation({BOUNDARY_RELATION_ID});
map_to_area->.searchArea;

(
    // 1. THAM QUAN, DU LICH
    nwr(area.searchArea)["tourism"~"attraction|museum|gallery|viewpoint|zoo|aquarium|theme_park|artwork|information"];

    // 2. LUU TRU
    nwr(area.searchArea)["tourism"~"hotel|motel|guest_house|hostel|apartment|chalet|camp_site|resort"];

    // 3. AN UONG
    nwr(area.searchArea)["amenity"~"restaurant|cafe|fast_food|food_court|ice_cream|bar|pub|biergarten"];

    // 4. BAI BIEN VA DIA DIEM TU NHIEN
    nwr(area.searchArea)["natural"~"beach|peak|water|cave|hot_spring"];

    // 5. MUA SAM
    nwr(area.searchArea)["shop"~"mall|department_store|supermarket|clothes|gift|souvenir|convenience|market|bakery"];

    // 6. GIAI TRI VA VUI CHOI
    nwr(area.searchArea)["amenity"~"cinema|theatre|arts_centre|nightclub|casino|community_centre"];

    nwr(area.searchArea)["leisure"~"water_park|amusement_arcade|sports_centre|stadium|park|garden|playground|miniature_golf|golf_course|marina"];

    // 7. DI TICH VA DIA DIEM LICH SU
    nwr(area.searchArea)["historic"~"castle|monument|memorial|archaeological_site|fort|ruins|wayside_shrine"];

    // 8. CHO VA CAC DIEM CONG CONG
    nwr(area.searchArea)["amenity"="marketplace"];

    // 9. TON GIAO VA CONG TRINH VAN HOA
    nwr(area.searchArea)["amenity"="place_of_worship"];

);

out center tags;
"""


# ==========================================
# 3. GUI REQUEST VA THU LAI KHI LOI
# ==========================================

def fetch_osm_data():

    for server in OVERPASS_SERVERS:

        print("\nDang ket noi:", server)

        for attempt in range(1, MAX_ATTEMPTS + 1):

            try:
                print(f"Lan thu {attempt}/{MAX_ATTEMPTS}")

                response = requests.post(
                    server,
                    data={"data": QUERY},
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT
                )

                print("HTTP Status:", response.status_code)

                if response.status_code == 200:

                    result = response.json()

                    if "elements" not in result:
                        print("Du lieu tra ve khong co danh sach elements.")
                        continue

                    print(
                        "So doi tuong OSM thu duoc:",
                        len(result["elements"])
                    )

                    return result

                if response.status_code in [429, 502, 503, 504]:

                    wait_time = 10 * (2 ** (attempt - 1))

                    print("Server dang qua tai.")
                    print(f"Cho {wait_time} giay...")

                    time.sleep(wait_time)
                    continue

                print("Noi dung loi:", response.text[:1000])
                response.raise_for_status()

            except requests.exceptions.Timeout:

                print("Request bi timeout.")

                if attempt < MAX_ATTEMPTS:
                    time.sleep(10 * attempt)

            except requests.exceptions.RequestException as error:

                print("Loi ket noi:", error)

                if attempt < MAX_ATTEMPTS:
                    time.sleep(10 * attempt)

            except ValueError as error:

                print("Khong doc duoc JSON:", error)

                if attempt < MAX_ATTEMPTS:
                    time.sleep(5)

        print("Chuyen sang server tiep theo...")

        time.sleep(3)

    return None


# ==========================================
# 4. XU LY DIA CHI
# ==========================================

def get_address(tags):

    address_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:district"),
        tags.get("addr:city")
    ]

    address = ", ".join(
        str(part).strip()
        for part in address_parts
        if part
    )

    if not address:
        address = tags.get("addr:full")

    return address


# ==========================================
# 5. CHUAN HOA DU LIEU POI
# ==========================================

def normalize_place(item):

    tags = item.get("tags", {})

    # Lay toa do:
    # Node: lay truc tiep lat/lon
    # Way/Relation: lay toa do center
    location = item.get("center", item)

    latitude = location.get("lat")
    longitude = location.get("lon")

    # Bo qua ban ghi khong co ten
    name = tags.get("name")

    if not name:
        return None, "missing_name"

    # Bo qua ban ghi khong co toa do
    if latitude is None or longitude is None:
        return None, "missing_coordinates"

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None, "invalid_coordinates"

    # Kiem tra gioi han toa do dia ly
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None, "invalid_coordinates"

    place = {
        "osm_id": item.get("id"),
        "osm_type": item.get("type"),

        "name": name,

        "latitude": latitude,
        "longitude": longitude,

        "address": get_address(tags),

        "phone": tags.get("phone"),
        "website": tags.get("website"),
        "email": tags.get("email"),

        "opening_hours": tags.get("opening_hours"),

        "tourism": tags.get("tourism"),
        "amenity": tags.get("amenity"),
        "natural": tags.get("natural"),
        "shop": tags.get("shop"),
        "leisure": tags.get("leisure"),
        "historic": tags.get("historic"),

        "price": tags.get("fee"),
        "description": tags.get("description"),

        # Giu toan bo tag goc de phuc vu phan loai sau nay
        "raw_tags": tags
    }

    return place, None


# ==========================================
# 6. THU THAP VA XU LY DU LIEU
# ==========================================

def collect_places():

    print("\n========== BAT DAU THU THAP ==========")

    data = fetch_osm_data()

    if data is None:
        print("Khong the lay du lieu tu Overpass API.")
        return None

    elements = data.get("elements", [])

    results = []

    seen_ids = set()

    stats = {
        "total_elements": len(elements),
        "missing_name": 0,
        "missing_coordinates": 0,
        "invalid_coordinates": 0,
        "duplicate_ids": 0,
        "valid_places": 0
    }

    for item in elements:

        place, error = normalize_place(item)

        if error:
            stats[error] += 1
            continue

        # Kiem tra trung ID OSM
        osm_key = (
            place["osm_type"],
            place["osm_id"]
        )

        if osm_key in seen_ids:
            stats["duplicate_ids"] += 1
            continue

        seen_ids.add(osm_key)

        results.append(place)

    stats["valid_places"] = len(results)

    print("\n========== THONG KE THU THAP ==========")

    print("Tong doi tuong OSM:", stats["total_elements"])
    print("POI hop le:", stats["valid_places"])
    print("Thieu ten:", stats["missing_name"])
    print("Thieu toa do:", stats["missing_coordinates"])
    print("Toa do khong hop le:", stats["invalid_coordinates"])
    print("ID OSM bi trung:", stats["duplicate_ids"])

    print("=======================================\n")

    return {
        "metadata": {
            "source": "OpenStreetMap",
            "boundary_relation_id": BOUNDARY_RELATION_ID,
            "collection_method": "Overpass API - administrative relation",
            "total_elements": stats["total_elements"],
            "total_valid_places": stats["valid_places"],
            "collection_time": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        },
        "statistics": stats,
        "places": results
    }


# ==========================================
# 7. LUU DU LIEU
# ==========================================

def save_data(data):

    os.makedirs("data/raw", exist_ok=True)

    output_path = OUTPUT_FILE

    # Khong ghi de file da ton tai
    if os.path.exists(output_path):

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        output_path = (
            f"data/raw/osm_places_danang_old_full_{timestamp}.json"
        )

    with open(output_path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("Da luu du lieu tai:", output_path)

    return output_path


# ==========================================
# 8. KIEM TRA PHAM VI TOA DO
# ==========================================

def inspect_coordinates(places):

    if not places:
        print("Khong co POI de kiem tra toa do.")
        return

    latitudes = [
        place["latitude"]
        for place in places
    ]

    longitudes = [
        place["longitude"]
        for place in places
    ]

    print("\n========== PHAM VI TOA DO ==========")

    print("Latitude min:", min(latitudes))
    print("Latitude max:", max(latitudes))

    print("Longitude min:", min(longitudes))
    print("Longitude max:", max(longitudes))

    print("====================================")


# ==========================================
# 9. CHUONG TRINH CHINH
# ==========================================

if __name__ == "__main__":

    start_time = time.time()

    data = collect_places()

    if data is not None:

        places = data["places"]

        output_path = save_data(data)

        inspect_coordinates(places)

        print("\n========== KET QUA CUOI CUNG ==========")

        print("Tong so POI:", len(places))

        print(
            "Thoi gian thu thap:",
            round(time.time() - start_time, 2),
            "giay"
        )

        print("File:", output_path)

        print("=======================================")

    else:

        print("\nThu thap that bai.")
        print("Kiem tra lai ket noi Overpass API.")
