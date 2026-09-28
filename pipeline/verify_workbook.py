"""Open the finished workbook in Excel COM and sanity-check pivots/slicers,
then export a couple of sheet screenshots (PDF) for review."""
import os, sys
import win32com.client as win32

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

FINAL = os.path.join(config.OUTPUT_DIR, "ICBC_Vehicle_Inventory.xlsx")


def main():
    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(os.path.abspath(FINAL))
        print("Sheets:")
        for ws in wb.Worksheets:
            vis = {-1: "vis", 0: "hidden", 2: "veryhidden"}.get(ws.Visible, ws.Visible)
            npt = ws.PivotTables().Count
            print(f"  - {ws.Name:22} [{vis}]  pivots={npt}")
        print("\nSlicerCaches:", wb.SlicerCaches.Count)
        for sc in wb.SlicerCaches:
            print(f"  - {sc.Name}  items={sc.SlicerItems.Count}")

        # Functional test: filter Fleet Trend to Surrey and read the pivot back
        print("\nFunctional test - filter Fleet Trend to 'Surrey':")
        pt = wb.Worksheets("Fleet Trend").PivotTables(1)
        # find the Municipality slicer cache connected to THIS pivot
        for sc in wb.SlicerCaches:
            if sc.SlicerItems.Count < 100:
                continue
            connected = any(p.Name == pt.Name for p in sc.PivotTables)
            if connected:
                for it in sc.SlicerItems:
                    it.Selected = (it.Name == "Surrey")
                print(f"   selected Surrey on {sc.Name}")
                break
        excel.Calculate()
        pt.PivotCache().Refresh()
        # read the data body
        rng = pt.TableRange1
        print(f"   pivot now {rng.Rows.Count} rows x {rng.Columns.Count} cols")
        for r in range(1, min(rng.Rows.Count, 9) + 1):
            vals = [rng.Cells(r, c).Text for c in range(1, rng.Columns.Count + 1)]
            print("   ", " | ".join(vals))
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()


if __name__ == "__main__":
    main()
