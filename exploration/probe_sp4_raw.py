import json
from tableau_client import load_workbook
from tableauscraper import api

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")

# Raw response of navigating to story point 4 ("Vehicle population dataset")
r = api.setActiveStoryPoint(ts, storyBoard="Vehicle Population Data", storyPointId=4)
with open("sp4.json", "w", encoding="utf-8") as f:
    json.dump(r, f, indent=2)
s = json.dumps(r)
print("sp4.json size:", len(s))
for key in ["Municipality", "MUNICIPALITY", "MODEL YEAR", "MAKE", "MODEL",
            "2025-Passenger", "2021-Passenger", "categoricalFilter", "quantitativeFilter",
            "globalFieldName", "VEHICLE COUNT", "Vehicle Count", "worksheet", "vehicle count",
            "presModelHolder"]:
    print(f"  {key!r}: count={s.count(key)}")

# Walk to find filter zones and their fields + domains
def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path, k, v
            yield from walk(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")

print("\n=== fields named like filters (globalFieldName) ===")
seen = set()
for path, k, v in walk(r):
    if k == "globalFieldName" and isinstance(v, str) and v not in seen:
        seen.add(v)
        print("  ", v)

print("\n=== worksheet names appearing in cmd response ===")
seen = set()
for path, k, v in walk(r):
    if k in ("worksheet", "name") and isinstance(v, str) and ("Passenger" in v or "Commercial" in v or "Veh Pop" in v or "Municipality" in v):
        if v not in seen:
            seen.add(v)
            print("  ", repr(v))
