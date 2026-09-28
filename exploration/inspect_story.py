import json

info = json.load(open("info.json", encoding="utf-8"))

def walk(obj, path=""):
    """Yield (path, key, value) for dict keys of interest."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v
            yield from walk(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")

# Find storyboard / storyPoints structures
print("=== nodes containing 'storyPoint' or 'storyboard' keys ===")
seen = set()
for path, k, v in walk(info):
    if ("storyPoint" in k.lower() or "storyboard" in k.lower()) and path not in seen:
        seen.add(path)
        if isinstance(v, (list, dict)):
            s = json.dumps(v)[:400]
        else:
            s = repr(v)
        print(f"  {path}/{k} = {s}")

# Find windows (navigable sheets)
print("\n=== windows / sheet navigation ===")
for path, k, v in walk(info):
    if k in ("windowId", "windows", "sheetName", "namedWindows") and isinstance(v, (list, str)):
        print(f"  {path}/{k} -> {json.dumps(v)[:300]}")
