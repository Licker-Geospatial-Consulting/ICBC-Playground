"""
Phase 3b - Apply the segment/length classifier to the master inventory and
build the aggregated views that feed the Excel workbook.

Outputs (in data/build/):
  vehicle_class_map.csv        distinct Make/Model/Body_Style/Type -> Segment, Length
  view_by_model_year.parquet   community x year x model-year counts
  view_by_segment.parquet      community x year x segment counts + length/weight
  view_by_make.parquet         community x year x make (+segment) counts
  view_by_model.parquet        community x year x make x model counts (full detail)
  view_community_summary.parquet  community x year fleet totals (the hypothesis view)
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config          # noqa: E402
from classifier import classify, SEGMENT_LENGTH_M  # noqa: E402


def build_class_map(master: pd.DataFrame) -> pd.DataFrame:
    keys = (master[["Make", "Model", "Body_Style", "Vehicle_Type"]]
            .drop_duplicates().reset_index(drop=True))
    print(f"  classifying {len(keys):,} distinct Make/Model/Body/Type combos ...")
    keys["Segment"] = [
        classify(mk, mo, bs, vt)
        for mk, mo, bs, vt in zip(keys["Make"], keys["Model"],
                                  keys["Body_Style"], keys["Vehicle_Type"])
    ]
    keys["Length_m"] = keys["Segment"].map(SEGMENT_LENGTH_M).astype(float)
    return keys


def main() -> int:
    if not os.path.exists(config.MASTER_PARQUET):
        print("master parquet missing - run build_inventory.py first")
        return 1
    print("loading master inventory ...")
    master = pd.read_parquet(config.MASTER_PARQUET)
    print(f"  {len(master):,} rows")

    # --- classifier ---
    class_map = build_class_map(master)
    class_map.to_csv(config.CLASSIFIER_CSV, index=False)
    print(f"  wrote {config.CLASSIFIER_CSV} ({len(class_map):,} rows)")

    master = master.merge(class_map, on=["Make", "Model", "Body_Style", "Vehicle_Type"],
                          how="left")
    master["Length_m"] = master["Length_m"].fillna(SEGMENT_LENGTH_M["Unclassified"])
    master["length_sum"] = master["Length_m"] * master["n_vehicles"]

    # --- coverage report (by volume) ---
    total_v = master["n_vehicles"].sum()
    seg_vol = (master.groupby("Segment")["n_vehicles"].sum()
               .sort_values(ascending=False))
    print("\nSegment share of fleet (all years/types):")
    for seg, v in seg_vol.items():
        print(f"  {seg:22} {v:>12,}  {100*v/total_v:5.1f}%")
    unclad = seg_vol.get("Unclassified", 0)
    print(f"  --> Unclassified: {100*unclad/total_v:.2f}% of vehicles")

    # --- view: by model year (carry length so avg length BY model year works) ---
    v_my = (master.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year",
                            "Model_year", "Model_year_num"], as_index=False, observed=True)
            .agg(n_vehicles=("n_vehicles", "sum"),
                 length_sum=("length_sum", "sum"),
                 net_weight_sum=("net_weight_sum", "sum")))
    v_my.to_parquet(config.VIEW_BY_MODELYEAR, index=False)
    print(f"\nview_by_model_year: {len(v_my):,} rows")

    # --- view: by segment (with length + weight) ---
    v_seg = (master.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year",
                             "Segment", "Length_m"], as_index=False, observed=True)
             .agg(n_vehicles=("n_vehicles", "sum"),
                  length_sum=("length_sum", "sum"),
                  net_weight_sum=("net_weight_sum", "sum")))
    v_seg.to_parquet(config.VIEW_BY_SEGMENT, index=False)
    print(f"view_by_segment: {len(v_seg):,} rows")

    # --- view: by make ---
    v_mk = (master.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year",
                            "Make"], as_index=False, observed=True)
            .agg(n_vehicles=("n_vehicles", "sum"),
                 length_sum=("length_sum", "sum")))
    v_mk.to_parquet(config.VIEW_BY_MAKE, index=False)
    print(f"view_by_make: {len(v_mk):,} rows")

    # --- view: by model (full detail) ---
    v_mo = (master.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year",
                            "Make", "Model", "Segment", "Length_m"],
                           as_index=False, observed=True)
            .agg(n_vehicles=("n_vehicles", "sum"),
                 net_weight_sum=("net_weight_sum", "sum")))
    v_mo.to_parquet(config.VIEW_BY_MODEL, index=False)
    print(f"view_by_model (full): {len(v_mo):,} rows")

    # Full detail also as CSV for power users (exceeds one Excel sheet).
    full_csv = os.path.join(config.BUILD_DIR, "view_by_model_FULL.csv")
    v_mo.to_csv(full_csv, index=False)

    # Capped version for the in-workbook pivot: top-N models per
    # (Municipality, Count_Year, Vehicle_Type); remainder rolled into "(Other)".
    TOP_N = 100
    v_mo = v_mo.sort_values("n_vehicles", ascending=False)
    v_mo["rank"] = (v_mo.groupby(["Municipality", "Count_Year", "Vehicle_Type"],
                                 observed=True).cumcount())
    top = v_mo[v_mo["rank"] < TOP_N].drop(columns="rank")
    tail = v_mo[v_mo["rank"] >= TOP_N]
    if len(tail):
        other = (tail.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year"],
                              as_index=False, observed=True)
                 .agg(n_vehicles=("n_vehicles", "sum"),
                      net_weight_sum=("net_weight_sum", "sum"),
                      n_models=("Model", "nunique")))
        other["Make"] = "(Other makes)"
        other["Model"] = "(" + other["n_models"].astype(str) + " other models)"
        other["Segment"] = "Mixed/other"
        other["Length_m"] = np.nan
        other = other.drop(columns="n_models")
        v_mo_top = pd.concat([top, other[top.columns]], ignore_index=True)
    else:
        v_mo_top = top
    v_mo_top.to_parquet(config.VIEW_BY_MODEL_TOP, index=False)
    print(f"view_by_model (capped top{TOP_N}+Other): {len(v_mo_top):,} rows  "
          f"[full CSV: {full_csv}]")

    # --- view: community summary (THE hypothesis view) ---
    g = master.groupby(["Municipality", "Region", "Vehicle_Type", "Count_Year"],
                       as_index=False, observed=True).agg(
        total_vehicles=("n_vehicles", "sum"),
        length_sum=("length_sum", "sum"),
        net_weight_sum=("net_weight_sum", "sum"),
    )
    g["avg_length_m"] = g["length_sum"] / g["total_vehicles"]
    g["total_fleet_length_km"] = g["length_sum"] / 1000.0
    g["avg_net_weight_kg"] = np.where(g["total_vehicles"] > 0,
                                      g["net_weight_sum"] / g["total_vehicles"], np.nan)
    g.to_parquet(config.VIEW_COMMUNITY_SUMMARY, index=False)
    print(f"view_community_summary: {len(g):,} rows")

    # quick hypothesis sanity check for a few big communities
    print("\nProvince-wide fleet averages by year (Passenger + Commercial):")
    prov = master.groupby("Count_Year").agg(
        total_vehicles=("n_vehicles", "sum"),
        length_sum=("length_sum", "sum")).reset_index()
    prov["avg_length_m"] = prov["length_sum"] / prov["total_vehicles"]
    prov["fleet_length_km"] = prov["length_sum"] / 1000.0
    for _, r in prov.iterrows():
        print(f"  {int(r['Count_Year'])}: vehicles={int(r['total_vehicles']):>10,}  "
              f"avg_len={r['avg_length_m']:.3f} m  fleet_len={r['fleet_length_km']:,.0f} km")

    return 0


if __name__ == "__main__":
    sys.exit(main())
