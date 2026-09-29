"""Compose the social link-preview image (Open Graph, 1200x627) for the dashboard:
logo + title + headline figures on the left, a crash-map render on the right.

    python pipeline/build_preview.py --map path/to/crash_map.png

The map render is the crash tab's <canvas> saved as PNG (2000x1240), e.g. with
Metro Vancouver selected: in the browser console run
    copy(document.getElementById("crashMap").toDataURL())
and save the data URL as a file, or right-click the map > Save image as.
Output: assets/og-crashes.png (copied to site/og-image.png by build_app.py --split).
Needs Pillow (pip install pillow) and the Segoe UI fonts that ship with Windows.
"""
import argparse, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa

ASSETS = os.path.join(config.ROOT, "assets")
OUT = os.path.join(ASSETS, "og-crashes.png")
LOGO = os.path.join(ASSETS, "lgeo-logo.png")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

W, H, S = 1200, 627, 2            # drawn at 2x, then downsampled for clean edges
PLANE, INK, INK2, MUTED = "#f4f6f8", "#0e1216", "#51565c", "#8b9096"
ACCENT, TEAL, BORDER = "#2a78d6", "#00474f", "#dde2e7"

# headline figures (province-wide, from the crashes tab)
STATS = [("1.47M", "crashes reported in BC, 2021-2025"),
         ("137k", "intersections and blocks mapped")]
URL = "icbc-lgeo-analysis.pages.dev"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size * S)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width * S or not line:
            line = trial
        else:
            lines.append(line); line = word
    return lines + [line]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="crash map canvas render (PNG)")
    # crop box on the 2000x1240 render: Vancouver to Langley
    ap.add_argument("--crop", default="440,230,1640,1150", help="x0,y0,x1,y1 on the map render")
    args = ap.parse_args()

    img = Image.new("RGB", (W * S, H * S), PLANE)
    d = ImageDraw.Draw(img)

    # ---- map panel (right) ----
    mx, my, mw, mh = 468, 24, 708, 579
    x0, y0, x1, y1 = map(int, args.crop.split(","))
    src = Image.open(args.map).convert("RGB")
    # widen the crop to the panel's aspect ratio around its centre
    cx, cy, ch = (x0 + x1) / 2, (y0 + y1) / 2, y1 - y0
    cw = ch * mw / mh
    crop = src.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2)))
    crop = crop.resize((mw * S, mh * S), Image.LANCZOS)
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, crop.size[0] - 1, crop.size[1] - 1), 18 * S, fill=255)
    img.paste(crop, (mx * S, my * S), mask)
    d.rounded_rectangle((mx * S, my * S, (mx + mw) * S - 1, (my + mh) * S - 1), 18 * S, outline=BORDER, width=2 * S)

    # ---- left column ----
    lx, colw = 48, 390
    logo = Image.open(LOGO).convert("RGBA")
    lh = 92
    logo = logo.resize((round(logo.width * lh / logo.height) * S, lh * S), Image.LANCZOS)
    img.paste(logo, (lx * S, 40 * S), logo)

    y = 176
    d.text((lx * S, y * S), "CRASHES  |  VEHICLES  |  LICENSING", font=font("seguisb.ttf", 14), fill=ACCENT)
    y += 30
    for line in wrap(d, "BC Road Data Explorer", font("segoeuib.ttf", 40), colw):
        d.text((lx * S, y * S), line, font=font("segoeuib.ttf", 40), fill=INK)
        y += 50
    y += 6
    sub = "Where crashes happen across British Columbia, down to the intersection, built from ICBC open data."
    for line in wrap(d, sub, font("segoeui.ttf", 19), colw):
        d.text((lx * S, y * S), line, font=font("segoeui.ttf", 19), fill=INK2)
        y += 27

    # headline figures
    y = 452
    sx = lx
    for big, label in STATS:
        d.text((sx * S, y * S), big, font=font("segoeuib.ttf", 34), fill=ACCENT)
        ly = y + 46
        for line in wrap(d, label, font("segoeui.ttf", 14), 170):
            d.text((sx * S, ly * S), line, font=font("segoeui.ttf", 14), fill=MUTED)
            ly += 19
        sx += 200

    d.text((lx * S, 580 * S), URL, font=font("seguisb.ttf", 16), fill=TEAL)

    img.resize((W, H), Image.LANCZOS).save(OUT, optimize=True)
    print(f"wrote {OUT} ({os.path.getsize(OUT):,} bytes)")


if __name__ == "__main__":
    main()
