import re
import requests

CANDIDATES = [
    "https://public.tableau.com/views/VehiclePopulationIntroPage/VehiclePopulationData",
    "https://public.tableau.com/views/VehiclePopulationIntroPage/VehiclePopulationData?:showVizHome=no&:embed=true",
    "https://public.tableau.com/app/profile/icbc/viz/VehiclePopulationIntroPage/VehiclePopulationData",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for url in CANDIDATES:
    print("=" * 70)
    print(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        print("status:", r.status_code, "len:", len(r.text))
        print("has tsConfigContainer:", "tsConfigContainer" in r.text)
        # Try to find the vizql/session hints or any workbook/view names
        for pat in [r'tsConfigContainer', r'"workbookName"\s*:\s*"[^"]+"',
                    r'"sheetId"\s*:\s*"[^"]+"', r'current_sheet_name',
                    r'/views/[A-Za-z0-9_]+/[A-Za-z0-9_]+']:
            m = re.findall(pat, r.text)
            if m:
                print(f"  {pat} -> {list(dict.fromkeys(m))[:8]}")
    except Exception as e:
        print("ERR", repr(e))
