from tableau_client import load_workbook

ts, wb = load_workbook("VehiclePopulationIntroPage", "VehiclePopulationData")
sp = wb.getStoryPoints()
print("storyBoard:", sp.get("storyBoard"))
print("storypoints meta:", [(p.get("storyPointId"), p.get("storyPointCaption")) for p in sp.get("storypoints", [])] if isinstance(sp.get("storypoints"), list) else sp)

for spid in [2, 3, 4, 7]:
    print("\n" + "=" * 70)
    print("STORY POINT", spid)
    try:
        wb2 = wb.goToStoryPoint(storyPointId=spid)
        for w in wb2.getWorksheets():
            cols = list(w.data.columns) if w.data is not None else None
            rows = 0 if w.data is None else len(w.data)
            print(f"  WS {w.name!r}  rows={rows}  cols={cols}")
        # filters visible at this story point
        for w in wb2.getWorksheets():
            for f in w.getFilters():
                print(f"    filter [{w.name}] {f['column']!r} n={len(f['values'])} sample={f['values'][:6]}")
    except Exception as e:
        print("  ERROR:", type(e).__name__, str(e)[:300])
