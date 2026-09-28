"""Recon the driver-licensing hyper extracts: table, rows, key columns, and
distinct EXTRACT_YEAR, so we know which files are DL snapshots (and their years)
vs the exam table vs metadata."""
import glob, os
from tableauhyperapi import HyperProcess, Telemetry, Connection

CRASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "crash_hyper")
files = sorted(glob.glob(os.path.join(CRASH_DIR, "driver_licensing__*.hyper")), key=os.path.getsize, reverse=True)

DLKEYS = {"LICENCE_CLASS", "AGE_RANGE", "EXTRACT_YEAR", "ISSUE_YEAR", "OUT_OF_PROVINCE_JURISDICTION"}

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    for f in files:
        with Connection(endpoint=hp.endpoint, database=f) as conn:
            tbl = None
            for s in conn.catalog.get_schema_names():
                n = conn.catalog.get_table_names(schema=s)
                if n:
                    tbl = n[0]; break
            if not tbl:
                continue
            cols = [c.name.unescaped for c in conn.catalog.get_table_definition(tbl).columns]
            rows = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {tbl}")
            isdl = DLKEYS.issubset(set(cols))
            yrs = ""
            if "EXTRACT_YEAR" in cols:
                yrs = [r[0] for r in conn.execute_list_query(f'SELECT DISTINCT "EXTRACT_YEAR" FROM {tbl} ORDER BY 1')]
            elif "Exam_Year" in cols:
                yrs = "EXAM: " + str([r[0] for r in conn.execute_list_query(f'SELECT DISTINCT "Exam_Year" FROM {tbl} ORDER BY 1')])
            print(f"{os.path.basename(f):55} rows={rows:>9,} DLsnapshot={isdl} extract_years={yrs}")
            if isdl or "Exam_Year" in cols:
                print(f"     cols: {cols}")
