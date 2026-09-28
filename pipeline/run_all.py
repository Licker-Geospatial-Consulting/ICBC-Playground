"""
One-shot entry point for the ICBC pipeline.

    python pipeline/run_all.py                   # vehicle inventory + Excel workbook
    python pipeline/run_all.py --skip-download   # rebuild from cached extracts
    python pipeline/run_all.py --dashboard       # vehicle data + the 4-tab HTML dashboard (no Excel)

Vehicle inventory steps:
  1. download_extracts  - pull vehicle-population .hyper extracts from Tableau Public
  2. build_inventory    - aggregate into the master parquet
  3. build_views        - classify + build the aggregated views
  4. excel_write_data   - write data tables to xlsx (xlsxwriter)
  5. excel_build_pivots - add PivotTables + slicers via Excel COM (Windows + Excel only)

Dashboard steps (--dashboard, after steps 1-3):
  build_dashboard_data  - vehicle fleet tab data
  discover_crash_data   - download crash / TAS / driver-licensing extracts (and print their schemas)
  build_crash_data      - crashes tab data + geocoded crash locations
  build_police_data     - police-reported (TAS) crashes tab data
  build_licensing_data  - driver licensing tab data
  get_bc_outline        - simplified BC outline
  fetch_basemap         - OpenStreetMap roads + Natural Earth water (cached after first run)
  build_basemap         - encode the embedded street basemap
  build_app             - assemble output/dashboard.html (single file) and site/ (split static site)

Idempotent, so it can be scheduled (Task Scheduler / cron) to refresh when ICBC
publishes new data (typically annually).
"""
from __future__ import annotations

import argparse
import runpy
import sys
import time
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DASHBOARD_STEPS = ["build_dashboard_data", "discover_crash_data", "build_crash_data",
                   "build_police_data", "build_licensing_data", "get_bc_outline",
                   "fetch_basemap", "build_basemap", "build_app"]


def run(module: str):
    print(f"\n{'='*70}\n>>> {module}\n{'='*70}", flush=True)
    t0 = time.time()
    runpy.run_path(os.path.join(HERE, f"{module}.py"), run_name="__main__")
    print(f"<<< {module} done in {time.time()-t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true",
                    help="reuse cached extracts (skips both vehicle and crash/licensing downloads)")
    ap.add_argument("--skip-excel", action="store_true",
                    help="stop after building views (no Excel/COM needed)")
    ap.add_argument("--dashboard", action="store_true",
                    help="build the HTML dashboard instead of the Excel workbook")
    args = ap.parse_args()
    os.chdir(ROOT)   # some steps use paths relative to the project root

    steps = []
    if not args.skip_download:
        steps.append("download_extracts")
    steps += ["build_inventory", "build_views"]
    if args.dashboard:
        steps += [s for s in DASHBOARD_STEPS
                  if not (args.skip_download and s == "discover_crash_data")]
    else:
        steps.append("excel_write_data")
        if not args.skip_excel:
            steps.append("excel_build_pivots")

    for m in steps:
        try:
            run(m)
            if m == "build_app":            # also emit the split static site for deployment
                sys.argv = [sys.argv[0], "--split"]
                run(m)
        except SystemExit as e:            # sub-scripts call sys.exit
            if e.code not in (0, None):
                print(f"step {m} exited with code {e.code}; stopping.")
                return e.code
    print("\nALL DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
