import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
YEARS = [2021, 2022, 2023, 2024, 2025]

candidates = []
for y in YEARS:
    candidates.append(f"VehiclePopulation-PassengerVehicles-{y}")
    candidates.append(f"VehiclePopulation-CommercialVehicles-{y}")
# "other" types - guesses (labels said 2021-2025, likely single multi-year workbooks)
candidates += [
    "VehiclePopulation-Motorhomes", "VehiclePopulation-Motorcycles",
    "VehiclePopulation-Trailers", "VehiclePopulation-ElectricVehicles",
    "VehiclePopulation-HybridVehicles", "VehiclePopulation-Electricvehicles",
    "VehiclePopulation-Hybridvehicles",
    "VehiclePopulation-VehiclePoliciesinForce", "VehiclePopulation-VehiclePoliciesInForce",
    "VehiclePopulationIntroPage",
]

def check(name):
    url = f"https://public.tableau.com/workbooks/{name}.twb"
    try:
        r = requests.head(url, headers=HEADERS, timeout=40, allow_redirects=True)
        cl = r.headers.get("Content-Length")
        ct = r.headers.get("Content-Type")
        return r.status_code, ct, cl
    except Exception as e:
        return "ERR", type(e).__name__, str(e)[:80]

for name in candidates:
    sc, ct, cl = check(name)
    ok = "OK " if sc == 200 else "   "
    size = f"{int(cl):,}" if (cl and str(cl).isdigit()) else cl
    print(f"  {ok}{sc}  {ct}  {size}  {name}")
