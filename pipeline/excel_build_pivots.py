"""
Phase 4b - Open the data-table workbook in Excel (COM) and build the
presentation layer: PivotTables + slicers + a Guide sheet + formatting.

Requires Microsoft Excel installed (uses win32com). Produces
output/ICBC_Vehicle_Inventory.xlsx.
"""
from __future__ import annotations

import os
import shutil
import sys

import pythoncom
import win32com.client as win32

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

DATA_XLSX = os.path.join(config.OUTPUT_DIR, "_data_tables.xlsx")
FINAL_XLSX = os.path.join(config.OUTPUT_DIR, "ICBC_Vehicle_Inventory.xlsx")

# Excel enum values (numeric to avoid makepy dependency)
xlDatabase = 1
xlRowField = 1
xlColumnField = 2
xlPageField = 3
xlDataField = 4
xlSum = -4157
xlCount = -4112
xlHidden = 0
xlUp = -4162
xlToRight = -4161

ACCENT = 0x9E5B15   # BGR for a blue-ish accent (Excel uses BGR)
TITLE_BLUE = 0xA85E17


def used_range_addr(ws):
    last_row = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    last_col = ws.Cells(1, 1).End(xlToRight).Column   # from A1 go right to last header
    return f"R1C1:R{last_row}C{last_col}", last_row, last_col


def add_pivot(wb, src_sheet, dest_sheet_name, table_name,
              row_fields, col_fields, data_fields, calc_fields=None,
              slicer_fields=None, title=""):
    """Create a presentation sheet with a PivotTable and slicers."""
    ws_src = wb.Worksheets(src_sheet)
    addr, nrows, ncols = used_range_addr(ws_src)
    src = f"'{src_sheet}'!{addr}"

    # (re)create destination sheet
    try:
        wb.Worksheets(dest_sheet_name).Delete()
    except Exception:
        pass
    ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
    ws.Name = dest_sheet_name

    # title
    ws.Cells(1, 1).Value = title
    ws.Cells(1, 1).Font.Size = 14
    ws.Cells(1, 1).Font.Bold = True
    ws.Cells(1, 1).Font.Color = TITLE_BLUE
    ws.Cells(2, 1).Value = "Use the slicers (right) to select a community / vehicle type."
    ws.Cells(2, 1).Font.Italic = True

    cache = wb.PivotCaches().Create(SourceType=xlDatabase, SourceData=src, Version=6)
    pt = cache.CreatePivotTable(TableDestination=f"'{dest_sheet_name}'!R5C1",
                                TableName=table_name, DefaultVersion=6)
    # Defer recomputation until all fields are placed - otherwise Excel
    # recomputes the (large) pivot on EVERY field change and blows up RAM/time.
    pt.ManualUpdate = True

    for cf in (calc_fields or []):
        pt.CalculatedFields().Add(cf["name"], cf["formula"])

    for i, f in enumerate(row_fields, 1):
        pf = pt.PivotFields(f)
        pf.Orientation = xlRowField
        pf.Position = i
    for i, f in enumerate(col_fields, 1):
        pf = pt.PivotFields(f)
        pf.Orientation = xlColumnField
        pf.Position = i

    for df in data_fields:
        d = pt.AddDataField(pt.PivotFields(df["field"]), df["caption"], df.get("func", xlSum))
        if df.get("numfmt"):
            d.NumberFormat = df["numfmt"]

    pt.ColumnGrand = True
    pt.RowGrand = True
    pt.ManualUpdate = False        # compute once, now
    try:
        pt.RowAxisLayout(1)        # xlTabularRow for readable multi-field rows
        pt.TableStyle2 = "PivotStyleMedium9"
    except Exception:
        pass

    # slicers (floating shapes, positioned in points to the right of the pivot)
    top = 60
    for f in (slicer_fields or []):
        sc = wb.SlicerCaches.Add2(pt, f)
        sc.Slicers.Add(ws, pythoncom.Missing, f"{table_name}_{f}"[:250], f, top, 430, 160, 150)
        top += 168
    return pt


def build_guide(wb):
    try:
        wb.Worksheets("Guide").Delete()
    except Exception:
        pass
    ws = wb.Worksheets.Add(Before=wb.Worksheets(1))
    ws.Name = "Guide"
    lines = [
        ("ICBC Vehicle Population - Community Inventory (2021-2025)", 16, True, TITLE_BLUE),
        ("", 11, False, 0),
        ("Source: ICBC Vehicle Population open data (public.tableau.com/profile/icbc), "
         "row-level extracts for passenger + commercial vehicles, 2021-2025.", 11, False, 0),
        ("Counts are vehicles with an active policy as of Dec 31 of each year, by the "
         "owner's mailing-address municipality.", 11, False, 0),
        ("", 11, False, 0),
        ("HOW TO USE", 13, True, TITLE_BLUE),
        ("Each analysis sheet has slicers on the right - click a community (and/or vehicle "
         "type) to filter every number on that sheet. Ctrl-click for multiple.", 11, False, 0),
        ("", 11, False, 0),
        ("SHEETS", 13, True, TITLE_BLUE),
        ("- By Model Year: vehicles by model year, one column per data year (2021-2025). "
         "Select a community with the slicer.", 11, False, 0),
        ("- By Segment (Size): vehicles by size class, with average length & weight - shows "
         "the shift toward larger vehicles.", 11, False, 0),
        ("- By Make: vehicles by manufacturer.", 11, False, 0),
        ("- By Model: vehicles by make & model (top 100 per community/year/type; the long "
         "tail is grouped as '(Other)'. Full detail: data/build/view_by_model_FULL.csv).", 11, False, 0),
        ("- Fleet Trend (Hypothesis): per-year totals, average vehicle length, average net "
         "weight and total fleet length for the selected community.", 11, False, 0),
        ("- Class Map: how every Make/Model/Body-style maps to a size Segment + length.", 11, False, 0),
        ("- Segment Lengths: the representative length (m) assigned to each segment.", 11, False, 0),
        ("", 11, False, 0),
        ("METHODOLOGY - vehicle length", 13, True, TITLE_BLUE),
        ("There are ~11,000 model names, so each vehicle is assigned to a size SEGMENT "
         "(e.g. Compact SUV, Full-size pickup) from its make, body style and model name, and "
         "the segment is given a representative length from published class averages.", 11, False, 0),
        ("Representative length reflects the FLEET MIX (sedans vs SUVs vs pickups). It is a "
         "fixed value per segment, so it does not capture year-over-year size growth WITHIN a "
         "segment.", 11, False, 0),
        ("'Net weight' is a MEASURED field in the ICBC data and is included as an independent, "
         "objective size signal: passenger-vehicle net weight rose ~20% from model-year 2000 "
         "to 2025 (approx. 1,470 -> 1,760 kg).", 11, False, 0),
        ("Caveat: older model-year vehicles still on the road skew toward trucks/vans "
         "(survivorship), so read model-year length/weight trends with that in mind.", 11, False, 0),
        ("", 11, False, 0),
        (f"Built {__import__('datetime').date.today().isoformat()} from ICBC data. "
         "Re-run pipeline/run_all.py to refresh.", 10, False, 0),
    ]
    for i, (text, size, bold, color) in enumerate(lines, 1):
        cell = ws.Cells(i, 1)
        cell.Value = text
        cell.Font.Size = size
        cell.Font.Bold = bold
        if color:
            cell.Font.Color = color
    ws.Columns(1).ColumnWidth = 120
    return ws


def main() -> int:
    if not os.path.exists(DATA_XLSX):
        print("data workbook missing - run excel_write_data.py first")
        return 1
    shutil.copyfile(DATA_XLSX, FINAL_XLSX)

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.ScreenUpdating = False
    try:
        wb = excel.Workbooks.Open(os.path.abspath(FINAL_XLSX))

        print("building: By Model Year", flush=True)
        add_pivot(wb, "d_model_year", "By Model Year", "pt_model_year",
                  row_fields=["Model_Year_Band", "Model_Year_Num"],
                  col_fields=["Count_Year"],
                  data_fields=[{"field": "Vehicles", "caption": "Total vehicles", "numfmt": "#,##0"}],
                  slicer_fields=["Municipality", "Vehicle_Type"],
                  title="Vehicles by Model Year (2021-2025)")

        print("building: By Segment (Size)")
        add_pivot(wb, "d_segment", "By Segment (Size)", "pt_segment",
                  row_fields=["Segment"], col_fields=["Count_Year"],
                  data_fields=[
                      {"field": "Vehicles", "caption": "Total vehicles", "numfmt": "#,##0"},
                      {"field": "AvgLen", "caption": "Avg length (m)", "numfmt": "0.00"},
                      {"field": "AvgWt", "caption": "Avg net wt (kg)", "numfmt": "#,##0"},
                  ],
                  calc_fields=[
                      {"name": "AvgLen", "formula": "=LengthSum_m/Vehicles"},
                      {"name": "AvgWt", "formula": "=WeightSum_kg/Vehicles"},
                  ],
                  slicer_fields=["Municipality", "Vehicle_Type"],
                  title="Vehicles by Size Segment (with average length & weight)")

        print("building: By Make", flush=True)
        add_pivot(wb, "d_make", "By Make", "pt_make",
                  row_fields=["Make"], col_fields=["Count_Year"],
                  data_fields=[{"field": "Vehicles", "caption": "Total vehicles", "numfmt": "#,##0"}],
                  slicer_fields=["Municipality", "Vehicle_Type"],
                  title="Vehicles by Make")

        print("building: By Model", flush=True)
        add_pivot(wb, "d_model", "By Model", "pt_model",
                  row_fields=["Make", "Model"], col_fields=["Count_Year"],
                  data_fields=[{"field": "Vehicles", "caption": "Total vehicles", "numfmt": "#,##0"}],
                  slicer_fields=["Municipality", "Vehicle_Type"],
                  title="Vehicles by Make & Model (top 100 per community/year)")

        print("building: Fleet Trend (Hypothesis)")
        add_pivot(wb, "d_summary", "Fleet Trend", "pt_summary",
                  row_fields=["Count_Year"], col_fields=[],
                  data_fields=[
                      {"field": "Vehicles", "caption": "Total vehicles", "numfmt": "#,##0"},
                      {"field": "AvgLen", "caption": "Avg length (m)", "numfmt": "0.000"},
                      {"field": "AvgWt", "caption": "Avg net wt (kg)", "numfmt": "#,##0"},
                      {"field": "FleetKm", "caption": "Fleet length (km)", "numfmt": "#,##0"},
                  ],
                  calc_fields=[
                      {"name": "AvgLen", "formula": "=LengthSum_m/Vehicles"},
                      {"name": "AvgWt", "formula": "=WeightSum_kg/Vehicles"},
                      {"name": "FleetKm", "formula": "=LengthSum_m/1000"},
                  ],
                  slicer_fields=["Municipality", "Vehicle_Type"],
                  title="Fleet Trend by Year - vehicles, average size, total length")

        print("building: Guide", flush=True)
        build_guide(wb)

        # hide raw data sheets
        for s in ("d_model_year", "d_segment", "d_make", "d_model", "d_summary"):
            wb.Worksheets(s).Visible = xlHidden

        wb.Worksheets("Guide").Activate()
        wb.Save()
        wb.Close(SaveChanges=True)
        print(f"\nSaved {FINAL_XLSX} ({os.path.getsize(FINAL_XLSX):,} bytes)")
    finally:
        excel.Quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
