import zipfile, io, os
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
wb = "VehiclePopulation-PassengerVehicles-2025"

for ext in (".twb", ".twbx"):
    url = f"https://public.tableau.com/workbooks/{wb}{ext}"
    print("=" * 70)
    print(url)
    r = requests.get(url, headers=HEADERS, timeout=120)
    print("status:", r.status_code, "type:", r.headers.get("Content-Type"), "len:", len(r.content))
    if r.status_code != 200 or len(r.content) < 100:
        continue
    head = r.content[:4]
    print("head bytes:", head)
    if head[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(r.content))
        print("ZIP contents:")
        for info in z.infolist():
            print(f"   {info.file_size:>13,}  {info.filename}")
        # save it
        fn = f"{wb}{ext}"
        with open(fn, "wb") as f:
            f.write(r.content)
        print("saved", fn)
        break
    else:
        print("not a zip (raw XML .twb)")
