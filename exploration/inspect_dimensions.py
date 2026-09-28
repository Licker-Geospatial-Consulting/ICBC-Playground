import glob, os
from tableauhyperapi import HyperProcess, Telemetry, Connection

hyper_path = glob.glob("extract_2025_passenger/**/*.hyper", recursive=True)[0]
T = '"Extract"."Extract"'

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database=hyper_path) as conn:
        def q(sql):
            return conn.execute_list_query(sql)
        def scalar(sql):
            return conn.execute_scalar_query(sql)

        print("total rows:", f"{scalar(f'SELECT COUNT(*) FROM {T}'):,}")
        for col in ["Make", "Model", "Model_year", "Municipality", "Region",
                    "Vehicle_Use", "Body_Style", "Fuel_Type", "Person_Org_Type"]:
            n = scalar(f'SELECT COUNT(DISTINCT "{col}") FROM {T}')
            print(f"  distinct {col}: {n:,}")

        print("\n=== distinct BODY_STYLE with total counts ===")
        for r in q(f'SELECT "Body_Style", SUM("Vehicle_Count") c, COUNT(*) rows FROM {T} '
                   f'GROUP BY "Body_Style" ORDER BY c DESC'):
            print(f"  {str(r[0]):<28} vehicles={r[1]:>10,}  combos={r[2]:>7,}")

        print("\n=== top 25 MAKES by vehicle count ===")
        for r in q(f'SELECT "Make", SUM("Vehicle_Count") c FROM {T} GROUP BY "Make" ORDER BY c DESC LIMIT 25'):
            print(f"  {str(r[0]):<20} {r[1]:>10,}")

        print("\n=== distinct Model_year values ===")
        yrs = [str(r[0]) for r in q(f'SELECT DISTINCT "Model_year" FROM {T} ORDER BY "Model_year"')]
        print("  count:", len(yrs), " range:", yrs[:5], "...", yrs[-5:])
