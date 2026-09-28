import zipfile
import os

path = "VehiclePopulationIntroPage.twb"
with zipfile.ZipFile(path) as z:
    print("ARCHIVE CONTENTS:")
    for info in z.infolist():
        print(f"  {info.file_size:>12,}  {info.filename}")
    # Extract everything into ./workbook_extracted
    outdir = "workbook_extracted"
    os.makedirs(outdir, exist_ok=True)
    z.extractall(outdir)
    print("\nExtracted to", outdir)
