import sys
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

targets = {
    "VehiclePopulationIntroPage.twbx": "https://public.tableau.com/workbooks/VehiclePopulationIntroPage.twbx",
    "VehiclePopulationIntroPage.twb": "https://public.tableau.com/workbooks/VehiclePopulationIntroPage.twb",
}

for fname, url in targets.items():
    print("=" * 60)
    print(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120, allow_redirects=True)
        print("status:", r.status_code, "type:", r.headers.get("Content-Type"), "len:", len(r.content))
        if r.status_code == 200 and len(r.content) > 100:
            with open(fname, "wb") as f:
                f.write(r.content)
            print("saved ->", fname, "first bytes:", r.content[:8])
    except Exception as e:
        print("ERR", type(e).__name__, str(e)[:200])
