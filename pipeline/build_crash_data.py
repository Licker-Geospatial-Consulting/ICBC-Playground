"""
Build the compact JSON for the Crash map / when-where dashboard tab, from the
ICBC Reported Crashes extract (1.45M rows, 2021-2025).

Outputs output/crash_data.json with:
  - geography lists (community / regional district / province), reusing the RD map
  - per (geography x road-user slice) aggregates: totals + crash-config + day +
    month + time-of-day distributions, and top streets
  - output/crash_locs.b64: every geocoded crash location (ICBC geocodes to an
    intersection or a mid-block address range) with its name, municipality and
    per-slice crash/victim counts, gzipped + base64 for the bubble map
Road-user slices: All, Pedestrian, Cyclist, Motorcycle, Heavy vehicle
(subsets are NOT mutually exclusive; a crash involving X is counted in that slice).
"""
from __future__ import annotations
import base64, glob, gzip, json, os, re, sys
import numpy as np
import pandas as pd
from tableauhyperapi import HyperProcess, Telemetry, Connection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa
import regional_districts as rd_mod  # noqa

ALLBC = "British Columbia (all communities)"
YEARS = [2021, 2022, 2023, 2024, 2025]
SLICES = ["All crashes", "Pedestrian", "Cyclist", "Motorcycle", "Heavy vehicle"]
FLAGCOL = {1: "PEDESTRIAN_FLAG", 2: "CYCLIST_FLAG", 3: "MOTORCYCLE_FLAG", 4: "HEAVY_VEH_FLAG"}
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
          "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
TIMES = ["00:00-02:59", "03:00-05:59", "06:00-08:59", "09:00-11:59",
         "12:00-14:59", "15:00-17:59", "18:00-20:59", "21:00-23:59"]
CONFIGS = ["REAR END", "SIDE IMPACT", "SINGLE VEHICLE", "SIDE SWIPE - SAME DIRECTION",
           "OVERTAKING", "HEAD ON", "SIDE SWIPE - OPPOSITE DIRECTION", "MULTIPLE IMPACTS",
           "CONFLICTED", "REAR TO REAR", "UNDETERMINED"]
LOC_Q = 1e-5        # location coordinate quantum (~1 m)
TOP_STREETS = 15

COLS = ["MUNICIPALITY_NAME", "LATITUDE", "LONGITUDE", "DERIVED_CRASH_CONFIGURATION",
        "DAY_OF_WEEK", "MONTH_OF_YEAR", "TIME_CATEGORY", "STREET_FULL_NAME",
        "CROSS_STREET_FULL_NAME", "ROAD_LOCATION_DESCRIPTION",
        "PEDESTRIAN_FLAG", "CYCLIST_FLAG", "MOTORCYCLE_FLAG", "HEAVY_VEH_FLAG",
        "TOTAL_CRASHES", "TOTAL_VICTIMS", "DATE_OF_LOSS_YEAR"]


def load_df():
    f = max(glob.glob("data/crash_hyper/icbc_reported_crashes__*public data set*.hyper"),
            key=os.path.getsize)
    sel = ",".join(f'"{c}"' for c in COLS)
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(endpoint=hp.endpoint, database=f) as conn:
            rows = conn.execute_list_query(f'SELECT {sel} FROM "Extract"."Extract"')
    df = pd.DataFrame(rows, columns=COLS)
    for c in ("TOTAL_CRASHES", "TOTAL_VICTIMS", "DATE_OF_LOSS_YEAR"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int64")
    for c in ("LATITUDE", "LONGITUDE"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Muni"] = df["MUNICIPALITY_NAME"].fillna("UNKNOWN").str.title()
    return df


BLOCK_RE = re.compile(r"#\s*0*(\d+)\s+TO\s+0*(\d+)\s*(odd|even)?", re.I)


def location_label(street, cross, desc):
    """Human name for a geocoded point: 'MAIN ST & E 12TH AVE' at intersections,
    'KINGSWAY, 4700-4749 block' mid-block, else whatever ICBC recorded."""
    street = street if isinstance(street, str) and street.strip() else None
    cross = cross if isinstance(cross, str) and cross.strip() else None
    desc = desc if isinstance(desc, str) and desc.strip() else None
    if street and cross:
        return f"{street} & {cross}"
    if desc:
        m = BLOCK_RE.search(desc)
        if m:
            base = desc[:m.start()].strip() or street or ""
            side = f" ({m.group(3).lower()} side)" if m.group(3) else ""
            return f"{base}, {m.group(1)}-{m.group(2)} block{side}"
        return desc if len(desc) <= 70 else desc[:67] + "..."
    return street or "Unnamed location"


def idxmap(values):
    return {v: i for i, v in enumerate(values)}


def main():
    print("loading crash rows ...")
    df = load_df()
    print(f"  {len(df):,} rows")
    C, V = "TOTAL_CRASHES", "TOTAL_VICTIMS"
    cfg_i, day_i, mon_i, time_i = idxmap(CONFIGS), idxmap(DAYS), idxmap(MONTHS), idxmap(TIMES)

    # slice membership masks
    masks = [pd.Series(True, index=df.index)]
    for s in range(1, 5):
        masks.append(df[FLAGCOL[s]].eq("Y"))

    munis = sorted(df["Muni"].unique())
    muni_i = idxmap(munis)
    rd_of = {m: rd_mod.resolve(m) for m in munis}          # short rd name or Unassigned
    rd_disp = {m: rd_mod.display_name(rd_of[m]) for m in munis}

    # ---- per (muni, slice) aggregates ----
    DIMS = (("DERIVED_CRASH_CONFIGURATION", "cfg", "cfgv", cfg_i, len(CONFIGS)),
            ("DAY_OF_WEEK", "day", "dayv", day_i, 7),
            ("MONTH_OF_YEAR", "mon", "monv", mon_i, 12),
            ("TIME_CATEGORY", "time", "timev", time_i, 8))

    def blank():
        d = {"c": 0, "v": 0, "st": {}, "yr": [0]*len(YEARS), "yrv": [0]*len(YEARS)}
        for _, ck, vk, _im, n in DIMS:
            d[ck] = [0]*n
            d[vk] = [0]*n
        return d

    # nested: muni -> [slice0..4] of blank
    agg = {m: [blank() for _ in SLICES] for m in munis}

    def accumulate(target, sub):
        # sub is a dataframe slice; accumulate crash + victim aggregates
        target["c"] += int(sub[C].sum())
        target["v"] += int(sub[V].sum())
        gy = sub.groupby("DATE_OF_LOSS_YEAR")[[C, V]].sum()
        for y, row in gy.iterrows():
            yi = int(y) - YEARS[0]
            if 0 <= yi < len(YEARS):
                target["yr"][yi] += int(row[C]); target["yrv"][yi] += int(row[V])
        for col, ck, vk, im, _n in DIMS:
            g = sub.groupby(col)[[C, V]].sum()
            for k, row in g.iterrows():
                if k in im:
                    target[ck][im[k]] += int(row[C])
                    target[vk][im[k]] += int(row[V])
        gs = sub.groupby("STREET_FULL_NAME").agg(c=(C, "sum"), v=(V, "sum"))
        for st, row in gs.iterrows():
            if st is None:
                continue
            e = target["st"].setdefault(st, [0, 0])
            e[0] += int(row["c"]); e[1] += int(row["v"])

    print("aggregating per municipality x slice ...")
    for s, mask in enumerate(masks):
        dslice = df[mask]
        for m, sub in dslice.groupby("Muni"):
            accumulate(agg[m][s], sub)

    # ---- roll up to RD + province ----
    def merge_into(dst, src):
        dst["c"] += src["c"]; dst["v"] += src["v"]
        for arr in ("cfg", "cfgv", "day", "dayv", "mon", "monv", "time", "timev", "yr", "yrv"):
            for i in range(len(dst[arr])):
                dst[arr][i] += src[arr][i]
        for st, (c, v) in src["st"].items():
            e = dst["st"].setdefault(st, [0, 0]); e[0] += c; e[1] += v

    geo_agg = {}                      # geo name -> [slice dicts]
    for m in munis:
        geo_agg[m] = agg[m]
    rd_nodes = {}
    prov = [blank() for _ in SLICES]
    for m in munis:
        for s in range(5):
            merge_into(prov[s], agg[m][s])
        disp = rd_disp[m]
        nodes = rd_nodes.setdefault(disp, [blank() for _ in SLICES])
        for s in range(5):
            merge_into(nodes[s], agg[m][s])
    geo_agg[ALLBC] = prov
    geo_agg.update(rd_nodes)

    # finalize: convert street dict -> top-N list, build street name table
    street_names = {}
    def street_idx(name):
        if name not in street_names:
            street_names[name] = len(street_names)
        return street_names[name]

    def pack(node_list):
        out = []
        for nd in node_list:
            # keep the union of top streets by crashes AND by victims (so the
            # victim measure isn't limited to crash-ranked streets)
            top_c = sorted(nd["st"].items(), key=lambda kv: -kv[1][0])[:TOP_STREETS]
            top_v = sorted(nd["st"].items(), key=lambda kv: -kv[1][1])[:TOP_STREETS]
            keep = {}
            for s, cv in top_c + top_v:
                keep[s] = cv
            out.append({
                "c": nd["c"], "v": nd["v"],
                "cfg": nd["cfg"], "cfgv": nd["cfgv"], "day": nd["day"], "dayv": nd["dayv"],
                "mon": nd["mon"], "monv": nd["monv"], "time": nd["time"], "timev": nd["timev"],
                "yr": nd["yr"], "yrv": nd["yrv"],
                "st": [[street_idx(s), cv[0], cv[1]] for s, cv in keep.items()],
            })
        return out

    packed = {g: pack(nodes) for g, nodes in geo_agg.items()}

    # ---- map locations (only geocoded rows in BC bounds) ----
    print("building map locations ...")
    valid = df[(df["LATITUDE"].between(47, 61)) & (df["LONGITUDE"].between(-140, -113))].copy()
    valid["_la"] = np.round(valid["LATITUDE"] / LOC_Q).astype(np.int64)
    valid["_lo"] = np.round(valid["LONGITUDE"] / LOC_Q).astype(np.int64)
    valid["_label"] = [location_label(a, b, d) for a, b, d in
                       zip(valid["STREET_FULL_NAME"], valid["CROSS_STREET_FULL_NAME"],
                           valid["ROAD_LOCATION_DESCRIPTION"])]
    key = ["_la", "_lo"]
    # dominant name + municipality per point (by crashes)
    gl = valid.groupby(key + ["_label", "Muni"])[C].sum().reset_index()
    dom = gl.loc[gl.groupby(key)[C].idxmax()].set_index(key)
    cnt = []
    for s_i in range(5):
        sub = valid if s_i == 0 else valid[valid[FLAGCOL[s_i]].eq("Y")]
        g = sub.groupby(key)[[C, V]].sum()
        cnt.append(g.reindex(dom.index, fill_value=0))
    order = np.lexsort((dom.index.get_level_values(1), dom.index.get_level_values(0)))
    la = dom.index.get_level_values(0).to_numpy()[order]
    lo = dom.index.get_level_values(1).to_numpy()[order]
    labels = dom["_label"].to_numpy()[order]
    lab_list = sorted(set(labels)); lab_i = idxmap(lab_list)
    locs = {
        "q": LOC_Q, "n": int(len(order)),
        # lat is sorted -> delta-encode; lon as delta from the previous point too
        "dla": np.diff(la, prepend=0).tolist(), "dlo": np.diff(lo, prepend=0).tolist(),
        "muni": [muni_i.get(m, -1) for m in dom["Muni"].to_numpy()[order]],
        "name": [lab_i[x] for x in labels], "names": lab_list,
        "cnt": [[int(x) for x in cnt[s_i][col].to_numpy()[order]] for s_i in range(5) for col in (C, V)],
    }
    raw = json.dumps(locs, separators=(",", ":")).encode()
    b64 = base64.b64encode(gzip.compress(raw, 9)).decode()
    lp = os.path.join(config.OUTPUT_DIR, "crash_locs.b64")
    open(lp, "w").write(b64)
    mapped = int(valid[C].sum()); total = int(df[C].sum())
    print(f"  locations: {len(order):,}  names: {len(lab_list):,}  raw {len(raw):,} -> b64 {len(b64):,} "
          f"({100*mapped/total:.0f}% of crashes geocoded)")

    # ---- geography ordering ----
    def tot(g):  # 2025-independent: use All-slice total crashes
        return packed[g][0]["c"]
    ordered_comm = [ALLBC] + sorted(munis, key=tot, reverse=True)
    ordered_rd = [ALLBC] + sorted(rd_nodes.keys(), key=tot, reverse=True)

    region_of = {ALLBC: "All BC"}
    for m in munis:
        region_of[m] = rd_disp[m] if rd_of[m] != rd_mod.UNASSIGNED else ""
    for disp in rd_nodes:
        # abbrev + member count
        short = disp.replace(" Regional District", "")
        n = sum(1 for m in munis if rd_disp[m] == disp)
        ab = rd_mod.ABBREV.get(short, "")
        region_of[disp] = (f"{ab}, {n} communities" if ab else f"{n} communities")
    alias = {}
    for disp in rd_nodes:
        short = disp.replace(" Regional District", "")
        a = rd_mod.ABBREV.get(short, "")
        alias[disp] = (a + " " + short).strip()

    st_table = [None]*len(street_names)
    for name, i in street_names.items():
        st_table[i] = name

    # muni index -> which geos need cell filtering: store muni list + muni->RD
    muni_list = munis
    muni_rd = {m: rd_disp[m] for m in munis}

    out = {
        "slices": SLICES, "configs": CONFIGS, "years": YEARS,
        "days": [d.title() for d in DAYS], "months": [m.title() for m in MONTHS],
        "times": TIMES,
        "community": ordered_comm, "district": ordered_rd,
        "region": region_of, "alias": alias,
        "streetNames": st_table,
        "muniList": muni_list, "muniRD": muni_rd,
        "agg": packed,
        "map": {"pct_geocoded": round(100*mapped/total, 1)},
    }
    path = os.path.join(config.OUTPUT_DIR, "crash_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=True)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    print(f"  communities={len(ordered_comm)-1} districts={len(ordered_rd)-1} "
          f"streets={len(st_table)}")
    prov0 = packed[ALLBC][0]
    peak = TIMES[int(np.argmax(prov0["time"]))]
    print(f"  BC total crashes={prov0['c']:,} victims={prov0['v']:,} peak-time={peak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
