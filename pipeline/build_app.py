"""Assemble the multi-tab dashboard from pipeline/dashboard_template.html.

    python pipeline/build_app.py            # single file: output/dashboard.html (all data inlined)
    python pipeline/build_app.py --split    # static site: site/index.html + site/data/*.json

Single-file build: every dataset is inlined, so the page works offline and can be
shared as one file (used for the Claude artifact).

Split build (for Cloudflare Pages or any static host): index.html holds only the app,
and each dataset is a separate JSON file that a tab fetches the first time it is
opened. Data file names carry a content hash (crash_data.1a2b3c4d.json), so they can
be cached permanently; a rebuild with changed data produces new names.
"""
import base64, gzip, hashlib, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html")
ASSETS = os.path.join(config.ROOT, "assets")
LOGO = os.path.join(ASSETS, "lgeo-logo.png")
OG_IMAGE = os.path.join(ASSETS, "og-crashes.png")     # 1200x627 link preview, made by build_preview.py

# Public address of the deployed site; social previews need absolute URLs
SITE_URL = "https://icbc-lgeo-analysis.pages.dev"
SITE_TITLE = "BC Road Data Explorer | Licker Geospatial Consulting"
SITE_DESC = ("Where crashes happen in British Columbia: 1.47 million ICBC-reported crashes "
             "mapped to 137,000 intersections, plus the vehicle fleet, police-reported crashes "
             "and driver licensing by community. Built from ICBC open data.")
OUT = os.path.join(config.OUTPUT_DIR, "dashboard.html")
SITE_DIR = os.path.join(config.ROOT, "site")

# template token -> (source file in output/, dataset file name in the split build, gzip+base64 source?)
SUBS = {
    "__DASHBOARD_DATA__": ("dashboard_data.json", "dashboard_data.json", False),
    "__CRASH_DATA__": ("crash_data.json", "crash_data.json", False),
    "__BC_OUTLINE__": ("bc_outline.json", "bc_outline.json", False),
    "__POLICE_DATA__": ("police_data.json", "police_data.json", False),
    "__LICENSING_DATA__": ("licensing_data.json", "licensing_data.json", False),
    "__BASEMAP__": ("basemap.b64", "basemap.json", True),
    "__CRASH_LOCS__": ("crash_locs.b64", "crash_locs.json", True),
}

# Cloudflare Pages headers: hashed data never changes, the page itself is revalidated
HEADERS = """/data/*
  Cache-Control: public, max-age=31536000, immutable
/
  Cache-Control: no-cache
/index.html
  Cache-Control: no-cache
"""


def read(name):
    return open(os.path.join(config.OUTPUT_DIR, name), encoding="utf-8").read()


def report(path, html):
    left = [t for t in SUBS if t in html]
    non = len(re.findall(r"[^\x00-\x7F]", html))
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    print(f"  tokens left: {left or 'none'} | non-ASCII: {non} | mdash: {'&mdash;' in html}")


def logo_uri():
    return "data:image/png;base64," + base64.b64encode(open(LOGO, "rb").read()).decode()


def site_head():
    """Document head for the static site, with Open Graph / Twitter tags so links
    shared on LinkedIn and elsewhere show a title, description and preview image."""
    img = f"{SITE_URL}/og-image.png"
    tags = [
        '<!doctype html>', '<html lang="en">', '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f'<meta name="description" content="{SITE_DESC}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{SITE_URL}/">',
        f'<meta property="og:title" content="{SITE_TITLE}">',
        f'<meta property="og:description" content="{SITE_DESC}">',
        f'<meta property="og:image" content="{img}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="627">',
        '<meta property="og:image:alt" content="Crash map of Metro Vancouver with bubbles at intersections, from the BC Road Data Explorer">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{SITE_TITLE}">',
        f'<meta name="twitter:description" content="{SITE_DESC}">',
        f'<meta name="twitter:image" content="{img}">',
        '<link rel="icon" type="image/png" href="/favicon.png">',
    ]
    return "\n".join(tags) + "\n"


def build_single(html):
    html = html.replace("__LOGO_PNG__", logo_uri())
    for token, (src, _, _) in SUBS.items():
        if token not in html:
            print(f"WARNING: token {token} not found in template")
        html = html.replace(token, read(src))
    open(OUT, "w", encoding="utf-8").write(html)
    report(OUT, html)


def build_split(html):
    html = site_head() + html.replace("__LOGO_PNG__", logo_uri())
    data_dir = os.path.join(SITE_DIR, "data")
    shutil.rmtree(data_dir, ignore_errors=True)       # drop stale hashed files
    os.makedirs(data_dir)
    total = 0
    for token, (src, name, is_gz) in SUBS.items():
        raw = (gzip.decompress(base64.b64decode(read(src))) if is_gz
               else read(src).encode("utf-8"))
        stem, ext = os.path.splitext(name)
        hashed = f"{stem}.{hashlib.sha256(raw).hexdigest()[:8]}{ext}"
        open(os.path.join(data_dir, hashed), "wb").write(raw)
        total += len(raw)
        print(f"  data/{hashed:32} {len(raw):>11,} bytes")
        # the page references the hashed name and gets no inline copy
        html = html.replace(f'file:"{name}"', f'file:"{hashed}"')
        html = html.replace(f'"{token}"', '""') if is_gz else html.replace(token, "null")
    index = os.path.join(SITE_DIR, "index.html")
    open(index, "w", encoding="utf-8").write(html)
    open(os.path.join(SITE_DIR, "_headers"), "w", encoding="utf-8").write(HEADERS)
    if os.path.exists(OG_IMAGE):
        shutil.copyfile(OG_IMAGE, os.path.join(SITE_DIR, "og-image.png"))
    else:
        print("WARNING: assets/og-crashes.png missing; run pipeline/build_preview.py for link previews")
    shutil.copyfile(os.path.join(ASSETS, "favicon.png"), os.path.join(SITE_DIR, "favicon.png"))
    report(index, html)
    print(f"  data files total {total:,} bytes (Cloudflare serves them brotli-compressed)")


def main():
    html = open(TPL, encoding="utf-8").read()
    if "--split" in sys.argv[1:]:
        build_split(html)
    else:
        build_single(html)


if __name__ == "__main__":
    main()
