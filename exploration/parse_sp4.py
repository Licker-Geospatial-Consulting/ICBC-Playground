import json, re

r = json.load(open("sp4.json", encoding="utf-8"))

def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path, k, v
            yield from walk(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")

# 1) Context around 'Municipality'
print("=== nodes whose key/value mentions Municipality ===")
seen = set()
for path, k, v in walk(r):
    if isinstance(v, str) and "unicipalit" in v.lower():
        key = path[:60]
        if key not in seen:
            seen.add(key)
            print(f"  {path}/{k} = {v[:80]!r}")

# 2) Parameter controls
print("\n=== parameter-ish nodes ===")
for path, k, v in walk(r):
    if isinstance(k, str) and ("aramet" in k or "ropdown" in k or "fieldCaption" in k.lower()):
        if isinstance(v, (str, int, float, bool)):
            print(f"  {path}/{k} = {v}")

# 3) Column/field captions present in the viz (from vizData / presModel)
print("\n=== distinct fieldCaption / valueCaption-ish ===")
caps = set()
for path, k, v in walk(r):
    if k in ("fieldCaption", "caption") and isinstance(v, str):
        caps.add(v)
for c in sorted(caps):
    print("  ", repr(c))

# 4) gen* presModel types present (tells us control types)
print("\n=== gen* presModel component types ===")
gens = set()
for path, k, v in walk(r):
    if isinstance(k, str) and k.startswith("gen") and k.endswith("PresModel"):
        gens.add(k)
for g in sorted(gens):
    print("  ", g)
