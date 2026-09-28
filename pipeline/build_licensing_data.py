"""
Build compact JSON for the Driver Licensing tab from ICBC's active-driver-licence
snapshots (2022-2025, ~4M licences each) + the road/knowledge exam table.

Licence panels (residence geography: community or region):
  licence class, age, gender, licence issue-year band, licence type,
  out-of-province jurisdiction (origin of transferred-in licences).
Exam panel (test-centre region): road/knowledge/motorcycle pass rate by class.

The 2021 snapshot uses a different, partial schema (~1.1M rows) so it is excluded
for consistency; years shown are 2022-2025.
"""
from __future__ import annotations
import glob, json, os, re, sys
from collections import defaultdict
from tableauhyperapi import HyperProcess, Telemetry, Connection

# Grouped licence-class classification (by the driver's primary entitlement)
CLASS_GROUPS = ["Passenger (Class 5)", "Novice / Learner", "Commercial (Class 1-4)",
                "Motorcycle (Class 6/8)", "Other"]


def group_of(cls):
    c = str(cls).upper()
    if "LEARNER" in c or c == "CLASS 7" or c == "CLASS 7, 8":
        return "Novice / Learner"
    nums = set(re.findall(r"\d+", c))
    if nums & {"1", "2", "3", "4"}:
        return "Commercial (Class 1-4)"
    if "5" in nums:
        return "Passenger (Class 5)"
    if nums & {"6", "8"}:
        return "Motorcycle (Class 6/8)"
    return "Other"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa

CRASH_DIR = os.path.join(config.ROOT, "data", "crash_hyper")
YEARS = [2022, 2023, 2024, 2025]

CLASSES = ["CLASS 7", "CLASS 5", "CLASS 5 Learner", "GLP Learner", "CLASS 5, 6", "CLASS 6",
           "CLASS 1", "CLASS 3", "CLASS 4", "CLASS 2", "CLASS 1, 6", "CLASS 3, 4",
           "CLASS 3, 6", "CLASS 4, 6", "CLASS 2, 3", "CLASS 2, 6", "CLASS 7, 8", "CLASS 8",
           "CLASS 2, 3 and 6", "CLASS 3, 4 and 6", "Other Learner"]
AGES = ["16-18", "19-21", "22-25", "26-35", "36-45", "46-55", "56-65", "66-75", "76-85", "86+"]
GENDERS_RAW = ["Female", "Male", "Information not available"]
TYPES = ["5 Year Renewal", "5 Year Original", "2 Year Renewal", "2 Year Original", "Learner"]
ISSUE_BANDS = ["Pre-2000", "2000-2009", "2010-2014", "2015-2019", "2020-2025"]
# values that are NOT a genuine out-of-province origin (BC-native / unknown / catch-alls)
NOT_OOP = {"British Columbia", "BC", "Unknown", "Non Reciprocity", None, ""}


def first_tbl(conn):
    for s in conn.catalog.get_schema_names():
        n = conn.catalog.get_table_names(schema=s)
        if n:
            return n[0]


def main():
    dl_files = sorted(glob.glob(os.path.join(CRASH_DIR, "driver_licensing__20*_BCDLnew.hyper")))
    print("DL snapshot files:", [os.path.basename(f) for f in dl_files])

    # accumulators: dim -> {(muni,year): {category: count}}
    acc = {d: defaultdict(lambda: defaultdict(int)) for d in
           ("class", "age", "gender", "type", "juris")}
    tot = defaultdict(lambda: {"n": 0, "oop": 0})
    muni_region = {}

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        for f in dl_files:
            with Connection(endpoint=hp.endpoint, database=f) as conn:
                t = first_tbl(conn)
                for m, r in conn.execute_list_query(
                        f'SELECT DISTINCT COALESCE("MUNICIPALITY",\'Unknown\'), "REGION" FROM {t}'):
                    if m and r:
                        muni_region[m] = r
                geo = 'COALESCE("MUNICIPALITY",\'Unknown\')'

                def grp(col, dim):
                    q = f'SELECT "EXTRACT_YEAR", {geo}, {col}, COUNT(*) FROM {t} GROUP BY 1,2,3'
                    for yr, muni, cat, n in conn.execute_list_query(q):
                        if cat is None:
                            continue
                        acc[dim][(muni, int(yr))][cat] += int(n)

                grp('"LICENCE_CLASS"', "class")
                grp('"AGE_RANGE"', "age")
                grp('"GENDER"', "gender")
                grp('"LICENCE_TYPE"', "type")
                grp('"OUT_OF_PROVINCE_JURISDICTION"', "juris")
                # totals + out-of-province count
                q = (f'SELECT "EXTRACT_YEAR", {geo}, COUNT(*), '
                     f'SUM(CASE WHEN "OUT_OF_PROVINCE_JURISDICTION" IS NOT NULL AND '
                     f'"OUT_OF_PROVINCE_JURISDICTION" NOT IN '
                     f"('British Columbia','BC','Unknown','Non Reciprocity') THEN 1 ELSE 0 END) "
                     f'FROM {t} GROUP BY 1,2')
                for yr, muni, n, oop in conn.execute_list_query(q):
                    tot[(muni, int(yr))]["n"] += int(n)
                    tot[(muni, int(yr))]["oop"] += int(oop or 0)
            print(f"  processed {os.path.basename(f)}")

        # exams
        exam = {}
        ef = glob.glob(os.path.join(CRASH_DIR, "driver_licensing__*Exam.hyper"))
        exam_classes = []
        if ef:
            with Connection(endpoint=hp.endpoint, database=ef[0]) as conn:
                t = first_tbl(conn)
                q = (f'SELECT "Office_Region", "Exam_Year", "Exam_Class", '
                     f'SUM(CASE WHEN "EXAM_RESULT"=\'Passed\' THEN "exam_count" ELSE 0 END), '
                     f'SUM("exam_count") FROM {t} GROUP BY 1,2,3')
                for reg, yr, cls, p, n in conn.execute_list_query(q):
                    if yr is None or int(yr) not in YEARS or reg is None or cls is None:
                        continue
                    key = f"{reg}|{int(yr)}"
                    exam.setdefault(key, {})[cls] = [int(p or 0), int(n or 0)]
                    if cls not in exam_classes:
                        exam_classes.append(cls)
        exam_classes.sort()

    # ---- labels ----
    # juris: global top-15 excluding BC
    jur_glob = defaultdict(int)
    for cell, d in acc["juris"].items():
        for cat, n in d.items():
            if cat not in NOT_OOP:
                jur_glob[cat] += n
    juris_labels = [k for k, _ in sorted(jur_glob.items(), key=lambda x: -x[1])[:15]]

    labels = {"classGroup": CLASS_GROUPS, "age": AGES, "gender": ["Female", "Male", "Not available"],
              "type": TYPES, "juris": juris_labels}
    label_key = {"age": AGES, "gender": GENDERS_RAW, "type": TYPES, "juris": juris_labels}

    def build(dim):
        idx = {c: i for i, c in enumerate(label_key[dim])}
        out = {}
        for (muni, yr), d in acc[dim].items():
            arr = out.setdefault(f"{muni}|{yr}", [0]*len(idx))
            for cat, n in d.items():
                if cat in idx:
                    arr[idx[cat]] += n
        return out

    # grouped/classified licence classes (derived from the raw class aggregates)
    gi = {g: i for i, g in enumerate(CLASS_GROUPS)}
    class_group = {}
    for (muni, yr), d in acc["class"].items():
        arr = class_group.setdefault(f"{muni}|{yr}", [0]*len(CLASS_GROUPS))
        for cat, n in d.items():
            arr[gi[group_of(cat)]] += n

    data = {d: build(d) for d in ("age", "gender", "type", "juris")}
    data["classGroup"] = class_group
    totc = {f"{m}|{y}": v for (m, y), v in tot.items()}
    munis = sorted(m for m in muni_region if m and m != "Unknown")

    out = {
        "years": YEARS, "munis": munis, "muniRegion": muni_region,
        "regions": ["Lower Mainland", "Vancouver Island", "Southern Interior", "North Central"],
        "labels": labels, "data": data, "tot": totc,
    }
    path = os.path.join(config.OUTPUT_DIR, "licensing_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=True)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    tn = sum(v["n"] for k, v in totc.items() if k.endswith("|2025"))
    oo = sum(v["oop"] for k, v in totc.items() if k.endswith("|2025"))
    print(f"  2025 active licences={tn:,}  out-of-province={oo:,} ({100*oo/max(tn,1):.1f}%)")
    print(f"  top out-of-province origins: {juris_labels[:6]}")
    print(f"  exam classes: {exam_classes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
