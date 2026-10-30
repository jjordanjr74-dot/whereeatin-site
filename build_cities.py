#!/usr/bin/env python3
"""City SEO landing pages — one per corridor city in site_base.CITY_HUBS.

WHY THIS EXISTS
  The site's own home page advertised a 120-mile corridor but only four markets had any presence, and none of the
  outer cities (Fountain, Monument, Castle Rock, Salida, Walsenburg, Trinidad, La Junta) had a page to land on from
  a "food trucks <city>" search. Each hub gets a real, honest page: what the city's food-truck scene is, the known
  gathering spots, which tracked trucks actually serve it, and a link back to the live corridor radar.

HONESTY (the whole point)
  The truck list per city comes from the vendor DB, matched on the hub's local city names OR the hub's primary city
  name appearing in a truck's own name (so "Kona Ice of Canon City & Pueblo" shows on the Cañon City page). A city
  with no matching truck is shown as exactly that — "no tracked trucks based here yet" — never a fabricated roster.
  No city page claims a live location; the radar is the only thing that asserts a current position.

Usage:
  python build_cities.py           # write food-trucks-<slug>-co/index.html for all 11 hubs
  python build_cities.py --check   # report STALE/CURRENT without writing
"""
from __future__ import annotations

import datetime
import html as H
import json
import os
import pathlib
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_site as BS  # reuse data() so a city page and the roster cannot disagree about a truck  # noqa: E402
import site_base  # noqa: E402


def _norm(s: str) -> str:
    """Lowercase, strip accents (Cañon City -> canon city), ASCII-fold for safe token comparison."""
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


def hub_matches(hub: dict, t: dict) -> bool:
    """True when a tracked truck serves this hub city: same city, city in name, or city in service_area."""
    if _norm(t["city"]) in {_norm(c) for c in hub["local_cities"]}:
        return True
    if _norm(hub["city"]) in _norm(t["name"]):
        return True
    area = _norm(t.get("service_area") or "")
    return any(_norm(c) in area for c in hub["local_cities"])


def page(hub: dict, trucks: list[dict], all_hubs: tuple) -> str:
    path = hub["path"]  # e.g. 'food-trucks-pueblo-co/'
    serving = [t for t in trucks if hub_matches(hub, t)]
    n = len(serving)

    if serving:
        rows = "\n".join(
            f'        <li style="padding:12px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;'
            f'flex-wrap:wrap;align-items:center;justify-content:space-between">'
            f'<span><a href="/trucks/{t["slug"]}/"><strong>{H.escape(t["name"])}</strong></a> '
            f'<span class="muted small">{H.escape(t["cuisine"])} &middot; {H.escape(t["city"])}</span></span>'
            + (f'<a class="btn btn-sm btn-ghost" href="tel:{t["phone"]}">{H.escape(t["phone"])}</a>'
               if t["phone"] else '')
            + '</li>'
            for t in serving)
        roster_html = (
            f'    <p class="lead" style="margin:0 0 14px">{n} tracked truck{"" if n == 1 else "s"} '
            f'serve{"s" if n == 1 else ""} {hub["city"]}. Call them directly — no ordering app, no markup.</p>\n'
            f'    <ul style="list-style:none;padding:0;margin:0">\n{rows}\n    </ul>'
        )
    else:
        roster_html = (
            f'    <p class="lead" style="margin:0 0 8px">No tracked trucks are based in {hub["city"]} yet.</p>\n'
            f'    <p class="muted">The live radar covers the whole corridor, so trucks travelling through '
            f'{hub["city"]} still show up when they check in. If you run a truck here, listing is free: message '
            f'<a href="{site_base.desk_link("vendor")}">@Sheba_telegram_bot</a>.</p>'
        )

    spots = "\n".join(f'        <li>{H.escape(s)}</li>' for s in hub["spots"])

    siblings = "".join(
        f'          <li><a href="/{h["path"]}">{h["city"]}</a></li>\n'
        for h in all_hubs if h["slug"] != hub["slug"])

    faq = [
        {"q": f"Do you track food trucks in {hub['city']} in real time?",
         "a": "Only when a truck checks in with us, or confirms it is serving — and that check-in expires after "
              "four hours. Every other truck shows its usual area, never a pretend live position."},
        {"q": f"How much does it cost to list a food truck in {hub['city']}?",
         "a": "Nothing. Listing is free forever and includes the radar pin, menu, phone number and reviews. Optional "
              "paid plans (Professional $15/mo, Premier $35/mo) keep the page current; neither affects ratings."},
        {"q": f"Can I book a food truck for an event in {hub['city']}?",
         "a": f"Yes — message {site_base.desk_link('vendor')} with your headcount and date. A $250 booking deposit "
              "holds the date and is credited to the final bill."},
        {"q": f"Is {hub['city']} covered by the live radar?",
         "a": "Yes. The radar covers Pueblo and the full 120-mile corridor, sorted by distance from you with a call "
              "button on every truck."},
    ]
    faq_json = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq],
    }, ensure_ascii=False)

    jsonld = json.dumps({
        "@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "name": hub["title"], "description": hub["desc"],
             "url": site_base.url(path), "inLanguage": "en-US"},
            {"@type": "Place", "name": f"Food trucks in {hub['city']}, {hub['state']}",
             "address": {"@type": "PostalAddress", "addressLocality": hub["city"],
                         "addressRegion": hub["state"], "addressCountry": "US"}},
        ] + ([{"@type": "ItemList", "name": f"Tracked trucks serving {hub['city']}",
               "numberOfItems": n,
               "itemListElement": [{"@type": "FoodEstablishment", "name": t["name"],
                                    "url": site_base.url(f"trucks/{t['slug']}/")} for t in serving]}]
             if serving else []),
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(hub["title"])}</title>
<meta name="description" content="{H.escape(hub["desc"], quote=True)}">
<link rel="canonical" href="{site_base.url(path)}">
<meta name="theme-color" content="#d81f26">
{site_base.og_block(hub["title"], hub["desc"], path)}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.json">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<style>{site_base.NAV_CSS}</style>
<script type="application/ld+json">{jsonld}</script>
<script type="application/ld+json">{faq_json}</script>
</head>
<body>
<a class="skip" href="#main" style="position:absolute;left:-9999px;top:0;background:#fff;padding:12px;z-index:99"
   onfocus="this.style.left='12px'" onblur="this.style.left='-9999px'">Skip to content</a>
{site_base.nav_block("/" + path)}
<main id="main" class="wrap" style="padding-top:36px">
  <p class="small muted"><a href="/#community-hub">← All cities</a></p>
  <p class="eyebrow">{hub["city"]}, {hub["state"]} · part of the Pueblo + 120-mile corridor</p>
  <h1>{H.escape(hub["h1"])}</h1>
  <p class="lead" style="max-width:72ch">{H.escape(hub["desc"])}</p>

  <section style="margin-top:26px">
    <h2>Known {hub["city"]} gathering spots</h2>
    <ul style="margin:10px 0 0;padding-left:20px">
{spots}
    </ul>
  </section>

  <section style="margin-top:34px">
    <h2>Tracked trucks serving {hub["city"]}</h2>
{roster_html}
  </section>

  <section style="margin-top:34px">
    <div class="banner reveal">
      <div>
        <h2>Hungry in {hub["city"]} right now?</h2>
        <p>Open the live radar — sorted by distance from you, with a call button on every truck.</p>
      </div>
      <div><a class="btn btn-primary" href="/radar/">Open the live radar &rarr;</a></div>
    </div>
  </section>

  <section style="margin-top:34px">
    <h2>Other cities we cover</h2>
    <ul style="columns:2 220px;gap:24px;list-style:none;padding:0;margin:10px 0 0">
{siblings}    </ul>
  </section>
</main>
{site_base.footer_block()}
<script src="/assets/site.js" defer></script>
<script>{site_base.NAV_JS}</script>
</body>
</html>
"""


def build(check: bool = False) -> int:
    d = BS.data()
    trucks = d["trucks"]
    written = stale = 0
    for hub in site_base.CITY_HUBS:
        html = page(hub, trucks, site_base.CITY_HUBS)
        path = pathlib.Path(HERE) / hub["path"] / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        cur = path.read_text(encoding="utf-8") if path.is_file() else ""
        if site_base.same(html, cur):
            continue
        if check:
            stale += 1
            print(f"  STALE {hub['path']}")
            continue
        path.write_text(html, encoding="utf-8")
        written += 1
    if check:
        print(f"{'STALE' if stale else 'CURRENT'} — {stale} city page(s) would change")
        return 1 if stale else 0
    print(f"wrote {written} city page(s) for {len(site_base.CITY_HUBS)} hubs")
    return 0


if __name__ == "__main__":
    raise SystemExit(build(check="--check" in sys.argv))
