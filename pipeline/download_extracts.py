"""
Phase 1 - Download ICBC Vehicle Population workbooks from Tableau Public and
pull out their embedded .hyper data extracts.

Each per-year / per-type workbook on Tableau Public is served at
    https://public.tableau.com/workbooks/<WorkbookName>.twb
which (despite the .twb extension) is a packaged ZIP containing a full
row-level .hyper extract. We download each, extract the single .hyper, and
store it under data/hyper/<key>.hyper. Idempotent: existing files are skipped.
"""
from __future__ import annotations

import io
import os
import sys
import time
import zipfile

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HYPER_DIR = os.path.join(ROOT, "data", "hyper")
RAW_DIR = os.path.join(ROOT, "data", "raw_twb")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

YEARS = [2021, 2022, 2023, 2024, 2025]

# key -> workbook name on Tableau Public. Core scope = passenger + commercial.
WORKBOOKS: dict[str, str] = {}
for _y in YEARS:
    WORKBOOKS[f"passenger_{_y}"] = f"VehiclePopulation-PassengerVehicles-{_y}"
    WORKBOOKS[f"commercial_{_y}"] = f"VehiclePopulation-CommercialVehicles-{_y}"


def download_workbook(key: str, workbook: str, keep_twb: bool = False) -> str:
    """Download one workbook and extract its .hyper. Returns hyper path."""
    hyper_path = os.path.join(HYPER_DIR, f"{key}.hyper")
    if os.path.exists(hyper_path) and os.path.getsize(hyper_path) > 100_000:
        print(f"  [skip] {key}: already have {os.path.basename(hyper_path)} "
              f"({os.path.getsize(hyper_path):,} bytes)")
        return hyper_path

    url = f"https://public.tableau.com/workbooks/{workbook}.twb"
    print(f"  [get ] {key}: {url}")
    r = None
    last_err = None
    for attempt in range(1, 5):  # retry transient network/DNS errors
        try:
            r = requests.get(url, headers=HEADERS, timeout=300)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            last_err = e
            wait = 3 * attempt
            print(f"         attempt {attempt} failed ({type(e).__name__}); retrying in {wait}s")
            time.sleep(wait)
    if r is None:
        raise RuntimeError(f"{workbook}: download failed after retries: {last_err}")
    if r.content[:2] != b"PK":
        raise RuntimeError(f"{workbook}: expected a packaged (ZIP) workbook, got "
                           f"{r.headers.get('Content-Type')} / {r.content[:16]!r}")
    if keep_twb:
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(os.path.join(RAW_DIR, f"{workbook}.twb"), "wb") as f:
            f.write(r.content)

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        hyper_names = [n for n in z.namelist() if n.lower().endswith(".hyper")]
        if not hyper_names:
            raise RuntimeError(f"{workbook}: no .hyper extract inside "
                               f"(contents: {z.namelist()})")
        # The per-year data workbooks contain exactly one big fact extract.
        hyper_names.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
        chosen = hyper_names[0]
        with z.open(chosen) as src, open(hyper_path, "wb") as dst:
            dst.write(src.read())
    print(f"  [ok  ] {key}: {os.path.getsize(hyper_path):,} bytes -> {hyper_path}")
    return hyper_path


def main() -> int:
    os.makedirs(HYPER_DIR, exist_ok=True)
    print(f"Downloading {len(WORKBOOKS)} workbooks into {HYPER_DIR}")
    errors = []
    for key, workbook in WORKBOOKS.items():
        try:
            download_workbook(key, workbook)
        except Exception as e:  # keep going; report at the end
            print(f"  [ERR ] {key}: {type(e).__name__}: {e}")
            errors.append((key, str(e)))
    print("\nDone." if not errors else f"\nDone with {len(errors)} error(s): {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
