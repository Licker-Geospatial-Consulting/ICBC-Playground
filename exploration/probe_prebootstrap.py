import re
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
# First, re-read the embed HTML to grab the CURRENT PreBootstrap.min.js URL
embed = requests.get(
    "https://public.tableau.com/views/VehiclePopulationIntroPage/VehiclePopulationData?:embed=y&:showVizHome=no",
    headers=HEADERS, timeout=60).text
m = re.search(r'src="([^"]*PreBootstrap[^"]*\.js)"', embed)
print("PreBootstrap URL:", m.group(1) if m else "NOT FOUND")
js = requests.get(m.group(1), headers=HEADERS, timeout=60).text
print("js len:", len(js))

# Search for endpoint-ish string literals
patterns = [
    r'bootstrapSession', r'/sessions/', r'apiID', r'sessionId', r'sessionid',
    r'vizql', r'/bootstrap', r'commands', r'ensureLayout', r'set-parameter',
    r'\.txt', r'ClientXml', r'/w/', r'/v/',
]
for p in patterns:
    idxs = [mm.start() for mm in re.finditer(p, js)]
    if idxs:
        print(f"\n=== '{p}' ({len(idxs)} hits) ===")
        for i in idxs[:4]:
            print("  ...", js[max(0, i-80):i+80].replace("\n", " "))
