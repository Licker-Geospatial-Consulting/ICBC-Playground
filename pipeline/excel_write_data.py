"""
Phase 4a - Write the aggregated views into an .xlsx as plain data tables
(fast bulk write via pandas/openpyxl). Phase 4b then opens this file in Excel
and layers on PivotTables + slicers + formatting via COM.

Data sheets are prefixed "d_" and get hidden by the COM step.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from classifier import SEGMENT_LENGTH_M  # noqa: E402

OUT_XLSX = os.path.join(config.OUTPUT_DIR, "_data_tables.xlsx")

# Order categories so a size-ordered segment axis reads sensibly in pivots.
SEGMENT_ORDER = [
    "Microcar", "Subcompact car", "Compact car", "Midsize car", "Full-size car",
    "Luxury/large sedan", "Coupe", "Convertible", "Sports car", "Station wagon",
    "Subcompact SUV", "Compact SUV", "Midsize SUV", "Full-size SUV",
    "Minivan", "Cargo/passenger van", "Small pickup", "Full-size pickup",
    "Heavy commercial", "Limousine", "Motorcycle", "ATV/off-road", "Snowmobile",
    "Low-speed/other", "Mixed/other", "Unclassified",
]


def model_year_band(y):
    if pd.isna(y):
        return "Unknown"
    y = int(y)
    if y < 1990:
        return "Pre-1990"
    if y < 2000:
        return "1990-1999"
    if y < 2010:
        return "2000-2009"
    if y < 2015:
        return "2010-2014"
    if y < 2020:
        return "2015-2019"
    return "2020-2025"


def main() -> int:
    print("loading views ...")
    v_my = pd.read_parquet(config.VIEW_BY_MODELYEAR)
    v_seg = pd.read_parquet(config.VIEW_BY_SEGMENT)
    v_mk = pd.read_parquet(config.VIEW_BY_MAKE)
    v_mo = pd.read_parquet(config.VIEW_BY_MODEL_TOP)
    v_sum = pd.read_parquet(config.VIEW_COMMUNITY_SUMMARY)
    cmap = pd.read_csv(config.CLASSIFIER_CSV)

    # --- enrich ---
    v_my["Model_Year_Band"] = v_my["Model_year_num"].map(model_year_band)
    v_my = v_my.rename(columns={"Model_year": "Model_Year", "Model_year_num": "Model_Year_Num",
                                "n_vehicles": "Vehicles", "length_sum": "LengthSum_m",
                                "net_weight_sum": "WeightSum_kg"})

    v_seg = v_seg.rename(columns={"n_vehicles": "Vehicles", "length_sum": "LengthSum_m",
                                  "net_weight_sum": "WeightSum_kg", "Length_m": "SegLength_m"})
    v_seg["Segment"] = pd.Categorical(v_seg["Segment"], categories=SEGMENT_ORDER, ordered=True)
    v_seg = v_seg.sort_values(["Municipality", "Count_Year", "Vehicle_Type", "Segment"])
    v_seg["Segment"] = v_seg["Segment"].astype(str)  # xlsxwriter needs plain strings

    v_mk = v_mk.rename(columns={"n_vehicles": "Vehicles", "length_sum": "LengthSum_m"})
    v_mo = v_mo.rename(columns={"n_vehicles": "Vehicles", "net_weight_sum": "WeightSum_kg",
                                "Length_m": "SegLength_m"})

    v_sum = v_sum.rename(columns={"total_vehicles": "Vehicles",
                                  "length_sum": "LengthSum_m",
                                  "net_weight_sum": "WeightSum_kg",
                                  "avg_length_m": "AvgLength_m",
                                  "total_fleet_length_km": "FleetLength_km",
                                  "avg_net_weight_kg": "AvgWeight_kg"})

    seg_len = (pd.DataFrame({"Segment": list(SEGMENT_LENGTH_M),
                             "Representative_Length_m": list(SEGMENT_LENGTH_M.values())}))

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    print(f"writing data sheets -> {OUT_XLSX}")
    with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter") as xw:
        v_my[["Municipality", "Region", "Vehicle_Type", "Count_Year", "Model_Year",
              "Model_Year_Num", "Model_Year_Band", "Vehicles", "LengthSum_m",
              "WeightSum_kg"]].to_excel(xw, sheet_name="d_model_year", index=False)
        v_seg[["Municipality", "Region", "Vehicle_Type", "Count_Year", "Segment",
               "SegLength_m", "Vehicles", "LengthSum_m", "WeightSum_kg"]].to_excel(
            xw, sheet_name="d_segment", index=False)
        v_mk[["Municipality", "Region", "Vehicle_Type", "Count_Year", "Make",
              "Vehicles", "LengthSum_m"]].to_excel(xw, sheet_name="d_make", index=False)
        v_mo[["Municipality", "Region", "Vehicle_Type", "Count_Year", "Make", "Model",
              "Segment", "SegLength_m", "Vehicles", "WeightSum_kg"]].to_excel(
            xw, sheet_name="d_model", index=False)
        v_sum[["Municipality", "Region", "Vehicle_Type", "Count_Year", "Vehicles",
               "AvgLength_m", "FleetLength_km", "AvgWeight_kg", "LengthSum_m",
               "WeightSum_kg"]].to_excel(xw, sheet_name="d_summary", index=False)
        cmap.to_excel(xw, sheet_name="Class Map", index=False)
        seg_len.to_excel(xw, sheet_name="Segment Lengths", index=False)

    print("  rows: model_year=%d segment=%d make=%d model=%d summary=%d class_map=%d"
          % (len(v_my), len(v_seg), len(v_mk), len(v_mo), len(v_sum), len(cmap)))
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
