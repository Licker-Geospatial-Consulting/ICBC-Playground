import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
url = "https://public.tableau.com/views/VehiclePopulationIntroPage/VehiclePopulationData?:showVizHome=no&:embed=true"

r = requests.get(url, headers=HEADERS, timeout=60)
print("--- HTML chars 4000..end ---")
print(r.text[4000:])
print("\n\n--- response headers ---")
for k, v in r.headers.items():
    print(f"{k}: {v}")
