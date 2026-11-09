#!/usr/bin/env python3
"""Build a trip itinerary page from trip.json.

Usage: python3 build.py trip.json out/index.html [--check-links]

Validates the trip data, then injects it into assets/template.html.
Exits non-zero on errors; prints warnings (privacy, missing prices, links
that won't open a map) and a per-day stop list so you can check numbering
against the plan.

--check-links also opens every link in the trip (each place's maps_url and
each booking link) and reports any that fail. It needs internet access.
"""
import json, re, sys, datetime, html, urllib.request, urllib.error
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
errors, warnings = [], []


def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    src, out = Path(args[0]), Path(args[1])
    T = json.loads(src.read_text())

    for k in ["title", "dates_text", "base_id", "places", "days"]:
        if k not in T:
            err(f"missing top-level field: {k}")
    if errors:
        report(); sys.exit(1)

    P, areas = T["places"], {a["id"]: a for a in T.get("areas", [])}
    if T["base_id"] not in P:
        err(f"base_id '{T['base_id']}' is not in places")

    for pid, p in P.items():
        for k in ["name", "lat", "lng", "area"]:
            if k not in p:
                err(f"place {pid}: missing {k}")
        if not isinstance(p.get("lat"), (int, float)) or not isinstance(p.get("lng"), (int, float)):
            err(f"place {pid}: lat/lng must be numbers")
        if p.get("area") and p["area"] not in areas:
            err(f"place {pid}: unknown area '{p['area']}'")
        mu = p.get("maps_url")
        if mu is not None and not is_maps_link(mu):
            warn(f"place {pid}: maps_url {mu} isn't a Google Maps link, so tapping the place opens a website instead of a map. "
                 "Put the website in the note and drop maps_url (the page then searches Google Maps by q).")
        if p.get("badge") and len(p["badge"]) > 18:
            warn(f"place {pid}: badge '{p['badge']}' is long; keep badges to a few words (My favourite, On my list, Friends' pick)")
    for a in areas.values():
        for z in a.get("zones", []):
            for pid in z.get("places", []):
                if pid not in P:
                    err(f"area {a['id']} zone '{z.get('name')}': unknown place {pid}")
                elif P[pid].get("area") != a["id"]:
                    err(f"area {a['id']} zone lists {pid}, but that place's area is {P[pid].get('area')}")
        if a.get("zones"):
            zoned = {pid for z in a["zones"] for pid in z["places"]}
            missing = [pid for pid, p in P.items() if p.get("area") == a["id"] and pid not in zoned]
            if missing:
                warn(f"area {a['id']}: places not in any zone (they won't be listed): {missing}")

    prev = None
    for d in T["days"]:
        for k in ["id", "date", "dow", "title"]:
            if k not in d:
                err(f"day {d.get('id','?')}: missing {k}")
        try:
            dt = datetime.date.fromisoformat(d["date"])
            if dt.strftime("%A") != d.get("dow"):
                err(f"day {d['id']}: {d['date']} is a {dt.strftime('%A')}, not {d.get('dow')}")
            if prev and dt <= prev:
                err(f"day {d['id']}: dates must increase")
            prev = dt
        except Exception:
            err(f"day {d.get('id')}: bad date {d.get('date')}")
        if d.get("area") and d["area"] not in areas:
            err(f"day {d['id']}: unknown area '{d['area']}'")
        for it in d.get("items", []):
            if it.get("place") and it["place"] not in P:
                err(f"day {d['id']} item '{it.get('title')}': unknown place {it['place']}")
        for pid in d.get("map_skip", []):
            if pid not in P:
                err(f"day {d['id']} map_skip: unknown place {pid}")

    cards = T.get("cards") or {}
    if cards:
        if not cards.get("lang"):
            warn("cards: add lang (e.g. \"th\", \"ja\", \"ko\") so phones pick the right font for the local text")
        food = cards.get("food")
        if food:
            for i, x in enumerate(food.get("people", [])):
                for k in ["who", "local", "en"]:
                    if not x.get(k):
                        err(f"cards.food.people[{i}]: missing {k}")
            if not food.get("people"):
                err("cards.food: needs at least one entry in people")
        drv = cards.get("driver")
        if drv:
            for k in ["local", "en"]:
                if not drv.get(k):
                    err(f"cards.driver: missing {k}")

    R = T.get("reservations") or {}
    ids = [c.get("id") for k in ["priority", "walkin", "others"] for c in R.get(k, [])]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        err(f"duplicate reservation ids: {sorted(dupes)}")
    for dl in T.get("deadlines", []):
        for i in dl.get("ids", []):
            if i not in ids:
                err(f"deadline '{dl.get('text')}': unknown reservation id {i}")
    for i in (R.get("confirmed") or {}):
        if i not in ids:
            err(f"confirmed: unknown reservation id {i}")

    # Prices need a currency so they get home-currency amounts
    C = T.get("currency")
    raw = json.dumps(T, ensure_ascii=False)
    if C:
        for k in ["symbol", "rate", "home", "home_symbol", "rate_date"]:
            if k not in C:
                err(f"currency: missing {k}")
        if C.get("symbol") and C["symbol"] + " " in raw:
            warn(f"found '{C['symbol']} ' with a space; write prices symbol-first with no space, e.g. {C['symbol']}25")
    elif re.search(r"[¥€£₩฿₫]\s?\d", raw):
        warn("prices found but no currency block, so no home-currency amounts will show")

    # Privacy: this page is often published to a public link
    for pat, what in [
        (r"\b\d{13}\b", "a 13-digit number (looks like an e-ticket number)"),
        (r"(?i)(confirmation|booking ref|record locator|PNR|reservation)\s*(code|number|no\.?|#)?\s*(is|:)?\s*(?-i:[A-Z0-9]{5,8})\b(?=[^a-z]|$)", "a booking confirmation code"),
        (r"(?i)ending in \d{4}", "a payment card"),
        (r"(?i)passport (no|number)", "a passport number"),
        (r"(?i)[\w.+-]+@(gmail|yahoo|outlook|hotmail|icloud|me|live|proton|protonmail|aol)\.", "a personal email address (business contact emails are fine)"),
    ]:
        if re.search(pat, raw):
            warn(f"privacy: trip data contains {what}. Remove it unless the user asked for it on a shareable page.")

    if "--check-links" in sys.argv:
        check_links(T)

    report()
    if errors:
        sys.exit(1)

    # Stop numbering preview (mirrors the template's logic)
    print("\nStops per day (numbers shown on map pins and timeline):")
    for d in T["days"]:
        seen, order = {}, []
        for it in d.get("items", []):
            pid = it.get("place")
            if not pid or pid == T["base_id"] or it.get("nonum"):
                continue
            if pid not in seen:
                seen[pid] = len(seen) + 1
                order.append(f"{seen[pid]} {P[pid]['name']}")
        print(f"  {d['id']} {d['date']}: " + ("; ".join(order) if order else "(no map)"))

    tpl = TEMPLATE.read_text()
    data = json.dumps(T, ensure_ascii=False).replace("</", "<\\/")
    desc = T.get("description") or f"{T['title']} itinerary, {T['dates_text']}"
    page = (tpl.replace("__TITLE__", html.escape(T.get("page_title") or T["title"]))
               .replace("__DESCRIPTION__", html.escape(desc))
               .replace("__TRIP_JSON__", data))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"\nWrote {out} ({len(page)//1024} KB)")


def is_maps_link(u):
    return bool(re.match(r"https?://(maps\.app\.goo\.gl|goo\.gl/maps|maps\.google\.[a-z.]+|(www\.)?google\.[a-z.]+/maps)", u))


def check_links(T):
    """Open each link once. Short Google Maps links must redirect to a map; other links must load."""
    links = [(f"place {pid} maps_url", p["maps_url"]) for pid, p in T["places"].items() if p.get("maps_url")]
    R = T.get("reservations") or {}
    links += [(f"reservations.others {o.get('id')} link", o["link"]) for o in R.get("others", []) if o.get("link")]
    ua = {"User-Agent": "Mozilla/5.0 (trip-itinerary-site link check)"}
    for what, u in links:
        try:
            req = urllib.request.Request(u, headers=ua)
            with urllib.request.urlopen(req, timeout=20) as r:
                final = r.geturl()
            if "maps.app.goo.gl" in u and not is_maps_link(final):
                warn(f"link check: {what} {u} redirected to {final}, not a map")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                warn(f"link check: {what} {u} refused the automated check (HTTP {e.code}); open it once by hand")
            else:
                err(f"link check: {what} {u} is broken (HTTP {e.code})")
        except Exception as e:
            warn(f"link check: couldn't reach {what} {u} ({e.__class__.__name__}); check your connection or open it by hand")
    print(f"Checked {len(links)} links.")


def report():
    for e in errors:
        print("ERROR:", e)
    for w in warnings:
        print("WARN: ", w)


if __name__ == "__main__":
    main()
