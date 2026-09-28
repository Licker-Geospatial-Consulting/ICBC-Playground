"""Download the raw layers for the crash-map basemap and cache them under
data/basemap/:
  - OSM roads for British Columbia by class (Overpass API, ODbL)
  - Natural Earth 10m lakes and rivers (public domain)
Re-running skips files already downloaded."""
import json, os, sys, time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa

OUT_DIR = os.path.join(config.ROOT, "data", "basemap")
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "ICBC-dashboard/1.0 (research use)"}
BC_AREA = 3600390867  # OSM relation 390867 (British Columbia) as an Overpass area

ROAD_CLASSES = {
    "motorway": "motorway|trunk",
    "primary": "primary",
    "secondary": "secondary",
    "tertiary": "tertiary",
    "residential": "residential|unclassified|living_street",
}
NE = {
    "lakes": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_lakes.geojson",
    "rivers": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_rivers_lake_centerlines.geojson",
}


def overpass_roads(name, pattern):
    path = os.path.join(OUT_DIR, f"roads_{name}.json")
    if os.path.exists(path):
        print(f"  cached {path}")
        return
    # strip every tag except highway/name/ref so the response stays small
    q = (f'[out:json][timeout:900];area({BC_AREA})->.bc;'
         f'way["highway"~"^({pattern})(_link)?$"](area.bc);'
         f'convert way ::id=id(), ::geom=geom(), highway=t["highway"], name=t["name"], ref=t["ref"];'
         f'out geom;')
    for attempt in range(4):
        try:
            r = requests.post(OVERPASS, data={"data": q}, headers=UA, timeout=1000)
            if r.status_code == 200 and r.content.lstrip().startswith(b"{"):
                open(path, "wb").write(r.content)
                print(f"  wrote {path} ({len(r.content):,} bytes)")
                return
            print(f"  {name}: HTTP {r.status_code}, retrying")
        except requests.RequestException as e:
            print(f"  {name}: {e}, retrying")
        time.sleep(30 * (attempt + 1))
    raise SystemExit(f"failed to download {name}")


def natural_earth(name, url):
    path = os.path.join(OUT_DIR, f"ne_{name}.geojson")
    if os.path.exists(path):
        print(f"  cached {path}")
        return
    r = requests.get(url, headers=UA, timeout=300)
    r.raise_for_status()
    open(path, "wb").write(r.content)
    print(f"  wrote {path} ({len(r.content):,} bytes)")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for k, u in NE.items():
        natural_earth(k, u)
    for k, p in ROAD_CLASSES.items():
        overpass_roads(k, p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
