"""
Build a compact JSON dataset for the shareable HTML dashboard.

Aggregates the views down to (municipality x vehicle_type x year) with a coarse
size-class breakdown and a model-year-band breakdown, small enough to embed
directly in a self-contained HTML artifact. Passenger & Commercial are stored
separately; the page sums them for the "All" option.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import regional_districts as rd_mod  # noqa: E402

YEARS = [2021, 2022, 2023, 2024, 2025]

# fine segment -> coarse group (size-ordered)
COARSE = {
    "Microcar": "Car", "Subcompact car": "Car", "Compact car": "Car",
    "Midsize car": "Car", "Full-size car": "Car", "Luxury/large sedan": "Car",
    "Coupe": "Car", "Convertible": "Car", "Sports car": "Car", "Station wagon": "Car",
    "Subcompact SUV": "Small SUV", "Compact SUV": "Small SUV",
    "Midsize SUV": "Midsize SUV",
    "Full-size SUV": "Large SUV",
    "Minivan": "Minivan/Van", "Cargo/passenger van": "Minivan/Van",
    "Small pickup": "Small pickup",
    "Full-size pickup": "Full-size pickup",
    "Heavy commercial": "Heavy commercial", "Limousine": "Heavy commercial",
    "Motorcycle": "Other", "ATV/off-road": "Other", "Snowmobile": "Other",
    "Low-speed/other": "Other", "Mixed/other": "Other", "Unclassified": "Other",
}
SEG_ORDER = ["Car", "Small SUV", "Midsize SUV", "Large SUV", "Minivan/Van",
             "Small pickup", "Full-size pickup", "Heavy commercial", "Other"]
BANDS = ["Pre-1990", "1990-1999", "2000-2009", "2010-2014", "2015-2019", "2020-2025"]


def band_of(y):
    if pd.isna(y):
        return None
    y = int(y)
    if y < 1990: return "Pre-1990"
    if y < 2000: return "1990-1999"
    if y < 2010: return "2000-2009"
    if y < 2015: return "2010-2014"
    if y < 2020: return "2015-2019"
    return "2020-2025"


def main() -> int:
    seg = pd.read_parquet(config.VIEW_BY_SEGMENT)
    my = pd.read_parquet(config.VIEW_BY_MODELYEAR)
    seg["Coarse"] = seg["Segment"].map(COARSE).fillna("Other")
    my["Band"] = my["Model_year_num"].map(band_of)

    tcode = {"Passenger": "P", "Commercial": "C"}
    yr_idx = {y: i for i, y in enumerate(YEARS)}
    seg_idx = {s: i for i, s in enumerate(SEG_ORDER)}
    band_idx = {b: i for i, b in enumerate(BANDS)}

    munis = sorted(set(seg["Municipality"]))

    def blank(nfields):
        return [[0] * nfields for _ in YEARS]

    data = {}
    # region lookup for display
    region_of = (seg.groupby("Municipality")["Region"].first().to_dict())

    for m in munis:
        data[m] = {}
    # summary + segment from seg view
    for (m, vt, y), g in seg.groupby(["Municipality", "Vehicle_Type", "Count_Year"], observed=True):
        if vt not in tcode or y not in yr_idx:
            continue
        node = data[m].setdefault(tcode[vt], {
            "veh": [0]*5, "len": [0]*5, "wt": [0]*5,
            "seg": blank(len(SEG_ORDER)), "bandveh": blank(len(BANDS)), "bandwt": blank(len(BANDS)),
        })
        yi = yr_idx[y]
        node["veh"][yi] = int(g["n_vehicles"].sum())
        node["len"][yi] = int(g["length_sum"].sum())
        node["wt"][yi] = int(g["net_weight_sum"].sum())
        for coarse, gg in g.groupby("Coarse", observed=True):
            node["seg"][yi][seg_idx[coarse]] = int(gg["n_vehicles"].sum())

    # model-year bands from my view
    vehcol = "n_vehicles"
    wtcol = "net_weight_sum"
    for (m, vt, y), g in my.groupby(["Municipality", "Vehicle_Type", "Count_Year"], observed=True):
        if vt not in tcode or y not in yr_idx or m not in data:
            continue
        node = data[m].get(tcode[vt])
        if node is None:
            continue
        yi = yr_idx[y]
        for band, gg in g.groupby("Band", observed=True):
            if band in band_idx:
                node["bandveh"][yi][band_idx[band]] = int(gg[vehcol].sum())
                node["bandwt"][yi][band_idx[band]] = int(gg[wtcol].sum())

    # province-wide aggregate
    ALL = "British Columbia (all communities)"
    def new_node():
        return {"veh": [0]*5, "len": [0]*5, "wt": [0]*5, "seg": blank(len(SEG_ORDER)),
                "bandveh": blank(len(BANDS)), "bandwt": blank(len(BANDS))}

    def add_into(dst, src):
        for yi in range(5):
            dst["veh"][yi] += src["veh"][yi]; dst["len"][yi] += src["len"][yi]; dst["wt"][yi] += src["wt"][yi]
            for si in range(len(SEG_ORDER)):
                dst["seg"][yi][si] += src["seg"][yi][si]
            for bi in range(len(BANDS)):
                dst["bandveh"][yi][bi] += src["bandveh"][yi][bi]
                dst["bandwt"][yi][bi] += src["bandwt"][yi][bi]

    # province + regional-district rollups (aggregate municipalities up)
    prov = {"P": None, "C": None}
    rd_data: dict = {}          # rd short-name -> {P,C}
    rd_members: dict = {}       # rd short-name -> set(municipalities)
    veh_total = 0
    veh_mapped = 0
    for m in munis:
        rd = rd_mod.resolve(m)
        rd_members.setdefault(rd, set()).add(m)
        for tc in ("P", "C"):
            src = data[m].get(tc)
            if not src:
                continue
            veh_total += src["veh"][4]
            if rd != rd_mod.UNASSIGNED:
                veh_mapped += src["veh"][4]
            if prov[tc] is None:
                prov[tc] = new_node()
            add_into(prov[tc], src)
            rd_data.setdefault(rd, {"P": None, "C": None})
            if rd_data[rd][tc] is None:
                rd_data[rd][tc] = new_node()
            add_into(rd_data[rd][tc], src)
    data[ALL] = {k: v for k, v in prov.items() if v}
    region_of[ALL] = "All BC"

    def total_2025(node):
        return sum(node[tc]["veh"][4] for tc in ("P", "C") if node.get(tc))

    ordered_muni = [ALL] + sorted(list(munis), key=lambda m: total_2025(data[m]), reverse=True)

    # register RD geographies (display name) into the data + meta
    rd_display = {}
    for rd, node in rd_data.items():
        disp = rd_mod.display_name(rd)
        data[disp] = {k: v for k, v in node.items() if v}
        rd_display[rd] = disp
        nmem = len(rd_members.get(rd, ()))
        alias = rd_mod.ABBREV.get(rd, "")
        region_of[disp] = (f"{alias}, {nmem} communities" if alias else f"{nmem} communities")
    ordered_rd = [ALL] + sorted(rd_display.values(), key=lambda d: total_2025(data[d]), reverse=True)

    # build search-alias map (RD abbreviations help searching e.g. MVRD/CRD)
    alias_map = {}
    for rd, disp in rd_display.items():
        a = rd_mod.ABBREV.get(rd, "")
        alias_map[disp] = (a + " " + rd).strip()

    geos = list(dict.fromkeys(ordered_muni + ordered_rd))
    out = {
        "years": YEARS, "segments": SEG_ORDER, "bands": BANDS,
        "community": ordered_muni,
        "district": ordered_rd,
        "region": {g: region_of.get(g, "") for g in geos},
        "alias": {g: alias_map.get(g, "") for g in geos if alias_map.get(g)},
        "d": {g: data[g] for g in geos},
    }
    path = os.path.join(config.OUTPUT_DIR, "dashboard_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=True)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    print(f"  communities: {len(ordered_muni)-1} | regional districts: {len(ordered_rd)-1}")
    print(f"  RD coverage: {100*veh_mapped/max(veh_total,1):.1f}% of 2025 vehicles mapped to a district")
    unassigned = rd_display.get(rd_mod.UNASSIGNED)
    if unassigned:
        print(f"  Unassigned 2025 vehicles: {total_2025(data[unassigned]):,}")
    print("  Regional districts by 2025 vehicles:")
    for disp in ordered_rd[1:]:
        print(f"    {total_2025(data[disp]):>9,}  {disp}  [{region_of[disp]}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
