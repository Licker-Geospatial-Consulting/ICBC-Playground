import glob, os, re
from tableauhyperapi import HyperProcess, Telemetry, Connection

HYPER_DIR = "workbook_extracted/Data/Extracts"
DICT_FILE = os.path.join(HYPER_DIR, "federated_1gb275t0j9zrsp18zw66v0.hyper")

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database=DICT_FILE) as conn:
        print("=== DISTINCT DATASETS in dictionary ===")
        for r in conn.execute_list_query('SELECT DISTINCT "Dataset" FROM "Extract"."Extract"'):
            print("  -", r[0])
        print("\n=== ALL 'Vehicle Population' FIELDS ===")
        rows = conn.execute_list_query(
            'SELECT "Data Field Name","Description" FROM "Extract"."Extract" '
            "WHERE \"Dataset\" = 'Vehicle Population' ORDER BY \"Data Field Name\""
        )
        for name, desc in rows:
            print(f"  - {name}: {str(desc)[:90]}")

# --- inspect the workbook XML ---
twb = glob.glob("workbook_extracted/*.twb")[0]
with open(twb, encoding="utf-8") as f:
    xml = f.read()
print("\n\n=== WORKBOOK XML SUMMARY ===  (", len(xml), "chars )")
print("\nDATASOURCES (name / caption):")
for m in re.finditer(r'<datasource\b([^>]*)>', xml):
    attrs = m.group(1)
    cap = re.search(r'caption=\'([^\']*)\'', attrs)
    name = re.search(r'name=\'([^\']*)\'', attrs)
    print(f"  - name={name.group(1) if name else '?'!r}  caption={cap.group(1) if cap else '?'!r}")

print("\nCONNECTIONS (class / dbname / server):")
for m in re.finditer(r'<connection\b([^>]*)>', xml):
    a = m.group(1)
    cls = re.search(r"class='([^']*)'", a)
    print("  -", cls.group(1) if cls else a[:80])

print("\nWORKSHEETS:")
for m in re.finditer(r"<worksheet name='([^']*)'", xml):
    print("  -", m.group(1))

print("\nDASHBOARDS:")
for m in re.finditer(r"<dashboard name='([^']*)'", xml):
    print("  -", m.group(1))
