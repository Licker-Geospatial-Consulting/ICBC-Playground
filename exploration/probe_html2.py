import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
url = "https://public.tableau.com/views/VehiclePopulationIntroPage/VehiclePopulationData?:showVizHome=no&:embed=true"

r = requests.get(url, headers=HEADERS, timeout=60)
print("status", r.status_code, "len", len(r.text))
soup = BeautifulSoup(r.text, "html.parser")
ta = soup.find("textarea", {"id": "tsConfigContainer"})
print("textarea found:", ta is not None)
if ta:
    print("textarea text len:", len(ta.text))
    print(repr(ta.text[:500]))
print("\n--- FULL HTML (first 4000 chars) ---")
print(r.text[:4000])
