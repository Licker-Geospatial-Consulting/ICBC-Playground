"""
Phase 3 - Vehicle segment & length classifier.

Because the ICBC data has ~11,000 distinct model strings and ~570 makes, we do
NOT attempt a per-trim manufacturer spec lookup. Instead we assign every
(Make, Model, Body_Style, Vehicle_Type) row to a vehicle SEGMENT and give that
segment a representative length (metres) drawn from published class averages.

Signals used, in priority order:
  1. ICBC encodes light trucks/SUVs/vans by appending " TRUCK/VAN" to the make
     (e.g. "TOYOTA" vs "TOYOTA TRUCK/VAN"). This cleanly separates the car fleet
     from the SUV/pickup/van fleet.
  2. Model-name keywords identify pickups, vans, and SUV size bands, plus a few
     well-known car nameplates.
  3. Body_Style disambiguates cars (sedan/coupe/hatch/convertible/wagon) and
     flags non-road types (ATV, snowmobile, golf cart, etc.).

The representative length is a proxy: the point of the exercise is to measure the
FLEET-MIX SHIFT over time (sedans -> SUVs/pickups), for which a stable per-segment
length is sufficient. `net_weight` (a measured field in the data) is carried
separately as an independent corroborating size signal.
"""
from __future__ import annotations

import re

# ---- Segment -> representative length (metres) ---------------------------------
# Sources: manufacturer spec sheets / class averages (rounded). Documented in the
# workbook's "Methodology" sheet.
SEGMENT_LENGTH_M: dict[str, float] = {
    # passenger cars
    "Microcar":            3.0,
    "Subcompact car":      4.2,
    "Compact car":         4.5,
    "Midsize car":         4.9,
    "Full-size car":       5.2,
    "Coupe":               4.7,
    "Convertible":         4.5,
    "Sports car":          4.5,
    "Station wagon":       4.8,
    "Luxury/large sedan":  5.2,
    # SUVs / crossovers
    "Subcompact SUV":      4.3,
    "Compact SUV":         4.6,
    "Midsize SUV":         4.9,
    "Full-size SUV":       5.3,
    # trucks & vans
    "Minivan":             5.2,
    "Cargo/passenger van": 5.6,
    "Small pickup":        5.4,
    "Full-size pickup":    5.9,
    "Heavy commercial":    7.5,
    "Limousine":           6.5,
    # non-car road/other
    "Motorcycle":          2.2,
    "ATV/off-road":        2.1,
    "Snowmobile":          2.8,
    "Low-speed/other":     3.0,
    # fallback
    "Unclassified":        4.7,
}

# ---- Body-style groupings (values seen in the ICBC extracts) -------------------
BODY = {
    "sedan": {"Fourdoorsedan", "Twodoorsedan", "Fourdoorhardtop", "Twodoorhardtop"},
    "coupe": {"Twodoorcoupe", "Fourdoorcoupe", "Twodoorfastback", "Fourdoorfastback"},
    "convertible": {"Twodoorconvertible", "Fourdoorconvertible", "Sportconvertible"},
    "hatch": {"Hatchback"},
    "wagon_or_suv": {"Fourdoorstationwagon", "Twodoorstationwagon", "Dualpurpose"},
    "limo": {"Limousinepassenger"},
    "offroad": {"Wheeledatv", "Dunebuggy", "Amphibiousvehicle", "Threewheeled"},
    "snow": {"Snowmobile"},
    "lowspeed": {"Lowspeedvehicle", "Golfcart", "Workutilitypassengervehicle"},
}
_BODY_LOOKUP = {b: grp for grp, bodies in BODY.items() for b in bodies}

# ---- Model-name keyword banks -------------------------------------------------
# Full-size pickups
PICKUP_FULL = [
    "F-150", "F150", "F-250", "F250", "F-350", "F350", "F-450", "F550", "F-550",
    "SILVERADO", "SIERRA", "RAM 1500", "RAM 2500", "RAM 3500", "RAM PICKUP",
    "1500", "2500", "3500", "TUNDRA", "TITAN", "SIERRA", "C/K", "C1500", "K1500",
]
PICKUP_SMALL = [
    "TACOMA", "RANGER", "COLORADO", "CANYON", "FRONTIER", "RIDGELINE", "MAVERICK",
    "SANTA CRUZ", "DAKOTA", "S-10", "S10", "SONOMA", "GLADIATOR",
]
PICKUP_GENERIC = ["PICKUP", " PU", "PU ", "4X4 PU", "CREW CAB", "REG CAB", "EXT CAB", "QUAD CAB"]

VAN_MINI = ["CARAVAN", "TOWN & COUNTRY", "TOWN AND COUNTRY", "ODYSSEY", "SIENNA",
            "PACIFICA", "SEDONA", "CARNIVAL", "QUEST", "VILLAGER", "MONTANA",
            "GRAND CARAVAN", "MAZDA5", "MAZDA 5"]
VAN_CARGO = ["TRANSIT", "SPRINTER", "PROMASTER", "SAVANA", "EXPRESS", "NV200", "NV ",
             "METRIS", "ECONOLINE", "E-150", "E-250", "E-350", "E150", "E250", "E350",
             "CARGO VAN", "VAN"]

SUV_LARGE = ["SUBURBAN", "TAHOE", "YUKON", "EXPEDITION", "SEQUOIA", "ARMADA",
             "NAVIGATOR", "ESCALADE", "LAND CRUISER", "GRAND WAGONEER", "WAGONEER",
             "QX80", "LX ", "LX570", "GX ", "GLS", "GX460", "PATRIOT",
             "DURABLE"]
SUV_MID = ["HIGHLANDER", "PILOT", "PASSPORT", "4RUNNER", "GRAND CHEROKEE", "EXPLORER",
           "TRAVERSE", "ATLAS", "TELLURIDE", "PALISADE", "ASCENT", "SORENTO",
           "SANTA FE", "MURANO", "PATHFINDER", "EDGE", "BLAZER", "ACADIA", "ENVISION",
           "CX-9", "CX-90", "CX9", "MDX", "XC90", "Q7", "X5", "X7", "GLE", "GLC",
           "GRAND HIGHLANDER", "DEFENDER", "DISCOVERY", "MONTERO", "4 RUNNER"]
SUV_COMPACT = ["RAV4", "RAV 4", "CR-V", "CRV", "ROGUE", "ESCAPE", "EQUINOX", "TUCSON",
               "SPORTAGE", "FORESTER", "CX-5", "CX5", "CX-50", "CHEROKEE", "COMPASS",
               "TERRAIN", "OUTBACK", "OUTLANDER", "TIGUAN", "WRANGLER", "BRONCO",
               "X3", "Q5", "GLB", "NX ", "RX ", "UX ", "XT5", "ENVISION", "VENZA",
               "SELTOS", "KONA", "TRAILBLAZER", "ECOSPORT", "HR-V", "HRV", "QASHQAI",
               "KICKS", "CROSSTREK", "BRONCO SPORT", "CX-30", "CX30", "COROLLA CROSS",
               "EDGE", "MOKKA", "ENCORE", "TRAX",
               # EV crossovers/SUVs
               "MODEL Y", "MODEL X", "MACH-E", "MUSTANG MACH", "ID.4", "ID4",
               "IONIQ 5", "IONIQ 6", "EV6", "ARIYA", "SOLTERRA", "BZ4X", "EQB", "EQC",
               "IX ", "Q4", "ENYAQ", "BLAZER EV", "EQUINOX EV"]
SUV_SUB = ["HR-V", "HRV", "C-HR", "CHR", "KONA", "KICKS", "VENUE", "SOUL", "CROSSTREK",
           "CX-3", "CX3", "CX-30", "CX30", "ECOSPORT", "TRAX", "NIRO", "BAYON",
           "Q3", "X1", "GLA", "UX ", "COROLLA CROSS", "SELTOS", "MOKKA"]

CAR_FULL = ["CAMRY", "ACCORD", "MAXIMA", "AVALON", "IMPALA", "TAURUS", "CHARGER",
            "300", "LACROSSE", "ES ", "GS ", "LS ", "A6", "A8", "5 SERIES", "7 SERIES",
            "E-CLASS", "S-CLASS", "CTS", "CT6", "G80", "G90", "PANAMERA", "K5", "STINGER"]
CAR_MID = ["ALTIMA", "SONATA", "OPTIMA", "MALIBU", "FUSION", "LEGACY", "MAZDA6",
           "MAZDA 6", "PASSAT", "TLX", "ILX", "IS ", "A4", "3 SERIES", "C-CLASS",
           "MODEL 3", "MODEL S", "ARTEON", "GENESIS"]
CAR_COMPACT = ["COROLLA", "CIVIC", "ELANTRA", "SENTRA", "FORTE", "MAZDA3", "MAZDA 3",
               "JETTA", "GOLF", "CRUZE", "FOCUS", "IMPREZA", "LANCER", "A3", "1 SERIES",
               "2 SERIES", "PRIUS", "COROLLA IM", "VELOSTER", "GLI"]
CAR_SUB = ["YARIS", "FIT", "RIO", "ACCENT", "VERSA", "SPARK", "FIESTA", "MIRAGE",
           "SONIC", "MICRA", "IQ ", "SMART", "500", "MINI", "A1", "IBIZA", "SWIFT",
           "COOPER", "SOUL"]

SPORTS = ["MUSTANG", "CAMARO", "CORVETTE", "CHALLENGER", "GT-R", "GTR", "SUPRA", "MX-5",
          "MIATA", "BRZ", "GR86", "86", "911", "718", "CAYMAN", "BOXSTER", "Z4",
          "TT ", "M3", "M4", "M5", "AMG GT", "F-TYPE", "GT ", "VIPER"]


def _has(model: str, keywords) -> bool:
    return any(k in model for k in keywords)


def classify(make: str, model: str, body_style: str, vehicle_type: str) -> str:
    """Return a segment name (a key of SEGMENT_LENGTH_M)."""
    make_u = (make or "").upper()
    model_u = (model or "").upper()
    body = body_style or ""
    is_truckvan = "TRUCK/VAN" in make_u
    bgroup = _BODY_LOOKUP.get(body, "")

    # 1) Non-road / special bodies first (unambiguous)
    if bgroup == "offroad":
        return "ATV/off-road"
    if bgroup == "snow":
        return "Snowmobile"
    if bgroup == "lowspeed":
        return "Low-speed/other"
    if bgroup == "limo":
        return "Limousine"

    # 2) Motorcycles: they arrive via the Motorcycles workbook (vehicle_type set
    #    there); guard by keyword too.
    if vehicle_type == "Motorcycle" or "MOTORCYCLE" in make_u:
        return "Motorcycle"

    # 3) Pickups (model keywords win regardless of body encoding)
    if _has(model_u, PICKUP_FULL):
        return "Full-size pickup"
    if _has(model_u, PICKUP_SMALL):
        return "Small pickup"
    if _has(model_u, PICKUP_GENERIC):
        return "Full-size pickup" if _has(model_u, ["2500", "3500", "F-250", "F250", "F-350", "F350"]) else "Small pickup"

    # 4) Vans
    if _has(model_u, VAN_MINI):
        return "Minivan"
    if _has(model_u, VAN_CARGO):
        return "Cargo/passenger van"

    # 5) SUVs by size (keyword bands; large -> mid -> compact -> sub)
    if _has(model_u, SUV_LARGE):
        return "Full-size SUV"
    if _has(model_u, SUV_MID):
        return "Midsize SUV"
    if _has(model_u, SUV_SUB):
        return "Subcompact SUV"
    if _has(model_u, SUV_COMPACT):
        return "Compact SUV"

    # 6) Body-style based car classification
    if bgroup == "convertible":
        return "Convertible"
    if _has(model_u, SPORTS):
        return "Sports car"
    if bgroup == "coupe":
        return "Coupe"
    if bgroup == "hatch":
        # sub/compact hatchbacks
        if _has(model_u, CAR_SUB):
            return "Subcompact car"
        return "Compact car"
    if bgroup == "sedan":
        if _has(model_u, CAR_FULL):
            return "Full-size car"
        if _has(model_u, CAR_MID):
            return "Midsize car"
        if _has(model_u, CAR_SUB):
            return "Subcompact car"
        if _has(model_u, CAR_COMPACT):
            return "Compact car"
        return "Midsize car"  # default sedan
    if bgroup == "wagon_or_suv":
        # ICBC lumps SUVs/crossovers with 4-door station wagons.
        if is_truckvan:
            # A truck/van-classed "station wagon" is almost always an SUV/crossover.
            if _has(model_u, CAR_SUB):
                return "Subcompact SUV"
            return "Compact SUV"
        # car-make station wagon: could be a wagon or a crossover; keep as wagon
        if _has(model_u, CAR_SUB):
            return "Subcompact car"
        return "Station wagon"

    # 7) Anything left classed TRUCK/VAN -> assume compact SUV (dominant modern mix)
    if is_truckvan:
        return "Compact SUV"

    # 8) Heavy commercial fallback for commercial-type leftovers
    if vehicle_type == "Commercial":
        return "Heavy commercial"

    return "Unclassified"


def classify_row(make, model, body_style, vehicle_type):
    seg = classify(make, model, body_style, vehicle_type)
    return seg, SEGMENT_LENGTH_M[seg]


if __name__ == "__main__":
    tests = [
        ("TOYOTA", "COROLLA LE 4DR", "Fourdoorsedan", "Passenger"),
        ("TOYOTA TRUCK/VAN", "RAV4 XLE", "Fourdoorstationwagon", "Passenger"),
        ("FORD TRUCK/VAN", "F-150 XLT", "Fourdoorstationwagon", "Passenger"),
        ("HONDA TRUCK/VAN", "ODYSSEY EX", "Fourdoorstationwagon", "Passenger"),
        ("CHEVROLET TRUCK/VAN", "SUBURBAN LT", "Fourdoorstationwagon", "Passenger"),
        ("TESLA", "MODEL 3", "Fourdoorsedan", "Passenger"),
        ("TESLA", "MODEL Y", "Fourdoorstationwagon", "Passenger"),
        ("BMW", "750IL 4DR", "Fourdoorsedan", "Passenger"),
        ("DODGE/RAM TRUCK/VAN", "RAM 1500", "Fourdoorstationwagon", "Commercial"),
        ("PORSCHE", "911 CARRERA", "Twodoorcoupe", "Passenger"),
    ]
    for mk, mo, bs, vt in tests:
        seg, ln = classify_row(mk, mo, bs, vt)
        print(f"  {mk:22} {mo:22} {bs:22} -> {seg:20} {ln} m")
