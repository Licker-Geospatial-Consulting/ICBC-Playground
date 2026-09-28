import uuid
import requests

WB, VIEW = "VehiclePopulationIntroPage", "VehiclePopulationData"
BASE = "https://public.tableau.com"
S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})

embed_url = f"{BASE}/views/{WB}/{VIEW}?:embed=y&:showVizHome=no&:language=en-US"
r0 = S.get(embed_url, timeout=60)
print("embed GET:", r0.status_code)
gsh = r0.headers.get("global-session-header") or r0.headers.get("Global-Session-Header")
xsid = r0.headers.get("x-session-id") or r0.headers.get("X-Session-Id")
print("global-session-header:", gsh)
print("x-session-id:", xsid)
print("cookies:", S.cookies.get_dict())

ss_url = f"{BASE}/vizql/w/{WB}/v/{VIEW}/startSession/viewing"
headers = {
    "X-B3-TraceID": uuid.uuid4().hex,
    "X-B3-SpanID": uuid.uuid4().hex,
    "X-B3-Sampled": "1",
    "Accept": "text/javascript",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE,
    "Referer": embed_url,
}
if gsh:
    headers["Global-Session-Header"] = gsh

r1 = S.post(ss_url, headers=headers, timeout=90)
print("\nstartSession POST:", r1.status_code, "type:", r1.headers.get("Content-Type"), "len:", len(r1.content))
print("resp X-Session-Id:", r1.headers.get("X-Session-Id") or r1.headers.get("x-session-id"))
print("resp global-session-header:", r1.headers.get("global-session-header"))
print("\n--- body head (first 1500 chars) ---")
print(r1.text[:1500])
