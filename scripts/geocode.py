#!/usr/bin/env python3
"""Look up approximate coordinates (OpenStreetMap Nominatim, falling back to Photon).

Usage: python3 geocode.py --country jp "Kabukiza Tower" "築地場外市場" ...

Prints: query | lat | lng | matched name | source. "NONE" means not found by
either service: try the local-language name, the street address, or the
nearest station, then estimate and mark the place "approx": true.
Always read the matched name: both services happily return a same-named
place in another city. Requests are spaced ~1.2 s apart; Nominatim allows
one per second and blocks bursts.
"""
import json, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "trip-itinerary-skill/1.1 (personal travel planning)"}


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))


def nominatim(q, cc):
    p = {"format": "json", "limit": 1, "q": q}
    if cc:
        p["countrycodes"] = cc
    d = get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(p))
    if d:
        return float(d[0]["lat"]), float(d[0]["lon"]), d[0]["display_name"][:100]


def photon(q, cc):
    d = get("https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": q, "limit": 5}))
    for f in d.get("features", []):
        pr = f["properties"]
        if cc and pr.get("countrycode", "").lower() != cc.lower():
            continue
        lng, lat = f["geometry"]["coordinates"]
        name = ", ".join(str(pr[k]) for k in ["name", "street", "city", "country"] if pr.get(k))
        return lat, lng, name[:100]


args = sys.argv[1:]
cc = None
if "--country" in args:
    i = args.index("--country"); cc = args[i + 1]; del args[i:i + 2]
if not args:
    sys.exit(__doc__)
for q in args:
    hit, src = None, ""
    for fn in (nominatim, photon):
        try:
            hit = fn(q, cc)
        except Exception as e:  # rate limit or network: try the next service
            hit = None
        if hit:
            src = fn.__name__
            break
        time.sleep(1.2)
    print(f"{q} | {hit[0]:.5f} | {hit[1]:.5f} | {hit[2]} | {src}" if hit else f"{q} | NONE")
    time.sleep(1.2)
