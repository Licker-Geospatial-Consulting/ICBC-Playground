"""
Phase 2 - Build the master vehicle inventory from the .hyper extracts.

Reads every data/hyper/*.hyper, aggregates it inside the Hyper engine to a
compact grain (dropping per-registration attributes we don't need), unions all
years+types, and writes a single tidy master parquet.

Master grain (one row per unique combination):
    Count_Year, Vehicle_Type, Region, Municipality,
    Make, Model, Model_year, Body_Style, Fuel_Type
Measures:
    n_vehicles     = SUM(Vehicle_Count)
    net_weight_sum = SUM(net_weight * Vehicle_Count)      (for weighted avg kg)
    gvw_sum        = SUM(licenced_gross_vehicle_weight * Vehicle_Count)
"""
from __future__ import annotations

import glob
import os
import sys

import pandas as pd
from tableauhyperapi import HyperProcess, Telemetry, Connection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

GROUPED_SQL = """
SELECT
    "Vehicle_Count_Year"                     AS "Count_Year",
    "Vehicle_Type"                           AS "Vehicle_Type",
    "Region"                                 AS "Region",
    "Municipality"                           AS "Municipality",
    "Make"                                   AS "Make",
    "Model"                                  AS "Model",
    "Model_year"                             AS "Model_year",
    "Body_Style"                             AS "Body_Style",
    "Fuel_Type"                              AS "Fuel_Type",
    SUM("Vehicle_Count")                                   AS "n_vehicles",
    SUM("net_weight" * "Vehicle_Count")                   AS "net_weight_sum",
    SUM("licenced_gross_vehicle_weight" * "Vehicle_Count") AS "gvw_sum"
FROM {tbl}
GROUP BY 1,2,3,4,5,6,7,8,9
"""


def first_table(conn):
    for schema in conn.catalog.get_schema_names():
        names = conn.catalog.get_table_names(schema=schema)
        if names:
            return names[0]
    raise RuntimeError("no tables in hyper file")


def main() -> int:
    files = sorted(glob.glob(os.path.join(config.HYPER_DIR, "*.hyper")))
    if not files:
        print("No .hyper files found - run download_extracts.py first.")
        return 1

    frames = []
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        for f in files:
            key = os.path.splitext(os.path.basename(f))[0]
            with Connection(endpoint=hp.endpoint, database=f) as conn:
                tbl = first_table(conn)
                sql = GROUPED_SQL.format(tbl=tbl)
                result = conn.execute_list_query(sql)
                cols = ["Count_Year", "Vehicle_Type", "Region", "Municipality",
                        "Make", "Model", "Model_year", "Body_Style", "Fuel_Type",
                        "n_vehicles", "net_weight_sum", "gvw_sum"]
                df = pd.DataFrame(result, columns=cols)
            frames.append(df)
            print(f"  {key:20} -> {len(df):>9,} grouped rows, "
                  f"{df['n_vehicles'].sum():>12,} vehicles")

    master = pd.concat(frames, ignore_index=True)
    # tidy dtypes
    master["Count_Year"] = master["Count_Year"].astype("int32")
    for c in ("n_vehicles", "net_weight_sum", "gvw_sum"):
        master[c] = pd.to_numeric(master[c], errors="coerce").fillna(0).astype("int64")
    # Model_year is stored as text; keep a numeric version where possible
    master["Model_year_num"] = pd.to_numeric(master["Model_year"], errors="coerce").astype("Int64")

    master.to_parquet(config.MASTER_PARQUET, index=False)
    print(f"\nMaster inventory: {len(master):,} rows -> {config.MASTER_PARQUET}")
    print(f"  file size: {os.path.getsize(config.MASTER_PARQUET):,} bytes")
    print(f"  total vehicles (all yr/type): {master['n_vehicles'].sum():,}")
    print(f"  distinct municipalities: {master['Municipality'].nunique():,}")
    print(f"  distinct make: {master['Make'].nunique():,}  model: {master['Model'].nunique():,}")

    # Report the size of candidate Excel-feeding views (to size the workbook design)
    print("\nCandidate view sizes (rows):")
    v_my = master.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year",
                           "Model_year"], as_index=False)["n_vehicles"].sum()
    print(f"  by model-year (Muni x Region x Type x Year x ModelYear): {len(v_my):,}")
    v_mk = master.groupby(["Municipality", "Vehicle_Type", "Count_Year",
                           "Make"], as_index=False)["n_vehicles"].sum()
    print(f"  by make (Muni x Type x Year x Make): {len(v_mk):,}")
    v_mo = master.groupby(["Municipality", "Vehicle_Type", "Count_Year",
                           "Make", "Model"], as_index=False)["n_vehicles"].sum()
    print(f"  by model (Muni x Type x Year x Make x Model): {len(v_mo):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
