"""Explore the ICBC Reported Crashes extract to design the map aggregation."""
import glob, os
from tableauhyperapi import HyperProcess, Telemetry, Connection

f = max(glob.glob("data/crash_hyper/icbc_reported_crashes__*public data set*.hyper"), key=os.path.getsize)
T = '"Extract"."Extract"'
print("file:", os.path.basename(f), f"({os.path.getsize(f):,} bytes)")

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database=f) as conn:
        sc = lambda q: conn.execute_scalar_query(q)
        lst = lambda q: conn.execute_list_query(q)

        n = sc(f"SELECT COUNT(*) FROM {T}")
        print("rows:", f"{n:,}")
        print("total crashes:", f"{sc(f'SELECT SUM(\"TOTAL_CRASHES\") FROM {T}'):,}",
              " total victims:", f"{sc(f'SELECT SUM(\"TOTAL_VICTIMS\") FROM {T}'):,}")

        # coordinate quality / bounds
        nulls = sc(f'SELECT COUNT(*) FROM {T} WHERE "LATITUDE" IS NULL OR "LONGITUDE" IS NULL')
        zeros = sc(f'SELECT COUNT(*) FROM {T} WHERE "LATITUDE"=0 OR "LONGITUDE"=0')
        print(f"null coords rows: {nulls:,}   zero coords rows: {zeros:,}")
        b = lst(f'SELECT MIN("LATITUDE"),MAX("LATITUDE"),MIN("LONGITUDE"),MAX("LONGITUDE") FROM {T} '
                f'WHERE "LATITUDE" BETWEEN 47 AND 61 AND "LONGITUDE" BETWEEN -140 AND -113')[0]
        print("bounds (valid): lat", b[0], b[1], " lon", b[2], b[3])

        # grid cell counts at several resolutions (province-wide, valid coords only)
        where = 'WHERE "LATITUDE" BETWEEN 47 AND 61 AND "LONGITUDE" BETWEEN -140 AND -113'
        for res in (0.05, 0.02, 0.01, 0.005):
            cells = sc(f'SELECT COUNT(*) FROM (SELECT DISTINCT ROUND("LATITUDE"/{res}), ROUND("LONGITUDE"/{res}) FROM {T} {where}) t')
            mcells = sc(f'SELECT COUNT(*) FROM (SELECT DISTINCT "MUNICIPALITY_NAME", ROUND("LATITUDE"/{res}), ROUND("LONGITUDE"/{res}) FROM {T} {where}) t')
            print(f"  res {res}deg (~{int(res*111)}km): province cells={cells:,}   (muni x cell)={mcells:,}")

        print("\ndistinct STREET_FULL_NAME:", f"{sc(f'SELECT COUNT(DISTINCT \"STREET_FULL_NAME\") FROM {T}'):,}")
        print("distinct MUNICIPALITY_NAME:", f"{sc(f'SELECT COUNT(DISTINCT \"MUNICIPALITY_NAME\") FROM {T}'):,}")

        print("\ncrashes by year:")
        for r in lst(f'SELECT "DATE_OF_LOSS_YEAR", SUM("TOTAL_CRASHES"), SUM("TOTAL_VICTIMS") FROM {T} GROUP BY 1 ORDER BY 1'):
            print(f"   {r[0]}: crashes {r[1]:,}  victims {r[2]:,}")

        print("\nroad-user involvement (crashes):")
        for flag in ("PEDESTRIAN_FLAG","CYCLIST_FLAG","MOTORCYCLE_FLAG","HEAVY_VEH_FLAG","ANIMAL_FLAG"):
            c = sc(f'SELECT SUM("TOTAL_CRASHES") FROM {T} WHERE "{flag}"=\'Y\'')
            print(f"   {flag}: {c:,}")

        print("\ntime category (crashes):")
        for r in lst(f'SELECT "TIME_CATEGORY", SUM("TOTAL_CRASHES") FROM {T} GROUP BY 1 ORDER BY 1'):
            print(f"   {r[0]}: {r[1]:,}")

        print("\ntop 12 streets by crashes:")
        for r in lst(f'SELECT "STREET_FULL_NAME", SUM("TOTAL_CRASHES") c FROM {T} GROUP BY 1 ORDER BY c DESC LIMIT 12'):
            print(f"   {r[1]:>8,}  {r[0]}")
