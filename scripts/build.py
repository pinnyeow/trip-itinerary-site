#!/usr/bin/env python3
"""Build a trip itinerary page from trip.json.

Usage: python3 build.py trip.json out/index.html

Validates the trip data, then injects it into assets/template.html.
Exits non-zero on errors; prints warnings (privacy, missing prices) and a
per-day stop list so you can check numbering against the plan.
"""
import json, re, sys, datetime, html
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
errors, warnings = [], []


def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
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


def report():
    for e in errors:
        print("ERROR:", e)
    for w in warnings:
        print("WARN: ", w)


if __name__ == "__main__":
    main()
