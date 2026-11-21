
import json
from collections import Counter
from pathlib import Path

# 1. Doc du lieu tho
input_path = Path("data/raw/osm_places.json")

with open(input_path, "r", encoding="utf-8") as file:
    data = json.load(file)

print("========== TONG QUAN DU LIEU ==========")
print("Tong so ban ghi:", len(data))


# 2. Kiem tra du lieu thieu
missing_name = sum(1 for p in data if not p.get("name"))
missing_latitude = sum(1 for p in data if p.get("latitude") is None)
missing_longitude = sum(1 for p in data if p.get("longitude") is None)
missing_address = sum(1 for p in data if not p.get("address"))
missing_hours = sum(1 for p in data if not p.get("opening_hours"))

print("\n========== KIEM TRA DU LIEU THIEU ==========")
print("Thieu ten:", missing_name)
print("Thieu latitude:", missing_latitude)
print("Thieu longitude:", missing_longitude)
print("Thieu dia chi:", missing_address)
print("Thieu gio hoat dong:", missing_hours)


# 3. Thong ke cac nhom du lieu OSM
tag_fields = ["tourism", "amenity", "natural", "shop"]

print("\n========== THONG KE THEO LOAI OSM ==========")

for field in tag_fields:

    counter = Counter(
        p[field]
        for p in data
        if p.get(field)
    )

    print(f"\n{field.upper()}:")

    for category, count in counter.most_common():
        print(f"  {category}: {count}")


# 4. Kiem tra ban ghi trung lap
unique_ids = set()
duplicates = []

for place in data:

    key = (place.get("osm_type"), place.get("osm_id"))

    if key in unique_ids:
        duplicates.append(key)
    else:
        unique_ids.add(key)

print("\n========== KIEM TRA TRUNG LAP ==========")
print("So ban ghi trung lap:", len(duplicates))


# 5. Hien thi 10 dia diem dau tien
print("\n========== 10 DIA DIEM MAU ==========")

for index, place in enumerate(data[:10], start=1):

    print(f"\n{index}. {place.get('name')}")
    print("   Toa do:", place.get("latitude"), place.get("longitude"))
    print("   Tourism:", place.get("tourism"))
    print("   Amenity:", place.get("amenity"))
    print("   Natural:", place.get("natural"))
    print("   Shop:", place.get("shop"))

print("\n========== HOAN THANH KIEM TRA ==========")
