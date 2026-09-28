import glob, os
from tableauhyperapi import HyperProcess, Telemetry, Connection
f = max(glob.glob("data/crash_hyper/icbc_reported_crashes__*public data set*.hyper"), key=os.path.getsize)
T='"Extract"."Extract"'
where='WHERE "LATITUDE" BETWEEN 47 AND 61 AND "LONGITUDE" BETWEEN -140 AND -113'
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database=f) as conn:
        for res in (0.0025, 0.002, 0.001):
            n=conn.execute_scalar_query(f'SELECT COUNT(*) FROM (SELECT DISTINCT ROUND("LATITUDE"/{res}),ROUND("LONGITUDE"/{res}) FROM {T} {where}) t')
            # rough JSON size: cells * 13 numbers * ~5 chars
            print(f"res {res} (~{int(res*111000)}m): {n:,} cells  ~{n*13*5/1e6:.1f}MB dense-13  ~{n*7*5/1e6:.1f}MB slim-7")
