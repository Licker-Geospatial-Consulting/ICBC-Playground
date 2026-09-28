import json
from tableau_client import load_workbook
from tableauscraper import api

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")
wb4 = wb.goToStoryPoint(storyPointId=4)   # move session onto the data story point

print("=== export-crosstab-server-dialog ===")
try:
    r = api.exportCrosstabServerDialog(ts)
    with open("crosstab_dialog.json", "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2)
    items = (r["vqlCmdResponse"]["layoutStatus"]["applicationPresModel"]
             ["presentationLayerNotification"][0]["presModelHolder"]
             ["genExportCrosstabOptionsDialogPresModel"]["thumbnailSheetPickerItems"])
    print(f"exportable sheets: {len(items)}")
    for it in items:
        print(f"  sheetName={it.get('sheetName')!r} sheetdocId={it.get('sheetdocId')!r}")
except Exception as e:
    print("dialog ERROR:", type(e).__name__, str(e)[:500])
