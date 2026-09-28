"""Fetch a public Canada provinces GeoJSON, extract British Columbia, simplify
the rings (pure-Python Douglas-Peucker) and drop tiny islands, then save a
compact outline (list of [lon,lat] rings) for embedding in the crash map."""
import json, math, os
import requests

URLS = [
    "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/canada.geojson",
    "https://raw.githubusercontent.com/rowanwins/leaflet-easyPrint/gh-pages/dist/canada.geojson",
]
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "bc_outline.json")

TOL = 0.02        # ~2km simplification tolerance
MIN_AREA = 0.004  # drop rings smaller than this (deg^2) ~ tiny islands


def perp_dist(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    return math.hypot(x - (x1 + t*dx), y - (y1 + t*dy))


def dp(points, tol):
    if len(points) < 3:
        return points
    dmax, idx = 0, 0
    for i in range(1, len(points) - 1):
        d = perp_dist(points[i], points[0], points[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        left = dp(points[:idx+1], tol)
        right = dp(points[idx:], tol)
        return left[:-1] + right
    return [points[0], points[-1]]


def area(ring):
    s = 0
    for i in range(len(ring)):
        x1, y1 = ring[i]; x2, y2 = ring[(i+1) % len(ring)]
        s += x1*y2 - x2*y1
    return abs(s) / 2


def main():
    gj = None
    for url in URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                gj = r.json(); print("fetched", url); break
        except Exception as e:
            print("fail", url, e)
    if gj is None:
        raise SystemExit("could not fetch provinces geojson")

    feat = None
    for ft in gj["features"]:
        name = json.dumps(ft.get("properties", {}))
        if "British Columbia" in name or "Colombie-Britannique" in name:
            feat = ft; break
    if feat is None:
        raise SystemExit("BC feature not found")

    geom = feat["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    rings_out = []
    for poly in polys:
        outer = poly[0]  # exterior ring
        ring = [[round(x, 4), round(y, 4)] for x, y in outer]
        if area(ring) < MIN_AREA:
            continue
        simp = dp(ring, TOL)
        rings_out.append(simp)
    rings_out.sort(key=area, reverse=True)
    pts = sum(len(r) for r in rings_out)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"rings": rings_out}, f, separators=(",", ":"))
    print(f"BC outline: {len(rings_out)} rings, {pts} points -> {OUT} ({os.path.getsize(OUT):,} bytes)")
    # bounds
    xs = [x for r in rings_out for x, y in r]; ys = [y for r in rings_out for x, y in r]
    print(f"  lon {min(xs):.2f}..{max(xs):.2f}  lat {min(ys):.2f}..{max(ys):.2f}")


if __name__ == "__main__":
    main()
