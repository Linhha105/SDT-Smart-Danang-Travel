
import json
from collections import Counter

FILE_PATH = "data/raw/danang_old_boundary.json"

with open(FILE_PATH, "r", encoding="utf-8") as file:
    data = json.load(file)

elements = data.get("elements", [])

if not elements:
    print("Khong co du lieu Relation.")
    raise SystemExit

relation = next(
    (item for item in elements if item.get("type") == "relation"),
    None
)

if relation is None:
    print("Khong tim thay Relation.")
    raise SystemExit


# ==========================================
# 1. THONG TIN RELATION
# ==========================================

print("========== THONG TIN RELATION ==========")

print("ID:", relation.get("id"))
print("Version:", relation.get("version"))
print("Timestamp:", relation.get("timestamp"))

print("\n========== TOAN BO TAGS ==========")

tags = relation.get("tags", {})

for key, value in tags.items():
    print(f"{key}: {value}")


# ==========================================
# 2. KIEM TRA CAC WAY THANH PHAN
# ==========================================

members = relation.get("members", [])

role_count = Counter()
coordinate_count = Counter()

missing_geometry = []
way_details = []

print("\n========== DANH SACH WAY ==========")

for member in members:

    if member.get("type") != "way":
        continue

    role = member.get("role", "unknown")
    geometry = member.get("geometry", [])

    role_count[role] += 1
    coordinate_count[role] += len(geometry)

    if not geometry:
        missing_geometry.append(member.get("ref"))

    way_details.append({
        "id": member.get("ref"),
        "role": role,
        "coordinates": len(geometry)
    })

    print(
        f"ID: {member.get('ref')} "
        f"| Role: {role} "
        f"| Toa do: {len(geometry)}"
    )


# ==========================================
# 3. TONG HOP
# ==========================================

print("\n========== TONG HOP ==========")

for role, count in role_count.items():
    print(f"{role}: {count} way")

print("Tong Way:", sum(role_count.values()))
print("Way thieu geometry:", len(missing_geometry))

print("\nSo toa do theo role:")

for role, count in coordinate_count.items():
    print(f"{role}: {count} toa do")

if missing_geometry:
    print("\nDanh sach Way thieu geometry:")
    print(missing_geometry)

print("\n========== KIEM TRA ROLE ==========")

unknown_roles = [
    item for item in way_details
    if item["role"] not in ["outer", "inner"]
]

print("Way co role khong phai outer/inner:", len(unknown_roles))

print("================================")
