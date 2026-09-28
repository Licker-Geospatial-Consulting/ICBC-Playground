"""Build the vector basemap for the crash map from the layers cached by
fetch_basemap.py. Output: output/basemap.b64, a base64 string of gzipped JSON
that the page inflates with the browser's DecompressionStream.

Layout of the JSON:
  q      quantum in degrees (coordinates are integers of q)
  tile   tile size in degrees; roads are bucketed by the tile of their first point
  roads  {class: {"tx,ty": [n, x0, y0, dx1, dy1, ..., n, ...]}}  x/y relative to tile origin
  lakes  [[n, x0, y0, dx, dy, ...], ...]  one flat ring per entry (absolute origin 0,0)
  rivers same format as lakes, as polylines
  bbox   [lonMin, lonMax, latMin, latMax] of the data
"""
import base64, gzip, json, math, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa

SRC = os.path.join(config.ROOT, "data", "basemap")
OUT = os.path.join(config.OUTPUT_DIR, "basemap.b64")

Q = 5e-5          # ~5.5 m quantum
TILE = 0.2        # degrees
BC = (-139.2, -114.0, 48.2, 60.1)
# per-class Douglas-Peucker tolerance in degrees
TOL = {"motorway": 6e-5, "primary": 6e-5, "secondary": 6e-5, "tertiary": 6e-5, "residential": 6e-5}
# link roads are drawn one tier lower so ramps don't read as highways when zoomed out
LINK_DEMOTE = {"motorway": "secondary", "primary": "secondary", "secondary": "tertiary", "tertiary": "tertiary"}


def dp(pts, tol):
    """Iterative Douglas-Peucker on [(x, y), ...] with a lon-scaled distance."""
    n = len(pts)
    if n < 3:
        return pts
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        best, bi = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            if L2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
                d = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if d > best:
                best, bi = d, k
        if best > tol:
            keep[bi] = True
            stack.append((i, bi))
            stack.append((bi, j))
    return [p for p, k in zip(pts, keep) if k]


def lonscale(lat):
    return math.cos(math.radians(lat))


def quantize(coords, tol):
    """lon/lat list -> simplified list of integer (x, y) with duplicate points removed."""
    if not coords:
        return []
    c = math.cos(math.radians(coords[0][1]))
    # simplify in an approximately equal-distance space (lon scaled by cos(lat))
    pts = [(lon * c, lat) for lon, lat in coords]
    pts = dp(pts, tol)
    out = []
    for x, y in pts:
        q = (round(x / c / Q), round(y / Q))
        if not out or out[-1] != q:
            out.append(q)
    return out


def enc(pts, ox, oy):
    """[(x, y)] -> [n, x0-ox, y0-oy, dx, dy, ...]"""
    arr = [len(pts), pts[0][0] - ox, pts[0][1] - oy]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        arr += [x1 - x0, y1 - y0]
    return arr


def in_bc(coords):
    return any(BC[0] <= lon <= BC[1] and BC[2] <= lat <= BC[3] for lon, lat in coords)


def main():
    roads = defaultdict(lambda: defaultdict(list))
    stats = {}
    tq = round(TILE / Q)
    for cls in ["motorway", "primary", "secondary", "tertiary", "residential"]:
        d = json.load(open(os.path.join(SRC, f"roads_{cls}.json"), encoding="utf-8"))
        npts = nlines = 0
        for el in d["elements"]:
            g = el.get("geometry") or {}
            if g.get("type") != "LineString":
                continue
            hw = (el.get("tags") or {}).get("highway", "")
            target = LINK_DEMOTE.get(cls, cls) if hw.endswith("_link") else cls
            pts = quantize(g["coordinates"], TOL[target])
            if len(pts) < 2:
                continue
            tx, ty = math.floor(pts[0][0] / tq), math.floor(pts[0][1] / tq)
            roads[target][f"{tx},{ty}"].extend(enc(pts, tx * tq, ty * tq))
            npts += len(pts); nlines += 1
        stats[cls] = (nlines, npts)
        print(f"  {cls:12} lines={nlines:>7,} points={npts:>9,}")

    def ne_layer(name, kind, tol, min_extent=0.0):
        d = json.load(open(os.path.join(SRC, f"ne_{name}.geojson"), encoding="utf-8"))
        out = []
        for f in d["features"]:
            g = f["geometry"]
            if not g:
                continue
            if g["type"] in ("Polygon", "LineString"):
                parts = [g["coordinates"]]
            else:
                parts = g["coordinates"]
            for part in parts:
                rings = part if kind == "poly" else [part]
                for ring in rings[:1] if kind == "poly" else rings:
                    if not in_bc(ring):
                        continue
                    lo = [p[0] for p in ring]; la = [p[1] for p in ring]
                    if max(max(lo) - min(lo), max(la) - min(la)) < min_extent:
                        continue
                    pts = quantize(ring, tol)
                    if len(pts) >= (4 if kind == "poly" else 2):
                        out.append(enc(pts, 0, 0))
        print(f"  {name:12} parts={len(out):>7,}")
        return out

    lakes = ne_layer("lakes", "poly", 4e-4, 0.02)
    rivers = ne_layer("rivers", "line", 4e-4)

    data = {"q": Q, "tile": TILE, "roads": roads, "lakes": lakes, "rivers": rivers,
            "classes": ["motorway", "primary", "secondary", "tertiary", "residential"],
            "attribution": "Roads (c) OpenStreetMap contributors, ODbL. Lakes/rivers: Natural Earth."}
    raw = json.dumps(data, separators=(",", ":")).encode()
    gz = gzip.compress(raw, 9)
    b64 = base64.b64encode(gz).decode()
    open(OUT, "w").write(b64)
    per = {c: len(json.dumps(v, separators=(",", ":"))) for c, v in roads.items()}
    print(f"  raw json {len(raw):,}  gzip {len(gz):,}  base64 {len(b64):,} -> {OUT}")
    print("  raw per class:", {k: f"{v:,}" for k, v in per.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
