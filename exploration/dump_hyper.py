"""Dump schemas, tables, row counts and a sample of every .hyper extract."""
import glob
import os

from tableauhyperapi import HyperProcess, Telemetry, Connection, TableName

HYPER_DIR = "workbook_extracted/Data/Extracts"


def main():
    files = sorted(glob.glob(os.path.join(HYPER_DIR, "*.hyper")))
    print(f"Found {len(files)} hyper files\n")
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        for f in files:
            print("#" * 80)
            print("FILE:", os.path.basename(f), f"({os.path.getsize(f):,} bytes)")
            with Connection(endpoint=hp.endpoint, database=f) as conn:
                schemas = conn.catalog.get_schema_names()
                for schema in schemas:
                    tables = conn.catalog.get_table_names(schema=schema)
                    for tbl in tables:
                        tdef = conn.catalog.get_table_definition(tbl)
                        cols = [(c.name.unescaped, str(c.type)) for c in tdef.columns]
                        try:
                            n = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {tbl}")
                        except Exception as e:
                            n = f"count err: {e}"
                        print(f"\n  TABLE {tbl}  rows={n}")
                        print(f"    columns ({len(cols)}):")
                        for name, typ in cols:
                            print(f"      - {name} :: {typ}")
                        # sample rows
                        try:
                            rows = conn.execute_list_query(f"SELECT * FROM {tbl} LIMIT 5")
                            print("    sample:")
                            for r in rows:
                                vals = [str(v)[:40] for v in r]
                                print("      ", vals)
                        except Exception as e:
                            print("    sample err:", e)


if __name__ == "__main__":
    main()
