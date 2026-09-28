import json
import uuid
import requests

WB, VIEW = "VehiclePopulationIntroPage", "VehiclePopulationData"
BASE = "https://public.tableau.com"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36",
                  "Accept-Language": "en-US,en;q=0.9"})

embed_url = f"{BASE}/views/{WB}/{VIEW}?:embed=y&:showVizHome=no&:language=en-US"
r0 = S.get(embed_url, timeout=60)
gsh = r0.headers.get("global-session-header")

ss_url = f"{BASE}/vizql/w/{WB}/v/{VIEW}/startSession/viewing"
headers = {"X-B3-TraceID": uuid.uuid4().hex, "X-B3-SpanID": uuid.uuid4().hex,
           "X-B3-Sampled": "1", "Accept": "text/javascript", "Origin": BASE, "Referer": embed_url}
if gsh:
    headers["Global-Session-Header"] = gsh
r1 = S.post(ss_url, headers=headers, timeout=90)
data = r1.json()
with open("startSession.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("saved startSession.json, top-level keys:")
for k in data:
    v = data[k]
    print(f"  {k}: {type(v).__name__}" + (f" (len {len(v)})" if isinstance(v, (list, dict, str)) else f" = {v}"))

# hunt for interesting substrings across the raw text
raw = r1.text
for key in ["presModel", "worksheet", "dataDictionary", "Municipality", "sheetName",
            "sessionId", "newBootstrap", "vqlCmdResponse", "secondaryInfo", "MODEL YEAR",
            "bootstrapResponse", "vizStateList", "sheetPath"]:
    print(f"  '{key}' present: {key in raw}  count={raw.count(key)}")
