import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Candidate direct workbook download endpoints on Tableau Public
CANDS = [
    "https://public.tableau.com/workbooks/VehiclePopulationIntroPage.twb",
    "https://public.tableau.com/workbooks/VehiclePopulationIntroPage.twbx",
    "https://public.tableau.com/app/profile/icbc/vizzes",  # profile listing
    # Public REST used by the site to list a profile's workbooks
    "https://public.tableau.com/profile/api/icbc/workbooks?count=100",
]

for url in CANDS:
    print("=" * 70)
    print(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        print("status:", r.status_code, "type:", ct, "len:", len(r.content))
        if "json" in ct:
            print(r.text[:1500])
        elif "xml" in ct or url.endswith(".twb"):
            print(r.text[:600])
        else:
            print("bytes head:", r.content[:16])
    except Exception as e:
        print("ERR", repr(e))
