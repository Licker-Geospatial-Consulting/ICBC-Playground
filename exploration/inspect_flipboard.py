import json

info = json.load(open("info.json", encoding="utf-8"))
apm = info["worldUpdate"]["applicationPresModel"]
wpm = apm["workbookPresModel"]

# 1) Full sheet inventory
print("=== sheetsInfo (all sheets) ===")
for s in wpm.get("sheetsInfo", []):
    print(f"  name={s.get('sheet')!r:45} dash?={s.get('isDashboard')} "
          f"story?={s.get('isStoryboard')} vis?={s.get('isVisible')} "
          f"windowId={s.get('windowId')}")

# 2) Flipboard / story structure
zones = wpm["dashboardPresModel"]["zones"]
fb = zones["5"]["presModelHolder"].get("flipboard")
print("\n=== flipboard keys ===")
print(list(fb.keys()) if fb else "no flipboard")
if fb:
    for k, v in fb.items():
        if k == "storyPoints":
            print(f"  storyPoints: {len(v)} entries")
            continue
        print(f"  {k} = {json.dumps(v)[:300]}")
    # story point details
    print("\n  --- storyPoints ---")
    for spid, sp in fb.get("storyPoints", {}).items():
        cap = None
        try:
            cap = sp["dashboardPresModel"]["sheetPath"]["sheetName"]
        except Exception:
            pass
        print(f"    id={spid} caption={sp.get('caption')!r} sheetName={cap!r}")

# 3) Is there a storyPointCount / captions elsewhere?
def find_keys(obj, keys, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys:
                print(f"  {path}/{k} = {json.dumps(v)[:200]}")
            find_keys(v, keys, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_keys(v, keys, f"{path}[{i}]")

print("\n=== story count / caption keys ===")
find_keys(info, {"storyPointCount", "storyPointCaptions", "activeStoryPointId",
                 "storyPointId", "flipboardType", "storyPoints"})
