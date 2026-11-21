
import json
from collections import Counter

FILE_PATH = "data/raw/danang_old_boundary.json"

with open(FILE_PATH, "r", encoding="utf-8") as file:
    data = json.load(file)

relation = data["elements"][0]
members = relation.get("members", [])

for target_role in ["outer", "inner"]:

    print(f"\n========== KIEM TRA {target_role.upper()} ==========")

    ways = [
        member for member in members
        if member.get("type") == "way"
        and member.get("role") == target_role
    ]

    endpoints = Counter()
    closed_ways = 0
    invalid_ways = []

    for way in ways:

        geometry = way.get("geometry", [])

        if len(geometry) < 2:
            invalid_ways.append(way.get("ref"))
            continue

        start = (
            round(geometry[0]["lat"], 7),
            round(geometry[0]["lon"], 7)
        )

        end = (
            round(geometry[-1]["lat"], 7),
            round(geometry[-1]["lon"], 7)
        )

        endpoints[start] += 1
        endpoints[end] += 1

        if start == end:
            closed_ways += 1

    print("So Way:", len(ways))
    print("Way tu dong khep kin:", closed_ways)
    print("Way khong du 2 toa do:", len(invalid_ways))

    if invalid_ways:
        print("ID Way loi:", invalid_ways)

    unconnected = [
        point for point, count in endpoints.items()
        if count == 1
    ]

    connected_more_than_two = [
        (point, count)
        for point, count in endpoints.items()
        if count > 2
    ]

    print("So diem dau/cuoi chi xuat hien 1 lan:", len(unconnected))
    print("So diem co hon 2 ket noi:", len(connected_more_than_two))

    print("========================================")
