import re
import requests

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                  "Accept-Language": "en-US,en;q=0.9"})

WB, VIEW = "VehiclePopulationIntroPage", "VehiclePopulationData"

variants = [
    ("GET", f"https://public.tableau.com/views/{WB}/{VIEW}?:embed=y&:showVizHome=no"),
    ("GET", f"https://public.tableau.com/vizql/w/{WB}/v/{VIEW}?:embed=y&:showVizHome=no"),
    ("GET", f"https://public.tableau.com/vizql/w/{WB}/v/{VIEW}/viewData/sessions"),
    ("GET", f"https://public.tableau.com/views/{WB}/{VIEW}?:embed=y&:showVizHome=no&:apiID=host0"),
]

def scan(txt):
    hits = {}
    for key in ["sessionid", "\"session\"", "vizql_root", "sheetId", "current_sheet_name",
                "bootstrapSession", "tsConfigContainer", "sessionId"]:
        if key.lower() in txt.lower():
            hits[key] = True
    # pull an actual sessionid if present
    m = re.search(r'"sessionid"\s*:\s*"([^"]+)"', txt)
    if m:
        hits["SESSIONID_VALUE"] = m.group(1)
    return hits

for method, url in variants:
    print("=" * 70)
    print(method, url)
    try:
        r = S.request(method, url, timeout=60, allow_redirects=True)
        print("status:", r.status_code, "type:", r.headers.get("Content-Type"), "len:", len(r.text))
        print("final url:", r.url)
        # Check for populated tsConfig textarea
        m = re.search(r'id="tsConfigContainer"[^>]*>(.*?)</textarea>', r.text, re.S)
        if m:
            print("tsConfig len:", len(m.group(1).strip()))
        print("scan:", scan(r.text))
    except Exception as e:
        print("ERR", type(e).__name__, str(e)[:200])
