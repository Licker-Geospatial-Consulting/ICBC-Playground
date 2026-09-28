"""
Reconnaissance script for the ICBC Vehicle Population Tableau Public workbook.

Goal: understand the workbook's structure before building the real pipeline:
  - what worksheets exist on the current view
  - what dashboards / story points / tabs exist
  - what filters / parameters (community, year, passenger vs commercial) are exposed
  - what columns the underlying data actually returns

Nothing here is production logic; it just prints what we find.
"""
import json
import sys

from tableauscraper import TableauScraper as TS

# The "app/profile/.../viz/<Workbook>/<Sheet>" URL maps to the /views/ form.
URL = "https://public.tableau.com/views/VehiclePopulationIntroPage/VehiclePopulationData?:showVizHome=no&:embed=true"


def dump_workbook(wb, label):
    print(f"\n{'='*70}\n{label}\n{'='*70}")
    # Story points (tabs are often story points in these ICBC vizzes)
    try:
        sp = wb.getStoryPoints()
        print("STORY POINTS:")
        print(json.dumps(sp, indent=2)[:2000])
    except Exception as e:
        print(f"getStoryPoints -> {e!r}")

    print("\nWORKSHEETS ON THIS VIEW:")
    for ws in wb.worksheets:
        print(f"  - {ws.name!r}  cols={list(ws.data.columns) if ws.data is not None else None}  rows={0 if ws.data is None else len(ws.data)}")

    print("\nPARAMETERS:")
    try:
        for p in wb.getParameters():
            vals = p.get("values", [])
            print(f"  - {p.get('column')!r} = {p.get('parameterName')!r} current={p.get('value')!r} values[:15]={vals[:15]}")
    except Exception as e:
        print(f"getParameters -> {e!r}")

    print("\nFILTERS (per worksheet):")
    for ws in wb.worksheets:
        try:
            fs = ws.getFilters()
            for f in fs:
                vals = f.get("values", [])
                print(f"  [{ws.name}] {f.get('column')!r} ({f.get('globalFieldName','')}) n={len(vals)} vals[:15]={vals[:15]}")
        except Exception as e:
            print(f"  [{ws.name}] getFilters -> {e!r}")


def main():
    ts = TS()
    ts.loads(URL)
    wb = ts.getWorkbook()
    dump_workbook(wb, "INITIAL LOAD")

    # Peek at a sample of data from each worksheet that has rows
    for ws in wb.worksheets:
        if ws.data is not None and len(ws.data):
            print(f"\n--- sample data: {ws.name} ---")
            print(ws.data.head(10).to_string())


if __name__ == "__main__":
    main()
