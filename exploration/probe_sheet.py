import json
from tableau_client import load_workbook
from tableauscraper import api

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")

for sheet in ["2021-Passenger", "2025-Passenger"]:
    print("\n" + "=" * 72)
    print("goToSheet:", sheet)
    try:
        wb2 = wb.goToSheet(sheet)
        for w in wb2.getWorksheets():
            cols = list(w.data.columns) if w.data is not None else None
            rows = 0 if w.data is None else len(w.data)
            print(f"  WS {w.name!r} rows={rows} cols={cols}")
            if w.data is not None and rows:
                print(w.data.head(8).to_string())
        print("  -- filters --")
        for w in wb2.getWorksheets():
            for f in w.getFilters():
                print(f"    [{w.name}] {f['column']!r} field={f.get('globalFieldName')!r} n={len(f['values'])} sample={f['values'][:10]}")
    except Exception as e:
        print("  ERROR", type(e).__name__, str(e)[:300])

# Try underlying data on the last sheet's main worksheet
print("\n" + "=" * 72)
print("UNDERLYING DATA test on 2025-Passenger")
try:
    r = api.getDownloadableUnderlyingData(ts, "2025-Passenger", ts.dashboard, numRows=20)
    print(json.dumps(r, indent=2)[:2500])
except Exception as e:
    print("  ERROR", type(e).__name__, str(e)[:400])
