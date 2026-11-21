
import requests
import json
import os
import time

SERVERS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

QUERY = """
[out:json][timeout:120];
relation(19297407);
out geom;
"""

HEADERS = {
    "User-Agent": "DaNangSmartTravel/1.0 (student research project)",
    "Accept": "application/json"
}

def download_boundary():

    for server in SERVERS:

        print("\nDang ket noi:", server)

        for attempt in range(3):

            try:
                print(f"Lan thu {attempt + 1}/3")

                response = requests.post(
                    server,
                    data={"data": QUERY},
                    headers=HEADERS,
                    timeout=180
                )

                print("HTTP Status:", response.status_code)
                response.raise_for_status()

                data = response.json()
                elements = data.get("elements", [])

                if not elements:
                    print("Khong tim thay Relation.")
                    continue

                relation = elements[0]
                members = relation.get("members", [])

                way_count = 0
                geometry_count = 0

                print("\nID Relation:", relation.get("id"))
                print("Ten:", relation.get("tags", {}).get("name"))

                for member in members:

                    if member.get("type") == "way":

                        way_count += 1
                        geometry = member.get("geometry", [])

                        if geometry:
                            geometry_count += 1

                        print(
                            "Way:", member.get("ref"),
                            "| Role:", member.get("role"),
                            "| So toa do:", len(geometry)
                        )

                os.makedirs("data/raw", exist_ok=True)

                output_path = "data/raw/danang_old_boundary.json"

                with open(output_path, "w", encoding="utf-8") as file:
                    json.dump(
                        data,
                        file,
                        ensure_ascii=False,
                        indent=2
                    )

                print("\n========== KET QUA ==========")
                print("Tong so Way:", way_count)
                print("Way co geometry:", geometry_count)
                print("Da luu:", output_path)
                print("=============================")

                return True

            except requests.exceptions.RequestException as error:

                print("Loi:", error)

                if attempt < 2:
                    wait_time = 5 * (2 ** attempt)
                    print(f"Cho {wait_time} giay roi thu lai...")
                    time.sleep(wait_time)

        print("Chuyen sang server tiep theo...")

    print("\nKhong the tai du lieu tu cac server.")
    return False


if __name__ == "__main__":
    download_boundary()
