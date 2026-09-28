"""
Municipality -> Regional District crosswalk for BC (27 regional districts).

Base list is the incorporated municipalities (from the BC municipalities list),
supplemented with the higher-volume UNINCORPORATED place names that ICBC's
postal-code-derived "Municipality" field also contains. Anything unmatched maps
to "Unassigned" (surfaced separately so RD totals stay honest).
"""
from __future__ import annotations

# incorporated municipality | regional district (short name)
_CROSSWALK_RAW = """
Abbotsford|Fraser Valley
Armstrong|North Okanagan
Burnaby|Metro Vancouver
Campbell River|Strathcona
Castlegar|Central Kootenay
Chilliwack|Fraser Valley
Colwood|Capital
Coquitlam|Metro Vancouver
Courtenay|Comox Valley
Cranbrook|East Kootenay
Dawson Creek|Peace River
Delta|Metro Vancouver
Duncan|Cowichan Valley
Enderby|North Okanagan
Fernie|East Kootenay
Fort St. John|Peace River
Grand Forks|Kootenay Boundary
Greenwood|Kootenay Boundary
Kamloops|Thompson-Nicola
Kelowna|Central Okanagan
Kimberley|East Kootenay
Langford|Capital
Langley|Metro Vancouver
Maple Ridge|Metro Vancouver
Merritt|Thompson-Nicola
Mission|Fraser Valley
Nanaimo|Nanaimo
Nelson|Central Kootenay
New Westminster|Metro Vancouver
North Vancouver|Metro Vancouver
Parksville|Nanaimo
Penticton|Okanagan-Similkameen
Pitt Meadows|Metro Vancouver
Port Alberni|Alberni-Clayoquot
Port Coquitlam|Metro Vancouver
Port Moody|Metro Vancouver
Powell River|qathet
Prince George|Fraser-Fort George
Prince Rupert|North Coast
Quesnel|Cariboo
Revelstoke|Columbia Shuswap
Richmond|Metro Vancouver
Rossland|Kootenay Boundary
Salmon Arm|Columbia Shuswap
Surrey|Metro Vancouver
Terrace|Kitimat-Stikine
Trail|Kootenay Boundary
Vancouver|Metro Vancouver
Vernon|North Okanagan
Victoria|Capital
West Kelowna|Central Okanagan
White Rock|Metro Vancouver
Williams Lake|Cariboo
100 Mile House|Cariboo
Barriere|Thompson-Nicola
Central Saanich|Capital
Chetwynd|Peace River
Clearwater|Thompson-Nicola
Coldstream|North Okanagan
Elkford|East Kootenay
Esquimalt|Capital
Fort St. James|Bulkley-Nechako
Highlands|Capital
Hope|Fraser Valley
Houston|Bulkley-Nechako
Hudson's Hope|Peace River
Invermere|East Kootenay
Kent|Fraser Valley
Kitimat|Kitimat-Stikine
Lake Country|Central Okanagan
Lantzville|Nanaimo
Lillooet|Squamish-Lillooet
Logan Lake|Thompson-Nicola
Mackenzie|Fraser-Fort George
Metchosin|Capital
New Hazelton|Kitimat-Stikine
North Cowichan|Cowichan Valley
North Saanich|Capital
Northern Rockies|Northern Rockies
Oak Bay|Capital
Peachland|Central Okanagan
Port Edward|North Coast
Port Hardy|Mount Waddington
Saanich|Capital
Sechelt|Sunshine Coast
Sicamous|Columbia Shuswap
Sooke|Capital
Spallumcheen|North Okanagan
Sparwood|East Kootenay
Squamish|Squamish-Lillooet
Stewart|Kitimat-Stikine
Summerland|Okanagan-Similkameen
Taylor|Peace River
Tofino|Alberni-Clayoquot
Tumbler Ridge|Peace River
Ucluelet|Alberni-Clayoquot
Vanderhoof|Bulkley-Nechako
Wells|Cariboo
West Vancouver|Metro Vancouver
Bowen Island|Metro Vancouver
Whistler|Squamish-Lillooet
Comox|Comox Valley
Creston|Central Kootenay
Gibsons|Sunshine Coast
Golden|Columbia Shuswap
Ladysmith|Cowichan Valley
Lake Cowichan|Cowichan Valley
Oliver|Okanagan-Similkameen
Osoyoos|Okanagan-Similkameen
Port McNeill|Mount Waddington
Princeton|Okanagan-Similkameen
Qualicum Beach|Nanaimo
Sidney|Capital
Smithers|Bulkley-Nechako
View Royal|Capital
Alert Bay|Mount Waddington
Anmore|Metro Vancouver
Ashcroft|Thompson-Nicola
Belcarra|Metro Vancouver
Burns Lake|Bulkley-Nechako
Cache Creek|Thompson-Nicola
Canal Flats|East Kootenay
Chase|Thompson-Nicola
Clinton|Thompson-Nicola
Cumberland|Comox Valley
Daajing Giids|North Coast
Fraser Lake|Bulkley-Nechako
Fruitvale|Kootenay Boundary
Gold River|Strathcona
Granisle|Bulkley-Nechako
Harrison Hot Springs|Fraser Valley
Hazelton|Kitimat-Stikine
Kaslo|Central Kootenay
Keremeos|Okanagan-Similkameen
Lions Bay|Metro Vancouver
Lumby|North Okanagan
Lytton|Thompson-Nicola
Masset|North Coast
McBride|Fraser-Fort George
Midway|Kootenay Boundary
Montrose|Kootenay Boundary
Nakusp|Central Kootenay
New Denver|Central Kootenay
Pemberton|Squamish-Lillooet
Port Alice|Mount Waddington
Port Clements|North Coast
Pouce Coupe|Peace River
Radium Hot Springs|East Kootenay
Salmo|Central Kootenay
Sayward|Strathcona
Silverton|Central Kootenay
Slocan|Central Kootenay
Tahsis|Strathcona
Telkwa|Bulkley-Nechako
Valemount|Fraser-Fort George
Warfield|Kootenay Boundary
Zeballos|Strathcona
"""

# high-volume unincorporated / gulf-island / locality names in the ICBC data
_SUPPLEMENT = {
    "Salt Spring Island": "Capital",
    "Sunshine Coast": "Sunshine Coast",
    "Gabriola Island": "Nanaimo",
    "Bowser": "Nanaimo",
    "Errington": "Nanaimo",
    "Coombs": "Nanaimo",
    "Fanny Bay": "Comox Valley",
    "Black Creek": "Comox Valley",
    "Merville": "Comox Valley",
    "Cobble Hill": "Cowichan Valley",
    "Shawnigan Lake": "Cowichan Valley",
    "Mill Bay": "Cowichan Valley",
    "Chemainus": "Cowichan Valley",
    "Crofton": "Cowichan Valley",
    "Sun Peaks": "Thompson-Nicola",
    "Sun Peaks Mountain": "Thompson-Nicola",
    "Christina Lake": "Kootenay Boundary",
    "Naramata": "Okanagan-Similkameen",
    "Okanagan Falls": "Okanagan-Similkameen",
    "Kaleden": "Okanagan-Similkameen",
    "Fort Nelson": "Northern Rockies",
    "Sorrento": "Columbia Shuswap",
    "Blind Bay": "Columbia Shuswap",
    "Falkland": "Columbia Shuswap",
    "Malakwa": "Columbia Shuswap",
    "Sicamous": "Columbia Shuswap",
    "Roberts Creek": "Sunshine Coast",
    "Halfmoon Bay": "Sunshine Coast",
    "Madeira Park": "Sunshine Coast",
    "Pender Harbour": "Sunshine Coast",
    "Egmont": "Sunshine Coast",
    "Pender Island": "Capital",
    "Galiano Island": "Capital",
    "Mayne Island": "Capital",
    "Saturna Island": "Capital",
    "Sooke": "Capital",
    "Denman Island": "Comox Valley",
    "Hornby Island": "Comox Valley",
    "Bamfield": "Alberni-Clayoquot",
    "Kaslo": "Central Kootenay",
    "Winlaw": "Central Kootenay",
    "Ymir": "Central Kootenay",
    "Balfour": "Central Kootenay",
    "Genelle": "Kootenay Boundary",
    "Wynndel": "Central Kootenay",
    "Riondel": "Central Kootenay",
    "Sparwood": "East Kootenay",
    "Windermere": "East Kootenay",
    "Fairmont Hot Springs": "East Kootenay",
    "Panorama": "East Kootenay",
    "Field": "Columbia Shuswap",
    "Anahim Lake": "Cariboo",
    "Horsefly": "Cariboo",
    "Lac La Hache": "Cariboo",
    "150 Mile House": "Cariboo",
    "108 Mile Ranch": "Cariboo",
    "Bridge Lake": "Cariboo",
    "Wells": "Cariboo",
    "Likely": "Cariboo",
    "Hixon": "Fraser-Fort George",
    "Dunster": "Fraser-Fort George",
    "Dome Creek": "Fraser-Fort George",
    "Topley": "Bulkley-Nechako",
    "Fraser Lake": "Bulkley-Nechako",
    "Endako": "Bulkley-Nechako",
    "Hagensborg": "Central Coast",
    "Bella Coola": "Central Coast",
    "Bella Bella": "Central Coast",
    "Port Renfrew": "Capital",
    "Jordan River": "Capital",
    "Lake Cowichan": "Cowichan Valley",

    # --- extended: high-volume unincorporated localities & reserves (2nd pass) ---
    # Metro Vancouver electoral areas / treaty & reserve lands
    "Ubc": "Metro Vancouver",
    "Tsawwassen First Nation": "Metro Vancouver",
    "Gambier Island": "Metro Vancouver",
    "Barnston Island": "Metro Vancouver",
    # Fraser Valley
    "Agassiz": "Fraser Valley",
    "Hatzic": "Fraser Valley",
    "Cheam Ir": "Fraser Valley",
    "Deroche": "Fraser Valley",
    "Chilliwack River Valley": "Fraser Valley",
    "Cultus Lake": "Fraser Valley",
    "Boston Bar": "Fraser Valley",
    "Dewdney": "Fraser Valley",
    "Yale": "Fraser Valley",
    "Harrison Mills": "Fraser Valley",
    # Capital
    "East Sooke": "Capital",
    "Otter Point": "Capital",
    "Shirley": "Capital",
    "Willis Point": "Capital",
    # Cowichan Valley
    "Cowichan Bay": "Cowichan Valley",
    "Youbou": "Cowichan Valley",
    "Honeymoon Bay": "Cowichan Valley",
    "Thetis Island": "Cowichan Valley",
    "Koksilah": "Cowichan Valley",
    "Westholme": "Cowichan Valley",
    # Nanaimo
    "Nanoose Bay": "Nanaimo",
    # Comox Valley
    "Royston": "Comox Valley",
    "Union Bay": "Comox Valley",
    # Strathcona
    "Quathiaski Cove": "Strathcona",
    "Marina Island": "Strathcona",
    "Nootka Island": "Strathcona",
    "Cortes Island": "Strathcona",
    # Alberni-Clayoquot
    "Meares Island": "Alberni-Clayoquot",
    "Port Albion": "Alberni-Clayoquot",
    "Ahousaht": "Alberni-Clayoquot",
    "Kildonan": "Alberni-Clayoquot",
    # Thompson-Nicola
    "Coldwater": "Thompson-Nicola",
    "Upper Nicola": "Thompson-Nicola",
    "Lower Nicola": "Thompson-Nicola",
    "Pritchard": "Thompson-Nicola",
    "Savona": "Thompson-Nicola",
    "Knutsford": "Thompson-Nicola",
    "Heffley Lake": "Thompson-Nicola",
    "Heffley Creek": "Thompson-Nicola",
    "Pinantan Lake": "Thompson-Nicola",
    "Louis Creek": "Thompson-Nicola",
    "Tobiano": "Thompson-Nicola",
    "Rivershore": "Thompson-Nicola",
    "Vavenby": "Thompson-Nicola",
    "Barnhartvale": "Thompson-Nicola",
    "Monte Creek": "Thompson-Nicola",
    "Monte Lake": "Thompson-Nicola",
    "Paul Lake": "Thompson-Nicola",
    "Lac Le Jeune": "Thompson-Nicola",
    "Blue River": "Thompson-Nicola",
    "Black Pines": "Thompson-Nicola",
    "Vinsulla": "Thompson-Nicola",
    "Westwold": "Thompson-Nicola",
    "Walhachin": "Thompson-Nicola",
    "Darfield": "Thompson-Nicola",
    "Kamloops Ir No 1": "Thompson-Nicola",
    "Sunshine Valley Tnrd": "Thompson-Nicola",
    "Spences Bridge": "Thompson-Nicola",
    "Dot": "Thompson-Nicola",
    "Coutlee": "Thompson-Nicola",
    "Canford": "Thompson-Nicola",
    "Quilchena": "Thompson-Nicola",
    "Nooaitch": "Thompson-Nicola",
    # Fraser-Fort George
    "Pineview Ffg": "Fraser-Fort George",
    "Pineview": "Fraser-Fort George",
    "Beaverley": "Fraser-Fort George",
    "Chief Lake": "Fraser-Fort George",
    "Ness Lake": "Fraser-Fort George",
    "Salmon Valley": "Fraser-Fort George",
    "Buckhorn": "Fraser-Fort George",
    "Ferndale-tabor": "Fraser-Fort George",
    "Miworth": "Fraser-Fort George",
    "Mud River": "Fraser-Fort George",
    "Red Rock": "Fraser-Fort George",
    "Bear Lake": "Fraser-Fort George",
    "Giscome": "Fraser-Fort George",
    "Mcleod Lake Reserve": "Fraser-Fort George",
    "Upper Fraser": "Fraser-Fort George",
    "Isle Pierre": "Fraser-Fort George",
    "Stoner": "Fraser-Fort George",
    "Cluculz Lake": "Fraser-Fort George",
    "Strathnaver": "Fraser-Fort George",
    "Woodpecker": "Fraser-Fort George",
    "West Lake": "Fraser-Fort George",
    "Crescent Spur": "Fraser-Fort George",
    "Murdale": "Fraser-Fort George",
    # Cariboo
    "Bouchie Lake": "Cariboo",
    "Roe Lake": "Cariboo",
    "Kersley": "Cariboo",
    "Mcleese Lake": "Cariboo",
    "Big Lake Ranch": "Cariboo",
    "Forest Grove": "Cariboo",
    "Riske Creek": "Cariboo",
    "Nazko": "Cariboo",
    "Green Lake": "Cariboo",
    "93 Mile House": "Cariboo",
    "Lone Butte": "Cariboo",
    "Canoe Creek": "Cariboo",
    "Springhouse": "Cariboo",
    "Baker Creek": "Cariboo",
    "Alexandria": "Cariboo",
    "Marguerite": "Cariboo",
    "Soda Creek": "Cariboo",
    "Chimney Lake": "Cariboo",
    "Kleena Kleene": "Cariboo",
    "Tatla Lake": "Cariboo",
    "Nimpo Lake": "Cariboo",
    "Alexis Creek": "Cariboo",
    "Chilanko Forks": "Cariboo",
    "Nemaiah Valley": "Cariboo",
    "Gang Ranch": "Cariboo",
    "Dog Creek": "Cariboo",
    "Moose Heights": "Cariboo",
    "Narcosli Creek": "Cariboo",
    "Cottonwood": "Cariboo",
    "Barkerville": "Cariboo",
    # Central Kootenay
    "Ootischenia": "Central Kootenay",
    "Robson": "Central Kootenay",
    "Blewett": "Central Kootenay",
    "Pass Creek": "Central Kootenay",
    "Raspberry": "Central Kootenay",
    "South Slocan": "Central Kootenay",
    "Slocan Park": "Central Kootenay",
    "Taghum": "Central Kootenay",
    "Thrums": "Central Kootenay",
    "Glade": "Central Kootenay",
    "Crawford Bay": "Central Kootenay",
    "Krestova": "Central Kootenay",
    "Appledale": "Central Kootenay",
    "Fauquier": "Central Kootenay",
    "Burton": "Central Kootenay",
    "Lister": "Central Kootenay",
    "Erickson": "Central Kootenay",
    "Beasley": "Central Kootenay",
    "Harrop": "Central Kootenay",
    "Procter": "Central Kootenay",
    "Sanca": "Central Kootenay",
    "Gray Creek": "Central Kootenay",
    "Queens Bay": "Central Kootenay",
    "Ainsworth Hot Springs": "Central Kootenay",
    "Lardeau": "Central Kootenay",
    "Shoreacres": "Central Kootenay",
    "Tarrys": "Central Kootenay",
    "Sirdar": "Central Kootenay",
    "Kitchener": "Central Kootenay",
    # Kootenay Boundary
    "Rock Creek": "Kootenay Boundary",
    "Rivervale": "Kootenay Boundary",
    # East Kootenay
    "Wasa": "East Kootenay",
    "Jaffray": "East Kootenay",
    "Wycliffe": "East Kootenay",
    "Edgewater": "East Kootenay",
    "Baynes Lake": "East Kootenay",
    "Fort Steele": "East Kootenay",
    "Yahk": "East Kootenay",
    "Grasmere": "East Kootenay",
    "Wardner": "East Kootenay",
    "Athalmer": "East Kootenay",
    "Wilmer": "East Kootenay",
    "Brisco": "East Kootenay",
    "Skookumchuck": "East Kootenay",
    "Galloway": "East Kootenay",
    "Mayook": "East Kootenay",
    "Koocanusa West": "East Kootenay",
    "Roosville": "East Kootenay",
    "Elko": "East Kootenay",
    "Moyie": "East Kootenay",
    # Columbia Shuswap
    "Lee Creek": "Columbia Shuswap",
    "Tappen": "Columbia Shuswap",
    "Scotch Creek": "Columbia Shuswap",
    "Anglemont": "Columbia Shuswap",
    "Magna Bay": "Columbia Shuswap",
    "Eagle Bay": "Columbia Shuswap",
    "East Salmon Arm": "Columbia Shuswap",
    "Blaeberry": "Columbia Shuswap",
    "Celista": "Columbia Shuswap",
    "Falkland": "Columbia Shuswap",
    # North Okanagan
    "Cherryville": "North Okanagan",
    "Grindrod": "North Okanagan",
    "Ashton Creek": "North Okanagan",
    "Grandview Bench": "North Okanagan",
    "Lavington": "North Okanagan",
    "Hupel": "North Okanagan",
    # Central Okanagan
    "North Westside": "Central Okanagan",
    # Okanagan-Similkameen
    "Cawston": "Okanagan-Similkameen",
    "Hedley": "Okanagan-Similkameen",
    "Olalla": "Okanagan-Similkameen",
    "Apex": "Okanagan-Similkameen",
    # Squamish-Lillooet
    "Mount Currie": "Squamish-Lillooet",
    "Britannia Beach": "Squamish-Lillooet",
    "D'arcy": "Squamish-Lillooet",
    "Furry Creek": "Squamish-Lillooet",
    "Seton Portage": "Squamish-Lillooet",
    "Pemberton Meadows": "Squamish-Lillooet",
    "Shalalth": "Squamish-Lillooet",
    "Gold Bridge": "Squamish-Lillooet",
    # Sunshine Coast
    "Granthams Landing": "Sunshine Coast",
    "Langdale": "Sunshine Coast",
    "Garden Bay": "Sunshine Coast",
    # qathet
    "Gillies Bay": "qathet",
    "Lund": "qathet",
    "Van Anda": "qathet",
    "Saltery Bay": "qathet",
    # Bulkley-Nechako
    "Pinchi": "Bulkley-Nechako",
    "Palling": "Bulkley-Nechako",
    "Fort Fraser": "Bulkley-Nechako",
    "Tatalrose": "Bulkley-Nechako",
    "Southbank": "Bulkley-Nechako",
    "Tintagel": "Bulkley-Nechako",
    # Kitimat-Stikine
    "Thornhill": "Kitimat-Stikine",
    "Gitanmaax": "Kitimat-Stikine",
    "Gitanyow": "Kitimat-Stikine",
    "Hagwilget": "Kitimat-Stikine",
    "Kispiox": "Kitimat-Stikine",
    "South Hazelton": "Kitimat-Stikine",
    "Gitsegukla": "Kitimat-Stikine",
    "Cedarvale": "Kitimat-Stikine",
    "Lakelse Lake": "Kitimat-Stikine",
    "Kitsumkaylum Ir": "Kitimat-Stikine",
    "Kitamaat Village": "Kitimat-Stikine",
    "Rosswood": "Kitimat-Stikine",
    "Nass Camp": "Kitimat-Stikine",
    "Gitlaxt'aamiks": "Kitimat-Stikine",
    "Gitwinksihlkw": "Kitimat-Stikine",
    "Laxgalts Ap": "Kitimat-Stikine",
    "Glen Vowell": "Kitimat-Stikine",
    "Gingolx": "Kitimat-Stikine",
    # North Coast (incl. Haida Gwaii)
    "Skidegate": "North Coast",
    "Sandspit": "North Coast",
    "Tlell": "North Coast",
    "Lax Kw'alaams": "North Coast",
    "Dolphin Island": "North Coast",
    "Hartley Bay": "North Coast",
    # Central Coast
    "Ocean Falls": "Central Coast",
    "Wuikinuxv": "Central Coast",
    # Mount Waddington
    "Sointula": "Mount Waddington",
    "Woss": "Mount Waddington",
    "Coal Harbour": "Mount Waddington",
    "Winter Harbour": "Mount Waddington",
    "Quatsino": "Mount Waddington",
    "San Josef": "Mount Waddington",
    "Telegraph Cove": "Mount Waddington",
    "Kingcome Inlet": "Mount Waddington",
    "Gilford Island": "Mount Waddington",
    "Harbledown Island": "Mount Waddington",
    # Peace River
    "Charlie Lake": "Peace River",
    "Baldonnel": "Peace River",
    "Montney": "Peace River",
    "Prespatou": "Peace River",
    "Cecil Lake": "Peace River",
    "Moberly Lake": "Peace River",
    "Doig": "Peace River",
    "Rolla": "Peace River",
    "Arras": "Peace River",
    "Farmington": "Peace River",
    "Goodlow": "Peace River",
    "Progress": "Peace River",
    "Tupper": "Peace River",
    "Sunset Prairie": "Peace River",
    "South Taylor": "Peace River",
    "Two Rivers": "Peace River",
    "Groundbirch": "Peace River",
    "Pink Mountain": "Peace River",
    "Bear Flat": "Peace River",
    "North Pine": "Peace River",
    "Clayhurst": "Peace River",
    "One Island Lake": "Peace River",
    "Attachie": "Peace River",
    # Northern Rockies
    "Fort Nelson": "Northern Rockies",
    "Fort Nelson Ir": "Northern Rockies",
    "Prophet River": "Northern Rockies",
    "Muncho Lake": "Northern Rockies",
    "Liard River": "Northern Rockies",
}

# common abbreviations / aliases (used as extra search terms in the dashboard)
ABBREV = {
    "Metro Vancouver": "MVRD GVRD",
    "Fraser Valley": "FVRD",
    "Capital": "CRD",
    "Cowichan Valley": "CVRD",
    "Comox Valley": "CVRD",
    "Central Okanagan": "RDCO",
    "North Okanagan": "RDNO",
    "Okanagan-Similkameen": "RDOS",
    "Thompson-Nicola": "TNRD",
    "Columbia Shuswap": "CSRD",
    "Central Kootenay": "RDCK",
    "East Kootenay": "RDEK",
    "Kootenay Boundary": "RDKB",
    "Fraser-Fort George": "RDFFG",
    "Bulkley-Nechako": "RDBN",
    "Cariboo": "CCRD",
    "Strathcona": "SRD",
    "Nanaimo": "RDN",
    "Alberni-Clayoquot": "ACRD",
    "Mount Waddington": "RDMW",
    "Sunshine Coast": "SCRD",
    "Squamish-Lillooet": "SLRD",
    "qathet": "qRD",
    "North Coast": "NCRD",
    "Kitimat-Stikine": "RDKS",
    "Peace River": "PRRD",
    "Northern Rockies": "NRRM",
    "Central Coast": "CCRD",
}

UNASSIGNED = "Unassigned"


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def _build_map() -> dict:
    m = {}
    for line in _CROSSWALK_RAW.strip().splitlines():
        if "|" not in line:
            continue
        muni, rd = line.split("|", 1)
        m[_norm(muni)] = rd.strip()
    for muni, rd in _SUPPLEMENT.items():
        m.setdefault(_norm(muni), rd)
    return m


MUNI_TO_RD = _build_map()


def resolve(municipality: str) -> str:
    """Return the regional district short-name for an ICBC municipality string,
    or 'Unassigned' if not recognised."""
    return MUNI_TO_RD.get(_norm(municipality), UNASSIGNED)


def display_name(rd: str) -> str:
    if rd == UNASSIGNED:
        return "Unassigned / other localities"
    return f"{rd} Regional District"
