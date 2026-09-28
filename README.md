# ICBC BC Road Data Explorer

A Python pipeline that turns the Insurance Corporation of British Columbia (ICBC) public
data into a single interactive dashboard (plus an Excel workbook) for exploring BC's
vehicle fleet, crashes and driver licensing by community and regional district.

The dashboard is built two ways from the same source: a static site for the web
(`site/`, a small `index.html` plus JSON data files that each tab loads on demand) and a
single self-contained HTML file for sharing or offline use (`output/dashboard.html`).
Neither loads anything from third-party hosts.

## What's in the dashboard

| Tab | Data | Years | Geography |
|---|---|---|---|
| **Vehicle fleet** | Registered passenger + commercial vehicles by model year, make/model, size segment, length and net weight | 2021-2025 | Community, regional district |
| **Crashes** | ICBC-reported crashes and victims: bubble map of geocoded crash locations (intersection names on hover), top streets, crash configuration, day / month / time of day, year | 2021-2025 | Community, regional district |
| **Police crashes** | Police-reported crashes (Traffic Accident System): collision types, road and weather conditions, contributing factors, vehicles, people involved, injuries | 2020-2024 | Community (conditions and reasons), region (people and vehicles) |
| **Licensing** | Active driver licences by class group, age, gender and out-of-province origin | 2022-2025 snapshots | Community, region |

The original motivation was a hypothesis: even where traffic volumes fall, the physical
size of the vehicle fleet keeps rising. Passenger-vehicle net weight rose about 20% from
model year 2000 to 2025, and SUVs, pickups and vans now make up most of the fleet.

## Data sources and licences

| Source | Used for | Licence |
|---|---|---|
| [ICBC open data](https://public.tableau.com/app/profile/icbc) (Tableau Public) | All vehicle, crash, TAS and licensing figures | [ICBC Open Data Licence](https://www.icbc.com/policies/open-data-licence) |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) via the Overpass API | Street basemap on the crash map | ODbL 1.0 |
| [Natural Earth](https://www.naturalearthdata.com/) | Lakes and rivers | Public domain |
| Canada provinces GeoJSON ([click_that_hood](https://github.com/codeforgermany/click_that_hood)) | Simplified BC outline | See source repository |

**Attribution.** Contains information licensed under ICBC's Open Data Licence.
Map data (c) OpenStreetMap contributors.

This is an independent analysis. It is not produced, endorsed or supported by ICBC, and
any results, interpretations or derived figures are the authors' own, not ICBC's.

Raw data is **not** stored in this repository. The pipeline downloads it from the sources
above (about 900 MB) into `data/`, which is git-ignored.

### How the ICBC data is obtained

ICBC publishes its open data as Tableau Public workbooks. Each workbook can be downloaded
as a packaged `.twb` file (the dashboards' own **Download > Tableau Workbook** option),
which is a ZIP that embeds a row-level `.hyper` extract, for example:

```
https://public.tableau.com/workbooks/VehiclePopulation-PassengerVehicles-2025.twb
```

The pipeline downloads these packages, extracts the `.hyper` files and reads them with
Tableau's `tableauhyperapi`. No login, scraping of rendered pages, or private endpoints
are involved.

## Quick start

Requires Python 3.10+ (developed on 3.13, Windows).

```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Build the dashboard (downloads everything on the first run)
.\.venv\Scripts\python pipeline\run_all.py --dashboard

# Rebuild from cached downloads only
.\.venv\Scripts\python pipeline\run_all.py --dashboard --skip-download

# Excel workbook with PivotTables and slicers (needs Windows + Microsoft Excel)
.\.venv\Scripts\python pipeline\run_all.py
```

On macOS / Linux use `python3 -m venv .venv` and `.venv/bin/python`. Everything except
the Excel PivotTable step (`excel_build_pivots.py`, which drives Excel over COM) is
cross-platform.

Outputs:

- `site/`: the static site to deploy. `index.html` (~100 KB) holds the app; `data/*.json`
  holds one file per dataset, loaded the first time its tab is opened.
- `output/dashboard.html`: the same dashboard as one self-contained file (~11 MB), for
  sharing or offline use.
- `output/ICBC_Vehicle_Inventory.xlsx`: the Excel workbook.

None of these are committed; they are rebuilt from the pipeline. `pipeline/build_app.py`
builds the single file, and `pipeline/build_app.py --split` builds `site/`.

## Deploying (Cloudflare Pages)

The site is built locally and uploaded with Cloudflare's `wrangler` CLI, so Cloudflare
never has to download the ~900 MB of source data.

```powershell
# one-time
npm install -g wrangler
wrangler login
wrangler pages project create icbc-road-data --production-branch main

# each release
.\.venv\Scripts\python pipeline\run_all.py --dashboard --skip-download   # or build_app.py --split
wrangler pages deploy site --project-name icbc-road-data
```

How the site is set up for caching:

- Data files are named with a content hash (`crash_data.3407cc6e.json`) and served with
  `Cache-Control: immutable` (see `site/_headers`, written by the build). A visitor
  downloads each dataset once; a data refresh produces new names, so nobody gets stale data.
- `index.html` is always revalidated, so code changes show up on the next visit.
- Cloudflare compresses the JSON (brotli) automatically.
- A visitor who only opens the Vehicle fleet tab downloads about 0.8 MB rather than
  the full 21 MB of uncompressed data.

## Pipeline

```
pipeline/
  config.py                paths and constants
  run_all.py               orchestrator (idempotent)

  # vehicle fleet
  download_extracts.py     download vehicle-population .twb packages -> data/hyper/
  build_inventory.py       aggregate all extracts -> data/build/master_inventory.parquet
  classifier.py            size-segment + representative-length rules
  build_views.py           classify and build aggregated views
  regional_districts.py    municipality -> regional district crosswalk
  build_dashboard_data.py  vehicle fleet tab data

  # crashes, police crashes, licensing
  discover_crash_data.py   download crash / TAS / licensing packages -> data/crash_hyper/
  build_crash_data.py      crashes tab data + geocoded crash locations
  build_police_data.py     police-reported crashes tab data
  build_licensing_data.py  licensing tab data

  # map
  get_bc_outline.py        simplified BC outline
  fetch_basemap.py         OpenStreetMap roads + Natural Earth water -> data/basemap/
  build_basemap.py         simplify, quantize, tile and gzip the basemap

  # assembly
  dashboard_template.html  the dashboard app (HTML/CSS/JS) with data placeholders
  build_app.py             single file -> output/dashboard.html; --split -> site/ (static site)

  # Excel workbook
  excel_write_data.py      write data tables to xlsx (xlsxwriter)
  excel_build_pivots.py    add PivotTables + slicers via Excel COM
```

Other scripts in `pipeline/` (`check_*`, `dl_recon`, `explore_crashes`, `measure_fine_grid`,
`verify_workbook`) are one-off diagnostics. `exploration/` holds early experiments from
working out how to read the Tableau workbooks and is not needed to build anything.

**Editing the dashboard.** Change `pipeline/dashboard_template.html`, then run
`pipeline/build_app.py` (and `--split` for the site). Don't edit `output/dashboard.html`
or `site/index.html` directly: every build overwrites them.

## Methodology notes

### Vehicle size segments and length

There are about 11,000 model strings, so per-trim manufacturer specs aren't practical.
Instead every `(Make, Model, Body_Style, Vehicle_Type)` is mapped to a size segment
(Compact SUV, Full-size pickup, Midsize car and so on) using ICBC's `TRUCK/VAN` make
suffix, the body style and model-name keywords. Each segment gets a representative length
in metres (`SEGMENT_LENGTH_M` in `classifier.py`). These lengths are approximate class
averages, not measured values. Coverage is over 99.99% of vehicles.

Representative length reflects the fleet's **mix**. The measured `net_weight` is carried
alongside as an independent size signal that also captures growth within a segment.

### How weights are calculated

Both weight fields come straight from the ICBC extract, in kilograms per registration record:

- **`net_weight`**: the vehicle's empty (curb) weight. This is the size signal used throughout.
- **`licenced_gross_vehicle_weight` (GVW)**: the licensed maximum loaded weight; meaningful
  mainly for commercial vehicles. Carried through the pipeline (`gvw_sum`) but not shown by default.

The pipeline never estimates a vehicle's weight; it only aggregates ICBC's values. Each
extract row is a vehicle configuration with a `Vehicle_Count`, so averages are count-weighted:

```
# build_inventory.py (Hyper SQL GROUP BY)
net_weight_sum = SUM(net_weight * Vehicle_Count)
gvw_sum        = SUM(licenced_gross_vehicle_weight * Vehicle_Count)

# build_views.py / the Excel calculated field
average net weight (kg) = net_weight_sum / total_vehicles
```

Caveats:

- The average is per vehicle, so common models pull it toward their weight. That is what
  you want for a "typical vehicle on the road" figure.
- Some records have a missing or zero `net_weight`, mostly non-road types (ATVs,
  snowmobiles, trailers). They still count in the denominator, so mixed-segment averages
  are slightly understated. Filter to passenger / commercial car, SUV, pickup and van
  segments for clean trends.
- Weight isn't adjusted for trim or options. Treat it as a relative size indicator across
  years and communities rather than an exact spec for any single model.

### Crash locations

ICBC geocodes each reported crash to an intersection (`STREET & CROSS STREET`) or to a
mid-block address range (`STREET, 4700-4749 block`). The map plots those 137,570
locations as bubbles, merging nearby points when zoomed out. About 82% of crashes are
geocoded; the rest have no coordinates and appear in the totals and charts but not on the map.

### Police-reported crashes (TAS)

The four Traffic Accident System datasets are privacy-aggregated and share no crash ID,
so they can't be joined record by record. The dashboard filters them on the dimensions
they share (region and year, plus municipality for the crash-condition and reason
datasets). Figures are police-reported only and differ from ICBC's reported-crash counts.

### Driver licences

Licences are a **stock** (active licences at each annual snapshot), not a flow, so the
licensing tab shows one snapshot year at a time and never sums across years. The 2021
snapshot uses a different, partial format and is excluded. The
`OUT_OF_PROVINCE_JURISDICTION` field codes BC-origin licences as `Unknown` or
`Non Reciprocity`, so those values are excluded from the out-of-province share.

## Refreshing

`run_all.py` is idempotent. ICBC typically refreshes its open data once a year; schedule
`run_all.py --dashboard` with Windows Task Scheduler or cron, then run
`wrangler pages deploy site`.
