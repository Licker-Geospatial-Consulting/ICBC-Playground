import pandas as pd
from tableau_client import load_workbook

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 200)

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")
wb4 = wb.goToStoryPoint(storyPointId=4)

for sheet in ["2025-Passenger", "Vehicle Pop Data", "2025-Commercial"]:
    print("\n" + "=" * 72)
    print("CROSSTAB:", sheet)
    try:
        df = wb4.getCrossTabData(sheet)
        if df is None:
            print("  -> None")
            continue
        print("  shape:", df.shape)
        print("  columns:", list(df.columns))
        print(df.head(15).to_string())
    except Exception as e:
        print("  ERROR", type(e).__name__, str(e)[:400])
