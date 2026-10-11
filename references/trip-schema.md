# trip.json schema

`scripts/build.py` validates this file and injects it into `assets/template.html`.
The page renders everything from it, so there is no HTML to hand-edit.

Write all text as plain text (no HTML). Write prices symbol-first with no space
(`¥8,800`, `€25`, `₩280,000`, ranges `¥10,000–20,000`); the page appends the
home-currency amount automatically wherever it sees the trip's `currency.symbol`.

## Top level

| Field | Required | Notes |
|---|---|---|
| `title` | yes | City name, e.g. `"Kyoto"` |
| `page_title` | no | Browser tab title; defaults to `title`. Keep it a 2–4 word name, e.g. `"Kyoto, March 2027"` |
| `slug` | no | Short id used for per-phone tick storage |
| `city` | no | Appended to Google Maps searches when a place has no `q` |
| `local_name` | no | Name in the local script (`"京都"`, `"서울"`). Shown vertically on the cover. Omit for Latin-script cities |
| `eyebrow` | no | Small line above the title, e.g. `"Five days · March 2027"` |
| `dates_text` | yes | `"Friday 12 — Tuesday 16 March"` |
| `description` | no | Meta description |
| `facts` | no | Cover grid, two columns. Keep **Arrive and Depart adjacent** so they sit on one row. `[{label, value, detail?, wide?}]`. Usual set: Travellers, Base, Arrive, Depart, Currency (`wide: true`) |
| `base_id` | yes | Place id of the hotel. Shown as the "H" pin; every day route starts and ends there |
| `currency` | if prices | `{code, name, symbol, rate, home, home_symbol, rate_date}`. `rate` = local units per 1 home unit (e.g. 156 for JPY per USD). Look the rate up on the day you build |
| `week_title`, `week_intro` | no | Heading and line for the week overview |
| `where_title` | no | Heading for the area guide |
| `areas` | yes | See below |
| `places` | yes | Object keyed by place id. See below |
| `reservations` | no | See below |
| `deadlines` | no | Drives the countdown line on the cover |
| `days` | yes | See below |
| `notes` | no | `[{title, text}]` practical notes |

## areas

```json
{"id": "central", "name": "Downtown Kyoto", "short": "Downtown", "local": "中京",
 "far": "Home base · on foot", "color": "#6b655c",
 "desc": "Where you sleep. Nishiki and the covered arcades to the south, Pontochō along the river to the east.",
 "zones": [{"name": "By the hotel", "places": ["hotel", "ippodo"]},
           {"name": "Shijō and the river", "places": ["nishiki", "weekenders", "pontocho"]}]}
```

- `far`: travel time and line from the base. This is what "what's where" means to a traveller.
- `color`: muted, earthy, and visible on both light and dark backgrounds (avoid near-black and near-white). Good set: `#6b655c #9a7a52 #76846f #a8664f #6f7f8f #8a6f7d #8b8a5c #5f8580 #9a8aa8 #7b6f86 #7d6f5c`.
- `zones` (optional): use when an area has more than ~8 places. Every place in the area must be listed in some zone or it won't appear.
- `map_label: false` hides the label on the overview map, which helps when two small areas overlap.

## places

```json
"weekenders": {"name": "Weekenders Coffee Tominokoji", "area": "central", "type": "Coffee",
  "lat": 35.0046, "lng": 135.7652, "q": "Weekenders Coffee Tominokoji Kyoto",
  "note": "Tominokoji Rokkaku · opens 7:30 · closed Wednesdays · mostly standing", "approx": true}
```

- `type`: one of `Stay Dine Coffee Tea Drinks Sweet Shop See Do`. The area guide sorts by this order.
- `q`: the Google Maps search string. Include the branch or neighbourhood so the right location opens. The local-language name often works best for small shops.
- `note`: address · the one thing to know (hours, cash only, line, reservation).
- `approx`: true when the coordinates are estimated rather than geocoded.

## days

```json
{"id": "d14", "date": "2027-03-14", "dow": "Sunday", "area": "arashiyama",
 "label": "Arashiyama → Higashiyama", "headline": "Bamboo, then Kikunoi",
 "summary": "Bamboo Grove · Tenryū-ji · Ōkōchi Sansō · Kikunoi Honten",
 "title": "Bamboo at opening, kaiseki at night",
 "intro": "Why the day is shaped this way, in 1–3 sentences.",
 "lines": [{"name": "JR Sagano Line to Saga-Arashiyama, 15 min", "color": "#5f8580"}],
 "map_skip": ["kikunoi"], "map_note": "Map shows Arashiyama. Dinner is across town in Higashiyama.",
 "items": [
   {"time": "07:30", "title": "Arashiyama Bamboo Grove", "place": "bamboo", "text": "...", "res": "priority", "badge": "Must-happen"},
   {"time": "13:00", "title": "Hotel", "place": "hotel", "text": "Rest before dinner."},
   {"time": "17:00", "title": "Taxi to Higashiyama", "text": "About 15 minutes."},
   {"time": "17:30", "title": "Kikunoi Honten", "place": "kikunoi", "res": "priority", "badge": "Priority"}
 ]}
```

- `dow` must match `date`; the build checks it.
- Stops are numbered automatically, in item order, the first time each non-hotel `place` appears. The same numbers appear on the map pins and the timeline, so never type numbers into titles.
- Items without `place` (transit, "check out") have no number and no pin.
- `res`: `"priority"` (clay badge, highlighted row) or `"reserve"` (oak badge, highlighted row). Use for bookings and must-do walk-ins.
- `nonum: true` keeps a place on the route without a number (rare).
- `map_skip`: places still drawn but left out of the zoom, for one far-off stop (an evening dinner across town) that would otherwise shrink the day's cluster into a pile of overlapping pins. Explain it in `map_note`.
- `lines`: transit lines used that day, with the line's real colour where it has one.
- Arrival and departure days usually have only transit items, so no map renders. That's expected.

## reservations

```json
{"title": "One table matters most",
 "intro": "Everything else is walk-in. Booking times are local time.",
 "priority": [{"id": "kikunoi", "tag": "Priority · Sun 14", "time": "17:30", "title": "Kikunoi Honten",
   "meta": "Kaiseki · from ¥22,000 pp plus service · Higashiyama. Closed 1st and 3rd Tuesdays.", "opens": "Request via MY CONCIERGE or TABLEALL"}],
 "walkin": [{"id": "fushimi-w", "tag": "Priority · Sat 13", "time": "Gate ~05:50", "title": "Fushimi Inari at sunrise",
   "meta": "No tickets, open all night. Taxi from the hotel at 05:30."}],
 "prep_title": "This week",
 "prep": ["Check the booking platforms for Sun 14 March, 2 people.", "Decide which course you want before you book."],
 "others": [{"id": "haruka", "title": "Haruka Express · Fri 12 in, Tue 16 out", "when": "Any time · JR West online",
   "desc": "About 75 min. ¥3,600 each way per person.", "link": "https://..."}],
 "costs": [{"label": "Kikunoi Honten", "pp": 44000}],
 "party": 2,
 "confirmed": {"kikunoi": "Sun 14, 17:30, 2 people"}}
```

- `priority` and `walkin` cards with an `opens` line get a tick box. Walk-in cards usually omit `opens`.
- `confirmed`: bookings the user has told you are made. They render ticked and locked for everyone. Per-phone ticks cover the rest.
- `costs.pp`: a number in local currency, per person. The table shows per person and for the party, each with the home-currency amount.

## deadlines

```json
[{"ids": ["kikunoi"], "date": "2026-12-01", "text": "Request Kikunoi for Sun 14 March, 2 people."},
 {"ids": ["kikunoi"], "date": "2027-02-12", "text": "One month out. If Kikunoi isn't confirmed, phone or ask the concierge."},
 {"ids": [], "date": "2027-03-11", "text": "Flights out."}]
```

The cover shows the first deadline whose ids aren't all ticked: "N days · text", or "Now" once the date has passed. End with an id-less entry for departure day.
