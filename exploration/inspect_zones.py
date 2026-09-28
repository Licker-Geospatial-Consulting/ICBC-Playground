import json
from tableau_client import load_workbook

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")

with open("info.json", "w", encoding="utf-8") as f:
    json.dump(ts.info, f, indent=2)
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(ts.data, f, indent=2)

# 1) All worksheet names referenced anywhere
info_str = json.dumps(ts.info)
data_str = json.dumps(ts.data)
print("info.json size:", len(info_str), " data.json size:", len(data_str))

# 2) Zones in the presentation layout
try:
    zones = ts.info["worldUpdate"]["applicationPresModel"]["workbookPresModel"][
        "dashboardPresModel"]["zones"]
    print("\nZONES:", len(zones))
    for zid, z in list(zones.items()):
        nm = z.get("worksheet") or z.get("name") or z.get("zoneType")
        print(f"  zone {zid}: type={z.get('zoneType')!r} worksheet={z.get('worksheet')!r} name={z.get('name')!r}")
except Exception as e:
    print("zones err:", e)

# 3) look for storyPoints / sheet navigation / parameter fields
for key in ["storyPoints", "storyboard", "2021-Passenger", "2025-Passenger",
            "MODEL YEAR", "MAKE", "MUNICIPALITY", "goto", "sheetLink", "windowId",
            "VehiclePopulationData", "Vehicle Pop Data"]:
    print(f"  info has {key!r}: {key in info_str} ({info_str.count(key)}) | data: {key in data_str} ({data_str.count(key)})")
