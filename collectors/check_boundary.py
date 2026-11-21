
import requests

URL = "https://overpass-api.de/api/interpreter"

QUERY = """
[out:json][timeout:30];
relation(19297407);
out body;
"""

HEADERS = {
    "User-Agent": "DaNangSmartTravel/1.0 (student research project)",
    "Accept": "application/json"
}

try:
    response = requests.get(
        URL,
        params={"data": QUERY},
        headers=HEADERS,
        timeout=60
    )

    print("HTTP Status:", response.status_code)

    if response.status_code != 200:
        print("Noi dung loi tu server:")
        print(response.text[:2000])
    else:
        data = response.json()
        elements = data.get("elements", [])

        print("So relation tim thay:", len(elements))

        if elements:
            relation = elements[0]

            print("\nID:", relation.get("id"))
            print("Tags:", relation.get("tags"))

            members = relation.get("members", [])
            print("Tong so thanh phan:", len(members))

            for member in members:
                print(
                    "Loai:", member.get("type"),
                    "| ID:", member.get("ref"),
                    "| Role:", member.get("role")
                )
        else:
            print("Khong tim thay Relation 19297407.")

except requests.exceptions.RequestException as error:
    print("Loi ket noi:", error)
