import glob, os
from tableauhyperapi import HyperProcess, Telemetry, Connection

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HYPER_DIR = os.path.join(ROOT, "data", "hyper")
T = '"Extract"."Extract"'

files = sorted(glob.glob(os.path.join(HYPER_DIR, "*.hyper")))
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    ref_cols = None
    for f in files:
        key = os.path.splitext(os.path.basename(f))[0]
        with Connection(endpoint=hp.endpoint, database=f) as conn:
            tbl = None
            for schema in conn.catalog.get_schema_names():
                names = conn.catalog.get_table_names(schema=schema)
                if names:
                    tbl = names[0]
                    break
            if tbl is None:
                print(f"{key:20} NO TABLES FOUND")
                continue
            tq = f'{tbl}'  # TableName renders quoted+qualified
            tdef = conn.catalog.get_table_definition(tbl)
            cols = [c.name.unescaped for c in tdef.columns]
            n = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {tq}")
            vt = [r[0] for r in conn.execute_list_query(f'SELECT DISTINCT "Vehicle_Type" FROM {tq}')]
            cy = [r[0] for r in conn.execute_list_query(f'SELECT DISTINCT "Vehicle_Count_Year" FROM {tq}')]
            tot = conn.execute_scalar_query(f'SELECT SUM("Vehicle_Count") FROM {tq}')
            same = "same-cols" if ref_cols is None or cols == ref_cols else "*** DIFFERENT COLS ***"
            ref_cols = cols
            print(f"{key:20} tbl={str(tbl):28} rows={n:>9,} vehicles={tot:>12,} type={vt} yr={cy} {same}")
    print("\ncolumns:", ref_cols)
