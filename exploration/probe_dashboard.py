import json
from tableau_client import load_workbook

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")

# Navigate straight to the main data dashboard
wb2 = wb.goToSheet("Vehicle Population Data")
print("dashboard now:", ts.dashboard)

print("\n=== worksheets with >1 row (real breakdowns) ===")
for w in wb2.getWorksheets():
    rows = 0 if w.data is None else len(w.data)
    cols = list(w.data.columns) if w.data is not None else None
    marker = "  <<<" if rows > 1 else ""
    print(f"  WS {w.name!r} rows={rows} cols={cols}{marker}")
    if rows > 1:
        print(w.data.head(12).to_string())

print("\n=== PARAMETERS ===")
for p in wb2.getParameters():
    print("  ", {k: p.get(k) for k in ("column", "parameterName", "values", "value")})

print("\n=== FILTERS ===")
for w in wb2.getWorksheets():
    for f in w.getFilters():
        print(f"  [{w.name}] col={f['column']!r} field={f.get('globalFieldName')!r} "
              f"n={len(f['values'])} sample={f['values'][:12]}")
