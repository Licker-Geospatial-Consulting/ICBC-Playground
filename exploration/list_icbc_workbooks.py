import json
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
           "Accept": "application/json"}

# Tableau Public profile workbooks API
for url in [
    "https://public.tableau.com/profile/api/icbc/workbooks?count=200&index=0",
    "https://public.tableau.com/api/search/query?count=200&start=0&language=en-us&query=&type=vizzes&profileUrl=icbc",
]:
    print("=" * 70)
    print(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        print("status:", r.status_code, "type:", r.headers.get("Content-Type"), "len:", len(r.content))
        if "json" in (r.headers.get("Content-Type") or ""):
            data = r.json()
            print("top keys:", list(data)[:20] if isinstance(data, dict) else type(data))
            js = json.dumps(data)
            # find workbook repo/title fields
            print(json.dumps(data, indent=2)[:2000])
    except Exception as e:
        print("ERR", type(e).__name__, str(e)[:200])
