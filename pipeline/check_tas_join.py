"""Check whether the 4 TAS extracts can be joined: look for a common key,
confirm which have MUNICIPALITY, and measure grain (count per row)."""
import glob, os
from tableauhyperapi import HyperProcess, Telemetry, Connection

CRASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "crash_hyper")
DS = {
    "no_contrib": ("tas_no_contrib", "CRASH_COUNT"),
    "no_month": ("tas_no_month", "CRASH_COUNT"),
    "entity": ("tas_entity", "ENTITY_COUNT"),
    "victim": ("tas_victim", "VICTIM_COUNT"),
}


def first_tbl(conn):
    for s in conn.catalog.get_schema_names():
        n = conn.catalog.get_table_names(schema=s)
        if n:
            return n[0]


with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    for name, (key, measure) in DS.items():
        f = max(glob.glob(os.path.join(CRASH_DIR, f"{key}__*.hyper")), key=os.path.getsize)
        with Connection(endpoint=hp.endpoint, database=f) as conn:
            tbl = first_tbl(conn)
            tdef = conn.catalog.get_table_definition(tbl)
            cols = [c.name.unescaped for c in tdef.columns]
            rows = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {tbl}")
            tot = conn.execute_scalar_query(f'SELECT SUM("{measure}") FROM {tbl}')
            has_muni = "MUNICIPALITY" in cols
            nmuni = conn.execute_scalar_query(f'SELECT COUNT(DISTINCT "MUNICIPALITY") FROM {tbl}') if has_muni else 0
            has_month = "MONTH" in cols
            idlike = [c for c in cols if any(k in c.upper() for k in ("ID", "NUMBER", "REF", "KEY", "ACCIDENT_NO", "CASE"))]
            print(f"\n{name}: rows={rows:,}  sum({measure})={tot:,}  ratio={tot/rows:.3f}")
            print(f"   MUNICIPALITY={has_muni} (distinct={nmuni})   MONTH={has_month}")
            print(f"   id-like columns: {idlike or 'NONE'}")
            print(f"   all columns: {cols}")
