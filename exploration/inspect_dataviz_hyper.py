import zipfile, os
from tableauhyperapi import HyperProcess, Telemetry, Connection

TWB = "VehiclePopulation-PassengerVehicles-2025.twb"
OUT = "extract_2025_passenger"
os.makedirs(OUT, exist_ok=True)
with zipfile.ZipFile(TWB) as z:
    hyper_name = [n for n in z.namelist() if n.endswith(".hyper")][0]
    z.extract(hyper_name, OUT)
    hyper_path = os.path.join(OUT, hyper_name)
print("hyper:", hyper_path, f"({os.path.getsize(hyper_path):,} bytes)")

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database=hyper_path) as conn:
        for schema in conn.catalog.get_schema_names():
            for tbl in conn.catalog.get_table_names(schema=schema):
                tdef = conn.catalog.get_table_definition(tbl)
                n = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {tbl}")
                print(f"\nTABLE {tbl}  rows={n:,}")
                for c in tdef.columns:
                    print(f"   - {c.name.unescaped} :: {c.type}")
                print("\n  sample rows:")
                for row in conn.execute_list_query(f"SELECT * FROM {tbl} LIMIT 8"):
                    print("   ", [str(v)[:22] for v in row])
