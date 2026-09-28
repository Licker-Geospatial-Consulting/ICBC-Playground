import re
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
js = requests.get(
    "https://d1ixzvs6g7du49.cloudfront.net/assets/vizql/v_202622608181324/javascripts/PreBootstrap.min.js",
    headers=HEADERS, timeout=60).text

for p in ["startSession", "global-session-header", "ingressProxy", "X-Tsi",
          "stickySessionKey", "FromHeaders", "method:", "\"POST\"", "'POST'",
          "worksheetPortSize", "clientDimension", "sheet_id", "apiID",
          "text/javascript", "FormData", "sessionRoute", "vizqlRoot="]:
    idxs = [mm.start() for mm in re.finditer(re.escape(p), js)]
    if idxs:
        print(f"\n=== '{p}' ({len(idxs)} hits) ===")
        for i in idxs[:3]:
            print("  ", js[max(0, i-120):i+120].replace("\n", " "))
