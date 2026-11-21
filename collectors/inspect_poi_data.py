
import json
import os

FILE_PATH = "data/raw/osm_places.json"

if not os.path.exists(FILE_PATH):
    print("Khong tim thay file:", FILE_PATH)
    raise SystemExit

with open(FILE_PATH, "r", encoding="utf-8") as file:
    data = json.load(file)

print("========== CAU TRUC FILE ==========")
print("Kieu du lieu goc:", type(data).__name__)

# Xac dinh danh sach ban ghi
records = None

if isinstance(data, list):
    records = data

elif isinstance(data, dict):
    print("Cac key cap cao:", list(data.keys()))

    # Thu tim danh sach ban ghi trong cac key pho bien
    for key in ["elements", "places", "data", "results"]:
        if isinstance(data.get(key), list):
            records = data[key]
            print("Danh sach ban ghi nam trong key:", key)
            break

if records is None:
    print("\nKhong xac dinh duoc danh sach ban ghi.")
    print("Hay gui minh cau truc file de kiem tra tiep.")
    raise SystemExit

print("Tong so ban ghi:", len(records))

print("\n========== 3 BAN GHI DAU TIEN ==========")

for index, record in enumerate(records[:3], start=1):
    print(f"\n--- BAN GHI {index} ---")
    print(json.dumps(
        record,
        ensure_ascii=False,
        indent=2
    ))

print("\n======================================")
