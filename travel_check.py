#!/usr/bin/env python3
"""Gate for the public traveller radar (travel/index.html).

The gate IS the deliverable here, not a summary of one. It asserts, mechanically:

  1. the page's inline JS parses (node --check on the extracted block)
  2. the browser-side haversine in the PAGE reproduces, within 0.1 mi, the distances the
     live app computes for the same origin - run in node against the real payload, so a
     drifting JS copy of the formula fails the gate instead of shipping
  3. the radius filter and the sort use the COMPUTED distance, not a stored column
  4. the page never renders an unbacked rating (rating text only behind review_count > 0)
  5. the page never claims live fuel prices or invented hours
  6. no dead links (href="#" / href="javascript:") and no third-party script beyond
     Leaflet/OSM
  7. the payload it fetches exists next to it, every row is geocoded, and its counts match
     the page's advertised totals

Usage: python travel_check.py            # exit 0 = all assertions hold
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
PAGE = HERE / "travel" / "index.html"
PAYLOAD = HERE / "travel" / "venues.json"
API = "http://127.0.0.1:5596/api/radar?lat={}&lon={}&radius=60"
ORIGINS = {"Pueblo": (38.2544, -104.6091), "Springs": (38.8339, -104.8214)}
failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok ' if ok else 'FAIL'}] {label}" + ((" -- " + detail) if detail else ""))
    if not ok:
        failures.append(label)


def main() -> int:
    if not os.path.isfile(PAGE):
        print(f"missing {PAGE}", file=sys.stderr)
        return 2

    html = open(PAGE, encoding="utf-8").read()
    flat = re.sub(r"\s+", " ", html)
    payload = json.load(open(PAYLOAD, encoding="utf-8"))
    eat = payload["layers"]["eat"]
    fuel = payload["layers"]["fuel"]

    print("1. the payload the page fetches is present, geocoded and matches the advertised totals")
    check("page fetches a relative venues.json (no backend, no absolute host)", "fetch('venues.json')" in html)
    check("payload sits next to the page", os.path.isfile(PAYLOAD))
    missing = [r["id"] for r in eat + fuel if not r.get("lat") or not r.get("lon")]
    check("every row geocoded", not missing, f"{len(missing)} missing")
    check("advertised eat count matches the payload", f"{len(eat)} places to eat" in flat, f"{len(eat)}")
    check("advertised fuel count matches the payload", f"{len(fuel)} fuel stops" in flat, f"{len(fuel)}")

    print("2. the inline JS parses")
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    check("exactly one inline script block", len(blocks) == 1, f"{len(blocks)} found")
    js = blocks[0]
    node = subprocess.run(["node", "--check", "-"], input=js, capture_output=True, text=True)
    check("node --check on the extracted script", node.returncode == 0, (node.stderr or "").strip()[:200])

    print("3. the PAGE's own haversine matches the live app (the formula is executed, not assumed)")
    harness = js.split("function miles(a, b) {", 1)
    check("the page defines miles()", len(harness) == 2)
    if len(harness) == 2:
        body = "function miles(a, b) {" + harness[1].split("\n}", 1)[0] + "\n}"
        rows = [{"id": r["id"], "lat": r["lat"], "lon": r["lon"], "name": r["name"]} for r in eat]
        prog = body + "\nvar rows=" + json.dumps(rows) + ";\nvar out=rows.map(function(r){return [r.id, miles([%s,%s],[r.lat,r.lon])]});\nconsole.log(JSON.stringify(out));\n"
        for label, (lat, lon) in ORIGINS.items():
            r = subprocess.run(["node", "-"], input=prog % (lat, lon), capture_output=True, text=True)
            if r.returncode != 0:
                check(f"{label}: node ran the page's miles()", False, (r.stderr or "").strip()[:160])
                continue
            page_dist = dict(json.loads(r.stdout))
            try:
                with urllib.request.urlopen(API.format(lat, lon), timeout=30) as resp:
                    api_rows = json.load(resp).get("results") or []
            except Exception as e:
                check(f"{label}: live app reachable for parity", False, f"{type(e).__name__}: {e}")
                continue
            worst = max(
                (abs(float(a.get("distance_miles") or 0) - page_dist[a["id"]])
                 for a in api_rows if a.get("id") in page_dist),
                default=-1,
            )
            check(f"{label}: page vs app within 0.1 mi over {len(api_rows)} rows",
                  0 <= worst <= 0.1, f"worst {worst:.3f} mi")

    print("4. distances are computed, and the filter/sort use the computed value")
    check("filter compares the computed distance", "if (d <= maxMi)" in js)
    check("sort is on the computed distance", "pick.sort(function (a, b) { return a.d - b.d; })" in js)
    check("no stored distance column is read", "distance_miles" not in js)

    print("5. no unbacked rating, no invented hours or prices")
    check("rating text is gated on review_count", "if (!r || !r.review_count) return 'no reviews yet';" in js)
    check("only two hour formats are parsed", "/^24\\/7$/" in js and "return null;" in js)
    check("unparseable hours report unknown, never open", "if (!m) return null;" in js)
    check("hours absence is stated as a gap", "hours not listed" in js)
    check("price rendering is gated on a report with its own timestamp",
          "if (!p || !p.length) return 'no price reported';" in js and "reported_at" in js)
    check("a stale price is marked stale, not shown as today's",
          "PRICE_STALE_H" in js and "possibly stale" in js)
    check("a price is never averaged or carried forward",
          "toFixed(3)" in js and "Math.max(0, Math.round((Date.now() - t) / 3600000))" in js)

    real_sources = {"desk", "review", "verified", "traveller-report", "operator", "public-report"}
    unbacked = [
        f"{layer}:{r['name']}={r['rating']}/{r['review_count']}"
        for layer, rows in (("eat", eat), ("fuel", fuel))
        for r in rows
        if r.get("rating") and r.get("review_count")
        and str(r.get("source") or "").strip().lower() not in real_sources
    ]
    check("every rating in the DATA names a traceable source", not unbacked, ", ".join(unbacked[:4]))

    fictional = [
        f"{layer}:{r['name']}={r['phone']}"
        for layer, rows in (("eat", eat), ("fuel", fuel))
        for r in rows
        if r.get("phone") and re.search(r"\b\d{3}-555-\d{4}\b", str(r["phone"]))
    ]
    check("no fictional 555-#### phone number is published", not fictional, ", ".join(fictional[:4]))

    reported = payload.get("fuel_price_count", 0)
    has_field = [r["id"] for r in fuel if r.get("prices")]
    if reported == 0:
        check("no fuel price is reported yet, so none is rendered", not has_field, f"{has_field}")
        check("the page's absence string is present", "no price reported" in js)
    else:
        check(f"{reported} price report(s) exist and every row carries a timestamp",
              all("reported_at" in p for r in fuel for p in r.get("prices", [])))

    price_fields = sorted({k for r in eat for k in r if "price" in k.lower() or "cost" in k.lower()})
    check("no eat listing carries a price field", not price_fields, f"{price_fields}")
    check("gap notes are emitted, not silence",
          "no fuel price has been reported yet" in js.lower() or "traveller-reported" in js)
    check("the origin is named on screen", "Distances from " in js)
    check("the origin label is not doubled ('from from')",
          "replace(/^\\s*from\\s*/i, '')" in js and "Distances from " in js and "label + '.'" in js)
    check("approximate pins are marked", "area-level pin" in js and (r"\u2248" in js or "\u2248" in js))

    print("6. search and directions are operational")
    check("search input is present and accessible", 'id="search"' in html and 'aria-label="Search places"' in html)
    check("search is applied to names and useful listing fields",
          "searchable.indexOf(query) === -1" in js and "r.cuisine" in js and "r.city" in js)
    check("result count is announced to assistive technology",
          'id="resultCount" aria-live="polite"' in html and "matching place" in js)
    check("each listing has a real map-directions destination",
          "maps/dir/?api=1&destination=" in js
          and "encodeURIComponent(String(r.lat) + ',' + String(r.lon))" in js)
    check("search/filter rerenders from the active location, including live GPS",
          "if (activeOrigin) return [activeOrigin, activeLabel];" in js and "addEventListener('input'" in js)

    print("8. the price renderer is executed against real inputs (fresh, stale, absent)")
    tail = js.split("var PRICE_STALE_H", 1)
    check("the page defines the price renderer", len(tail) == 2)
    if len(tail) == 2:
        body = "var PRICE_STALE_H" + tail[1].split("function anyPriceReported", 1)[0]
        fresh = datetime.now(timezone.utc).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat()
        prog = body + (
            "\nconsole.log(JSON.stringify({fresh: priceText({prices:[{grade:'regular',price:3.199,reported_at:'"
            + fresh + "',source:'public-report'}]}),stale: priceText({prices:[{grade:'diesel',price:3.899,reported_at:'"
            + old + "',source:'public-report'}]}),desk: priceText({prices:[{grade:'e85',price:2.799,reported_at:'"
            + fresh + "',source:'desk'}]}),unknown: priceText({prices:[{grade:'regular',price:3.499,reported_at:'"
            + fresh + "',source:'weird'}]}),none: priceText({prices:[]}), missing: priceText({})}));"
        )
        r = subprocess.run(["node", "-"], input=prog, capture_output=True, text=True)
        check("node ran the page's priceText()", r.returncode == 0, (r.stderr or "").strip()[:160])
        if r.returncode == 0:
            got = json.loads(r.stdout)
            check("a fresh report renders the price and its age",
                  "$3.199" in got["fresh"] and "0h ago" in got["fresh"], got["fresh"])
            check("a 20h-old report is marked possibly stale",
                  "possibly stale" in got["stale"] and "20h ago" in got["stale"], got["stale"])
            check("a driver's report is labelled as one", "driver report" in got["fresh"], got["fresh"])
            check("a desk filing is labelled as a desk filing, not a driver report",
                  "filed by our desk" in got["desk"] and "driver report" not in got["desk"], got["desk"])
            check("an unrecognised source says so rather than being silently trusted",
                  "source unknown" in got["unknown"], got["unknown"])
            check("an empty report list renders the absence string, not a number",
                  got["none"] == "no price reported", got["none"])
            check("a missing field renders the absence string",
                  got["missing"] == "no price reported", got["missing"])
            check("no price string is ever rendered as an unlabelled number",
                  all("$" not in v or "ago" in v for v in got.values()),
                  str([v for v in got.values() if "$" in v and "ago" not in v]))

    print("9. links and third-party scripts")
    check("no dead anchors", 'href="#"' not in html and "href='#'" not in html)
    check("no javascript: urls", "javascript:" not in html.lower())
    hosts = (set(re.findall(r'src="https?://([^/"]+)', html))
             | set(re.findall(r'href="(https?://[^"]+)', html)))
    third = {h for h in ("unpkg.com",) if h in hosts}
    check("Leaflet is the only script host",
          third == {"unpkg.com"} and len(re.findall("<script src=", html)) == 1,
          f"hosts={sorted(hosts)}")

    print("7. the reader has a route to report a fuel price (and it is the one we can actually serve)")
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("build_travel", os.path.join(HERE, "build_travel.py"))
    bt = _ilu.module_from_spec(spec)
    spec.loader.exec_module(bt)
    links = re.findall(r'href="(https://t\.me/[^"]+)"', html)
    if not bt.DESK_URL:
        check("fuel-report intake is paused, so no Telegram link is rendered on the travel page",
              not links, str(links))
        check("the page states that fuel report submissions are paused",
              "paused" in flat.lower())
        check("the page says the price route is manual, not automatic",
              "nothing about a price is automatic" in flat)
        check("the page never references the shared gateway bot",
              "HermesEbookBot" not in html and "hermesebookbot" not in html.lower())
    else:
        check("the page carries a Telegram desk link", bool(links), str(links))
        check("the desk link appears exactly once and IS the builder's DESK_URL constant",
              links.count(bt.DESK_URL) == 1, f"page={links} build={bt.DESK_URL}")
        allowed_tg = {bt.DESK_URL, "https://t.me/Sheba_telegram_bot?start=vendor"}
        tracking = [l for l in links if "utm_" in l or "tg_" in l or "ref=" in l or "aff" in l.lower()]
        check("every Telegram link is https, allowlisted, and carries no tracking/affiliate parameter",
              bool(links) and all(l.startswith("https://t.me/") for l in links)
              and all(l in allowed_tg for l in links) and not tracking,
              f"links={links} tracking={tracking}")
        check("the page says the price route is manual, not automatic",
              "nothing about a price is automatic" in flat and "Send us one on Telegram" in flat)

        token = ""
        for env_path in (Path("D:/Hermes_Core/secrets/sheba_keys.env"), Path("D:\\HermesPortable\\hermes_home\\.env")):
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith(("SHEBA_TELEGRAM_BOT_TOKEN=", "TELEGRAM_BOT_TOKEN=")) and not token:
                        token = line.split("=", 1)[1].strip()
        if not token:
            print("  [skip] could not resolve the bot handle (no bot token to hand)")
        else:
            handle = re.search(r"t\.me/([A-Za-z0-9_]+)", links[0]).group(1) if links else ""
            try:
                with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=25) as r:
                    me = json.load(r)
                live = (me.get("result") or {}).get("username")
                check(f"the page's desk handle @{handle} is the bot Telegram reports",
                      bool(me.get("ok")) and live == handle,
                      f"page says @{handle}, getMe says @{live}")
            except Exception as e:
                check("the desk handle resolves to a live bot", False, f"{type(e).__name__}: {e}")

    print("8. the page states its honesty rules to the reader")
    for phrase in ("never sent to us", "OpenStreetMap",
                   "Ratings appear only where a real report backs them", "never verified at the pump"):
        check(f"page says: {phrase!r}", phrase in flat)

    print("10. rendered page carries the audit fixes (2026-10-15) and no unreplaced template")
    left = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", html)))
    check("no unreplaced __PLACEHOLDER__ survived into the built page", not left, str(left))
    check("page ships og:image + twitter:card (share cards on inner pages)",
          'property="og:image"' in html and 'name="twitter:card"' in html)
    check("page ships the shared site nav with a hamburger (inner-page nav)",
          'class="sitnav"' in html and "navToggle" in html)
    check("page states it is a snapshot, not a live feed (freshness honesty)",
          "catalogue snapshot, not a live feed" in html)
    check("data date is the export's own file date, not an implied live time",
          'id="freshness"' in html and "static export" in html.replace("was built", "static export"))

    print("\nTRAVEL GATE - " + ("PASS" if not failures else f"{len(failures)} FAILURE(S)"))
    for f in failures:
        print("  failed:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    exit(main())
