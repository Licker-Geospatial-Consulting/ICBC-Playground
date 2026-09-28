"""
Reconnaissance for the crash / TAS / licensing dashboards the user wants to add.

Downloads each Tableau workbook (.twb, which is a packaged ZIP with an embedded
.hyper extract), then prints for each extract: table, row count, columns+types,
and for low-cardinality TEXT columns the distinct values (so we can see what
dimensions/measures exist and whether any geographic coordinates are present).
"""
from __future__ import annotations
import io, os, sys, zipfile
import requests
from tableauhyperapi import HyperProcess, Telemetry, Connection

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEST = os.path.join(ROOT, "data", "crash_hyper")
os.makedirs(DEST, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}

WORKBOOKS = {
    "icbc_reported_crashes": "ICBCReportedCrashes",
    "tas_no_contrib": "TAS-CrashesNoContributingFactors",
    "tas_no_month": "TAS-CrashesNoMonth",
    "tas_entity": "TAS-Entity",
    "tas_victim": "TAS-Victim",
    "driver_licensing": "PublicDatasetDashboard-Activedriverlicencesroadtestsandknowledgetests",
}


def fetch_hypers(key, wb):
    url = f"https://public.tableau.com/workbooks/{wb}.twb"
    r = requests.get(url, headers=HEADERS, timeout=300)
    print(f"\n{'#'*90}\n# {key}  ({wb})\n#  status={r.status_code} type={r.headers.get('Content-Type')} bytes={len(r.content):,}")
    if r.status_code != 200 or r.content[:2] != b"PK":
        print("#  NOT a packaged workbook (no embedded extract) - may be an intro page.")
        return []
    out = []
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        hypers = [n for n in z.namelist() if n.lower().endswith(".hyper")]
        print(f"#  ZIP contents: {len(z.namelist())} files; {len(hypers)} .hyper")
        for n in z.namelist():
            print(f"#     {z.getinfo(n).file_size:>13,}  {n}")
        for n in hypers:
            path = os.path.join(DEST, f"{key}__{os.path.basename(n)}")
            with z.open(n) as src, open(path, "wb") as dst:
                dst.write(src.read())
            out.append(path)
    return out


def inspect(hp, path):
    with Connection(endpoint=hp.endpoint, database=path) as conn:
        tbl = None
        for schema in conn.catalog.get_schema_names():
            names = conn.catalog.get_table_names(schema=schema)
            if names:
                tbl = names[0]; break
        if tbl is None:
            print("   (no tables)"); return
        tdef = conn.catalog.get_table_definition(tbl)
        n = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {tbl}")
        print(f"\n   TABLE {tbl}  rows={n:,}  cols={len(tdef.columns)}")
        for c in tdef.columns:
            cname = c.name.unescaped
            typ = str(c.type)
            note = ""
            if "TEXT" in typ.upper():
                try:
                    d = conn.execute_scalar_query(f'SELECT COUNT(DISTINCT "{cname}") FROM {tbl}')
                    note = f"  distinct={d}"
                    if d <= 40:
                        vals = [str(r[0]) for r in conn.execute_list_query(
                            f'SELECT DISTINCT "{cname}" FROM {tbl} ORDER BY 1 LIMIT 40')]
                        note += "  vals=" + repr(vals)[:400]
                except Exception as e:
                    note = f"  (distinct err {e})"
            print(f"      - {cname} :: {typ}{note}")


def main():
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        for key, wb in WORKBOOKS.items():
            try:
                for path in fetch_hypers(key, wb):
                    inspect(hp, path)
            except Exception as e:
                print(f"#  ERROR {key}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
