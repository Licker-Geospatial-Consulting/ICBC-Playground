"""
Bridge that lets the (otherwise broken-on-modern-vizzes) TableauScraper library
work against Tableau Public's new PreBootstrap "thin client" flow.

The modern flow no longer inlines the viz config in the page's
`tsConfigContainer` textarea. Instead the browser:
  1. GETs the embed shell (which carries a `global-session-header` for ingress
     proxy affinity),
  2. POSTs `/vizql/w/<wb>/v/<view>/startSession/viewing` which returns the full
     session config JSON (sessionid, sheetId, vizql_root, ...) plus an
     `X-Session-Id` response header.

Once we have that config we can hand it to TableauScraper exactly where its
`loads()` would have, and every downstream command (filters, worksheets,
underlying data, crosstab export) works unchanged.
"""
import json
import re
import uuid

import requests
from tableauscraper import TableauScraper as TS
from tableauscraper import api, utils

BASE = "https://public.tableau.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _start_session(workbook: str, view: str, session: requests.Session) -> dict:
    """Perform the modern startSession handshake; returns the config dict.

    Also pins ingress-proxy / session-affinity headers onto `session` so every
    subsequent vizql command lands on the same backend.
    """
    embed_url = f"{BASE}/views/{workbook}/{view}?:embed=y&:showVizHome=no&:language=en-US"
    r0 = session.get(embed_url, timeout=60)
    r0.raise_for_status()
    gsh = r0.headers.get("global-session-header")

    ss_url = f"{BASE}/vizql/w/{workbook}/v/{view}/startSession/viewing"
    headers = {
        "X-B3-TraceID": uuid.uuid4().hex,
        "X-B3-SpanID": uuid.uuid4().hex,
        "X-B3-Sampled": "1",
        "Accept": "text/javascript",
        "Origin": BASE,
        "Referer": embed_url,
    }
    if gsh:
        headers["Global-Session-Header"] = gsh
    r1 = session.post(ss_url, headers=headers, timeout=90)
    r1.raise_for_status()
    cfg = r1.json()

    # Pin affinity headers for all later requests.
    affinity = {}
    xsid = r1.headers.get("X-Session-Id") or r1.headers.get("x-session-id")
    if xsid:
        affinity["X-Session-Id"] = xsid
    new_gsh = r1.headers.get("global-session-header") or gsh
    if new_gsh:
        affinity["Global-Session-Header"] = new_gsh
    session.headers.update(affinity)
    return cfg


def load_workbook(workbook: str, view: str, delay_ms: int = 600):
    """Return (ts, workbook) where ts is a ready TableauScraper and workbook is
    the parsed TableauWorkbook for the default view."""
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

    cfg = _start_session(workbook, view, session)

    ts = TS(delayMs=delay_ms)
    ts.session = session
    ts.tableauData = cfg
    ts.host = BASE

    # Replicate TableauScraper.loads() lines 86-101 with our injected config.
    raw = api.getTableauData(ts)
    m = re.search(r"\d+;({.*})\d+;({.*})", raw, re.MULTILINE)
    if not m:
        raise RuntimeError(f"Unexpected bootstrapSession payload:\n{raw[:800]}")
    ts.info = json.loads(m.group(1))
    ts.data = json.loads(m.group(2))

    if "presModelMap" in ts.data["secondaryInfo"]:
        pmm = ts.data["secondaryInfo"]["presModelMap"]
        ts.dataSegments = (pmm["dataDictionary"]["presModelHolder"]
                           ["genDataDictionaryPresModel"]["dataSegments"])
        ts.parameters = utils.getParameterControlInput(ts.info)
    ts.dashboard = ts.info["sheetName"]
    ts.filters = utils.getFiltersForAllWorksheet(
        ts.logger, ts.data, ts.info, rootDashboard=ts.dashboard)

    return ts, ts.getWorkbook()


if __name__ == "__main__":
    ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")
    print("Root dashboard:", ts.dashboard)
    print("sessionid:", ts.tableauData["sessionid"], "vizql_root:", ts.tableauData["vizql_root"])
    print("\nWORKSHEETS:")
    for w in wb.worksheets:
        cols = list(w.data.columns) if w.data is not None else None
        rows = 0 if w.data is None else len(w.data)
        print(f"  - {w.name!r}  rows={rows}  cols={cols}")
    print("\nPARAMETERS:")
    for p in ts.parameters:
        print("  -", {k: p[k] for k in list(p)[:4]})
    print("\nFILTERS (root dashboard):")
    for w in wb.worksheets:
        for f in w.getFilters():
            print(f"  [{w.name}] {f['column']!r} n={len(f['values'])} sample={f['values'][:8]}")
