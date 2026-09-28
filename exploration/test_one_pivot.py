"""Minimal COM test: build ONE small pivot (+ one slicer) on d_summary to
validate mechanics and watch memory. Writes to a throwaway file."""
import os, sys, shutil, time
import pythoncom
import win32com.client as win32

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

DATA = os.path.join(config.OUTPUT_DIR, "_data_tables.xlsx")
TEST = os.path.join(config.OUTPUT_DIR, "_test_one.xlsx")

xlDatabase, xlRowField, xlDataField, xlSum = 1, 1, 4, -4157

shutil.copyfile(DATA, TEST)
excel = win32.DispatchEx("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False
try:
    t0 = time.time()
    wb = excel.Workbooks.Open(os.path.abspath(TEST))
    print("opened in %.1fs" % (time.time()-t0), flush=True)

    ws_src = wb.Worksheets("d_summary")
    last_row = ws_src.Cells(ws_src.Rows.Count, 1).End(-4162).Row
    last_col = ws_src.Cells(1, 1).End(-4161).Column   # from A1 go right
    print("d_summary range R1C1:R%dC%d" % (last_row, last_col), flush=True)
    src = f"'d_summary'!R1C1:R{last_row}C{last_col}"

    ws = wb.Worksheets.Add()
    ws.Name = "TestPivot"
    t0 = time.time()
    cache = wb.PivotCaches().Create(SourceType=xlDatabase, SourceData=src, Version=6)
    pt = cache.CreatePivotTable(TableDestination="'TestPivot'!R3C1", TableName="pt_test", DefaultVersion=6)
    print("pivot created in %.1fs" % (time.time()-t0), flush=True)
    pt.ManualUpdate = True
    pf = pt.PivotFields("Count_Year"); pf.Orientation = xlRowField; pf.Position = 1
    pt.AddDataField(pt.PivotFields("Vehicles"), "Total Vehicles", xlSum)
    pt.ManualUpdate = False
    print("fields set in %.1fs" % (time.time()-t0), flush=True)

    t0 = time.time()
    sc = wb.SlicerCaches.Add2(pt, "Municipality")
    print("slicercache items=%d in %.1fs" % (sc.SlicerItems.Count, time.time()-t0), flush=True)
    sl = sc.Slicers.Add(ws, pythoncom.Missing, "sl_muni", "Municipality", 40, 400, 160, 200)
    print("slicer added in %.1fs" % (time.time()-t0), flush=True)

    wb.Save()
    print("saved, size=%d" % os.path.getsize(TEST), flush=True)
    wb.Close(SaveChanges=True)
finally:
    excel.Quit()
print("DONE", flush=True)
