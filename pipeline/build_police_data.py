"""
Build compact JSON for the Police-reported crashes (TAS) tab, combining four
TAS extracts (2020-2024). They are different grains (crash / entity / victim)
so they can't be row-joined, but all share REGION + YEAR, which we use as the
shared filters. Each dataset is pre-aggregated per (REGION, YEAR).

  HOW  (TAS - No Contributing Factors, crash-level): collision type, crash
       configuration, weather, road condition, light + totals (crashes,
       casualties, vehicles).
  WHY  (TAS - No Month, crash-level): reason flags (alcohol/drug/impaired/
       speed/distracted/inattentive/asleep);
       (TAS - Entity): top contributing factors.
  WHO  (TAS - Entity, entity-level): vehicle type, vehicle use, age, gender,
       entity type; (TAS - Victim, victim-level): injury type, role, age,
       gender, safety equipment.
"""
from __future__ import annotations
import glob, json, os, sys
import pandas as pd
from tableauhyperapi import HyperProcess, Telemetry, Connection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa

CRASH_DIR = os.path.join(config.ROOT, "data", "crash_hyper")
YEARS = [2020, 2021, 2022, 2023, 2024]
REGIONS = ["Lower Mainland", "Vancouver Island", "Southern Interior", "North Central"]


def load(key):
    f = max(glob.glob(os.path.join(CRASH_DIR, f"{key}__*.hyper")), key=os.path.getsize)
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(endpoint=hp.endpoint, database=f) as conn:
            tbl = None
            for schema in conn.catalog.get_schema_names():
                names = conn.catalog.get_table_names(schema=schema)
                if names:
                    tbl = names[0]
                    break
            tdef = conn.catalog.get_table_definition(tbl)
            cols = [c.name.unescaped for c in tdef.columns]
            rows = conn.execute_list_query(f"SELECT * FROM {tbl}")
    return pd.DataFrame(rows, columns=cols)


def cellkey(r, y):
    return f"{r}|{int(y)}"


def dim_cells(df, dimcol, measure, labels, geocol="REGION"):
    """{'geo|year': [counts per label]} where geo is REGION or MUNICIPALITY."""
    idx = {l: i for i, l in enumerate(labels)}
    out = {}
    g = df.groupby([geocol, "YEAR", dimcol])[measure].sum()
    for (geo, yr, cat), val in g.items():
        if cat not in idx or pd.isna(yr):
            continue
        arr = out.setdefault(cellkey(geo, yr), [0]*len(labels))
        arr[idx[cat]] += int(val)
    return out


def labels_for(df, dimcol, measure, top=None, drop=()):
    s = df.groupby(dimcol)[measure].sum().sort_values(ascending=False)
    labs = [x for x in s.index if x not in drop and pd.notna(x)]
    return labs[:top] if top else labs


def tot_cells(df, measures, geocol="REGION"):
    out = {}
    g = df.groupby([geocol, "YEAR"])[measures].sum()
    for (geo, yr), row in g.iterrows():
        if pd.isna(yr):
            continue
        out[cellkey(geo, yr)] = {m: int(row[m]) for m in measures}
    return out


def build_how(df):
    dims = {
        "collision": labels_for(df, "COLLISION_TYPE", "CRASH_COUNT", top=14, drop={"Other"}),
        "config": labels_for(df, "CRASH_CONFIGURATION", "CRASH_COUNT", drop={"Other", "Unknown"}),
        "weather": labels_for(df, "WEATHER", "CRASH_COUNT", drop={"None"}),
        "road": labels_for(df, "ROAD_CONDITION", "CRASH_COUNT"),
        "light": labels_for(df, "LIGHT", "CRASH_COUNT", drop={"None"}),
    }
    data = {d: dim_cells(df, col, "CRASH_COUNT", dims[d], geocol="MUNICIPALITY") for d, col in
            (("collision", "COLLISION_TYPE"), ("config", "CRASH_CONFIGURATION"),
             ("weather", "WEATHER"), ("road", "ROAD_CONDITION"), ("light", "LIGHT"))}
    return {"labels": dims, "data": data, "muni": True,
            "tot": tot_cells(df, ["CRASH_COUNT", "TOTAL_CASUALTY", "TOTAL_VEHICLES_INVOLVED"],
                             geocol="MUNICIPALITY")}


def build_why_reasons(df):
    flags = [("Alcohol", "ALCOHOL_INVOLVED"), ("Drugs", "DRUG_INVOLVED"),
             ("Impaired (alc/drug)", "IMPAIRED_INVOLVED"), ("Speed-related", "SPEED_INVOLVED"),
             ("Distracted", "DISTRACTED_INVOLVED"), ("Driver inattentive", "DRIVER_INATTENTIVE"),
             ("Fell asleep", "FELL_ASLEEP")]
    labels = [n for n, _ in flags]
    cells = {}
    for (muni, yr), sub in df.groupby(["MUNICIPALITY", "YEAR"]):
        if pd.isna(yr):
            continue
        cells[cellkey(muni, yr)] = {
            "vals": [int(sub.loc[sub[col] == "Yes", "CRASH_COUNT"].sum()) for _, col in flags],
            "crashes": int(sub["CRASH_COUNT"].sum()),
        }
    return {"labels": labels, "cells": cells, "muni": True}


def build_why_factors(df):
    drop = {"None", "Not Applicable", "Unknown", "", None, "No Contributing Factor",
            "N/A", "Other (*see police comments)", "Other"}
    # melt the 4 contributing-factor columns, weighted by ENTITY_COUNT
    parts = []
    for i in (1, 2, 3, 4):
        c = f"CONTRIBUTING_FACTOR_{i}"
        if c in df.columns:
            parts.append(df[["REGION", "YEAR", c, "ENTITY_COUNT"]].rename(columns={c: "F"}))
    melt = pd.concat(parts, ignore_index=True)
    melt = melt[~melt["F"].isin(drop) & melt["F"].notna()]
    top = (melt.groupby("F")["ENTITY_COUNT"].sum().sort_values(ascending=False).head(18).index.tolist())
    labels = top
    cells = dim_cells(melt, "F", "ENTITY_COUNT", labels)
    return {"labels": labels, "cells": cells}


def build_who_entity(df):
    dims = {
        "vehType": labels_for(df, "VEHICLE_TYPE", "ENTITY_COUNT", top=14,
                              drop={"Not Applicable", "Other", "Unknown"}),
        "vehUse": labels_for(df, "VEHICLE_USE", "ENTITY_COUNT", top=12,
                             drop={"Not Applicable", "Other"}),
        "age": ["<16", "16-18", "19-21", "22-25", "26-35", "36-45", "46-55",
                "56-65", "66-75", "76-85", "86+", "Unknown"],
        "gender": ["Female", "Male", "Information not available - see caveats"],
        "entityType": ["Vehicle", "Pedestrian", "Cyclist", "Other"],
    }
    data = {
        "vehType": dim_cells(df, "VEHICLE_TYPE", "ENTITY_COUNT", dims["vehType"]),
        "vehUse": dim_cells(df, "VEHICLE_USE", "ENTITY_COUNT", dims["vehUse"]),
        "age": dim_cells(df, "AGE_RANGE", "ENTITY_COUNT", dims["age"]),
        "gender": dim_cells(df, "GENDER", "ENTITY_COUNT", dims["gender"]),
        "entityType": dim_cells(df, "ENTITY_TYPE", "ENTITY_COUNT", dims["entityType"]),
    }
    # friendly gender labels
    dims["gender"] = ["Female", "Male", "Not available"]
    return {"labels": dims, "data": data, "tot": tot_cells(df, ["ENTITY_COUNT"])}


def build_who_victim(df):
    dims = {
        "injury": ["Fatal injury", "Serious injury - Overnight at hospital",
                   "Non-serious injury", "No injury"],
        "role": ["Driver", "Passenger", "Pedestrian", "Cyclist", "Other"],
        "age": ["00-03", "04-07", "08-12", "13-15", "16-18", "19-21", "22-25", "26-35",
                "36-45", "46-55", "56-65", "66-75", "76-85", "86+", "Unknown"],
        "gender": ["Female", "Male", "Information not available - see caveats"],
        "safety": labels_for(df, "SAFETY_EQUIPMENT", "VICTIM_COUNT", top=10,
                             drop={"Not Applicable", "Other", "Unknown"}),
    }
    data = {
        "injury": dim_cells(df, "INJURY_TYPE", "VICTIM_COUNT", dims["injury"]),
        "role": dim_cells(df, "ROLE", "VICTIM_COUNT", dims["role"]),
        "age": dim_cells(df, "AGE_RANGE", "VICTIM_COUNT", dims["age"]),
        "gender": dim_cells(df, "GENDER", "VICTIM_COUNT", dims["gender"]),
        "safety": dim_cells(df, "SAFETY_EQUIPMENT", "VICTIM_COUNT", dims["safety"]),
    }
    dims["gender"] = ["Female", "Male", "Not available"]
    # fatalities per cell for KPI
    fat = df[df["INJURY_TYPE"] == "Fatal injury"]
    dims_tot = tot_cells(df, ["VICTIM_COUNT"])
    fat_tot = tot_cells(fat, ["VICTIM_COUNT"]) if len(fat) else {}
    for k in dims_tot:
        dims_tot[k]["FATAL"] = fat_tot.get(k, {}).get("VICTIM_COUNT", 0)
    return {"labels": dims, "data": data, "tot": dims_tot}


def main():
    print("loading TAS extracts ...")
    no_contrib = load("tas_no_contrib")
    no_month = load("tas_no_month")
    entity = load("tas_entity")
    victim = load("tas_victim")
    for name, d in (("no_contrib", no_contrib), ("no_month", no_month),
                    ("entity", entity), ("victim", victim)):
        for c in d.columns:
            if c.endswith("COUNT") or c.startswith("TOTAL") or c == "YEAR":
                d[c] = pd.to_numeric(d[c], errors="coerce")
        print(f"  {name}: {len(d):,} rows")

    # municipality -> region map + sorted community list (from the crash-level cube)
    muni_region = (no_contrib.dropna(subset=["MUNICIPALITY"])
                   .groupby("MUNICIPALITY")["REGION"].first().to_dict())
    munis = sorted(m for m in muni_region if m and m != "Unknown")

    out = {
        "years": YEARS, "regions": REGIONS,
        "munis": munis, "muniRegion": muni_region,
        "how": build_how(no_contrib),
        "whyReasons": build_why_reasons(no_month),
        "whyFactors": build_why_factors(entity),
        "whoEntity": build_who_entity(entity),
        "whoVictim": build_who_victim(victim),
    }
    path = os.path.join(config.OUTPUT_DIR, "police_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=True)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    # sanity: BC 2024 crashes, casualties, fatalities
    tot = out["how"]["tot"]
    bc_crashes = sum(v["CRASH_COUNT"] for v in tot.values())
    bc_cas = sum(v["TOTAL_CASUALTY"] for v in tot.values())
    bc_fatal = sum(v.get("FATAL", 0) for v in out["whoVictim"]["tot"].values())
    print(f"  BC 2020-2024: crashes={bc_crashes:,} casualties={bc_cas:,} fatalities={bc_fatal:,}")
    print(f"  top contributing factors: {out['whyFactors']['labels'][:6]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
