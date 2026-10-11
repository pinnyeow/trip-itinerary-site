---
name: trip-itinerary-site
description: Build a polished, phone-friendly travel itinerary website (one HTML page) for a city trip, with a map per day showing numbered stops, places grouped by neighbourhood, a reservations tracker with priorities and booking-release countdowns, local prices with home-currency conversion, and a clean Japandi design. Use this whenever someone wants to turn a trip plan, planner spreadsheet, pasted itinerary, PDF, booking emails or a list of restaurants into an itinerary page, site, or shareable plan, or asks to "make our trip into a website", "add maps for each day", "group places by area", "track our reservations", or update an itinerary page built this way, even if they don't say "website".
---

# Trip itinerary site

You produce one self-contained HTML page that a couple or small group uses on their phones before and during a trip. You write the trip as data (`trip.json`), and `scripts/build.py` validates it and renders it through `assets/template.html`. This split matters: hand-written itinerary pages drift. Map pin numbers stop matching the timeline, some prices get a USD amount and others don't, and private booking codes slip onto public links. The build script makes those mistakes impossible or loud.

Read `references/trip-schema.md` before writing `trip.json`. `assets/example-trip.json` is a complete worked example (a fictional couple's five days in Kyoto).

## What a good result looks like

Think like a luxury travel agent who is also a UX designer. The travellers should be able to answer these at a glance:
- **What are we doing today, in what order, and how do we get there?** Each day has a short reason for its shape, transit lines, a map with numbered pins, and a timeline with the same numbers.
- **What do we have to book, and when?** Priority bookings come first, with release dates and a countdown. Must-do places that take no reservations get their own cards with the queue strategy.
- **What's near what?** Every place is grouped by neighbourhood, with travel time from the hotel. Big areas are split into zones.
- **What does it cost in our money?** Prices are in local currency with the home-currency amount next to each.

The design is calm and minimal (Japandi): linen and charcoal, hairline rules, a serif for headings, and dark mode. The template already does this. Don't restyle it unless the user asks; put your effort into the content.

## Workflow

### 1. Read what they gave you, then interview them before planning

First pull everything you can from what the user gave you: pasted planners, PDFs, booking and flight emails, screenshots, earlier messages. That covers dates, the hotel, flights, existing bookings and the wish list.

Then **ask before you plan, every time, even when the request looks complete**. The trip belongs to the travellers. A plan built on your guesses is wrong in exactly the places they care about, and they will notice. Don't start researching or scheduling until you have answers to these:

1. **Hotel.** "Which hotel are you staying at?" Ask even if a hotel is mentioned, to confirm the exact property and branch; every day starts and ends there.
2. **Their list of places.** "Which restaurants, cafés, shops and sights do you want in the plan?" Use their list, not yours. If they've given one, show it back and ask what's missing.
3. **Priorities.** "Which of these are must-happens? I'll build the days around them." Multi-select from their own list, including restaurants that don't take reservations. If they already named a top priority, still ask about the rest.
4. **Bookings.** "Which are already booked (time, party size), and which still need booking?"

Then a short second round if needed: pace (early starts or slow mornings, an afternoon hotel break), who's travelling (first names as they want them shown), dietary needs, budget, home currency, and **"Do you want me to suggest extra places, or stick to your list?"**

Use your structured question tool if you have one (for example AskUserQuestion in Claude Code), up to 4 questions per round, with concrete options drawn from what they gave you plus "Other". Otherwise ask in a plain numbered message and wait for the reply. Never choose priorities yourself. Never pull names or preferences from memory of other conversations.

**Don't add places they didn't ask for** unless they said yes to suggestions. Fill gaps with their wish list, or leave the time open ("free afternoon"). When they do want suggestions, mark each one "suggested" in its note so it's clear what came from them and what came from you.

If you're running without a way to ask (a batch job, or a subagent told not to ask), stop and list the questions rather than inventing answers. Build only if the caller supplied the answers.

Ask where to publish only once the page is built (step 7).

### 2. Verify every place before scheduling it

Itineraries fail on facts, not design. For each restaurant, café, shop and sight, search the web for:
- **Is it still open, and is it the right branch?** Branches close and move; a branch can close weeks before the trip. When the user names a closed branch, find the nearest open one and say so.
- **Opening hours on the actual trip days.** Check weekly closed days, lunch breaks, last orders and holiday closures. A café that opens at noon cannot be a 10:00 stop.
- **How to get in:** reservation platform and link, how far ahead seats release and at what local time, phone-only, walk-in with a queue or numbered tickets, cancellation fees.
- **Price per person, address, nearest station.**

When sources disagree, say so in the place's note ("listed hours vary, check first"). Don't pick one silently. Keep the URLs you used; you'll cite them in your reply.

### 3. Shape the days

- **One area per day**, starting and ending at the hotel, so the travellers never cross the city twice in a day.
- **Anchor on the fixed points first** (priority dinners, timed tickets, queue openings), then fill the gaps with nearby wish-list items in walking order.
- **Check every slot against the place's hours** for that weekday.
- **Build the day around no-reservation priorities:** arrive at opening or get the queue ticket first, then do nearby things while waiting.
- **After a heavy shopping block, add a hotel stop** before dinner.
- **Weekend quirks matter**, such as pedestrian streets and Sunday closures. Put shopping-street days where they help.
- If one stop is far from the rest of the day (an evening dinner across town), keep it in the timeline, add it to `map_skip`, and explain it in `map_note` so the day's map stays readable.
- **Give each day an intro of 1–3 sentences that explains why it's shaped that way.**

### 4. Coordinates

Run `python3 scripts/geocode.py --country <cc> "name" ...`, trying the local-language name and the street address too. Check the matched name, because Nominatim returns same-named places in other cities. Small restaurants often aren't in OpenStreetMap; estimate from the address or the nearest station and set `"approx": true`. Give every place a precise Google Maps `q` (name + branch, or the local-script name). That link is what people tap, so it matters more than pin precision.

### 5. Exchange rate

Search for today's mid-market rate (local units per 1 unit of home currency); XE and Wise publish dated mid-market quotes. Record it in `currency` with its date. Don't use a remembered rate or a quote more than a few days old. Write every price symbol-first (`¥8,800`, `€25`); the page appends the converted amount itself.

### 6. Write trip.json, build, and look at it

```bash
python3 <skill>/scripts/build.py trip.json out/index.html
```

Fix every ERROR. Read the WARNs; privacy warnings almost always mean removing something. Check the printed stop order against your plan.

Then take one look at the page at phone width:
```bash
python3 <skill>/scripts/screenshot.py out/index.html shots/ --light
```
It finds Chrome, Chromium, Edge or Playwright's Chromium on macOS, Linux or Windows and writes viewable slices (`shots/part-1.png` ...). View them. Check that the maps loaded, pins aren't piled on top of each other, and text isn't clipped. Fix what you see, then move on; don't loop. If it exits saying no browser was found, skip the visual check and tell the user.

**Privacy:** the page is often published to a public link. Never include booking confirmation codes, e-ticket numbers, frequent-flyer numbers, card details, passport data, full legal names or email addresses, even if the user pasted them. Flight numbers, first names and the hotel name are fine. Tell the user what you left out and why.

### 7. Publish: ask each time

Once the page is built, offer only the options that actually work in your environment, and ask which one:
- **File only** (always available): leave it in `out/` and give the path. The page is one self-contained HTML file; it can be opened directly, AirDropped or emailed. Maps need an internet connection.
- **Surge** (public link, no login for viewers): offer it only if `surge whoami` succeeds. Run `surge <out-dir> <name>.surge.sh`. Pick a readable but not easily guessed name, e.g. `kyoto-mar27-trip-xx`. Say that anyone with the link can see it.
- **A private page on the user's own platform** (for example a claude.ai artifact in Claude Code, or whatever hosting tool your agent has): offer it only if such a tool is available to you.
- **Another static host the user already uses** (GitHub Pages, Netlify, Vercel): offer it only if its CLI is installed and logged in.

After publishing, fetch the live URL once (`curl -s <url> | grep -o '<title>.*</title>'`) to confirm it's serving.

### 8. Updates later

Edit `trip.json`, rebuild, and redeploy to the same destination.

- **"We booked X":** add it to `reservations.confirmed` (e.g. `"kikunoi": "Sun 14, 17:30, 2 people"`). It shows ticked and locked for everyone. Per-phone ticks never sync, so this is how both phones see the same status.
- **Renaming a Surge domain:** deploy to the new name, verify it, then `surge teardown <old>`. Tell the user the old link is gone.

## Reply to the user

Keep it short and concrete:
- the link or file path
- how the days are shaped, one line per day or a small table
- bookings with dates, in order, highlighting anything bookable now
- **things you couldn't verify, and things you changed from their plan** (a closed branch, a time that clashed with opening hours, a closed day)
- what you left off for privacy
- a "Sources:" list of the URLs you relied on
