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


def build_single(html):
    for token, (src, _, _) in SUBS.items():
        if token not in html:
            print(f"WARNING: token {token} not found in template")
        html = html.replace(token, read(src))
    open(OUT, "w", encoding="utf-8").write(html)
    report(OUT, html)


def build_split(html):
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
