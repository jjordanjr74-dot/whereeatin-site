#!/usr/bin/env python3
"""Generate the public home page — professional, honest, and built from the database, never typed.

Every number on the page comes from `vendors_row.db` or `reviews.summary()`:
truck count, city count, menu-item count, ratings and badge state. Nothing is invented, and any
figure the venture cannot yet back (reviews, orders) is shown as what it is.

Usage: python build_site.py [--check]
"""
from __future__ import annotations

import datetime
import html as H
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(VR, "vendors_row"))
import reviews as R  # noqa: E402  the rating rules and badge thresholds
import checkin_state as CS  # noqa: E402  live = fresh vendor check-in or vendor-confirmed serving only
import prices as P   # noqa: E402  menu-price confirmation state

DB = os.path.join(VR, "vendors_row", "vendors_row.db")
MARKETS = ("Pueblo West", "Colorado Springs", "Cañon City", "Pueblo")
OUT = os.path.join(HERE, "index.html")
# the public base URL lives in ONE place (site_base.py): four builders used to carry their own copy of the
# temporary github.io address, which put the wrong URL in canonical/og/sitemap and got regenerated on every run
import site_base  # noqa: E402

BASE = site_base.BASE
DESK = "/list-your-truck/"  # the listing page still exists; intake now routes through the desk bot below
REVIEW_DESK = "/reviews/"
DESK_BOT_LINK = site_base.desk_link("vendor")
REVIEW_BOT_LINK = site_base.desk_link("review")

# photo per truck, chosen by what the kitchen actually makes (files are CC-licensed, credited in the footer)
PHOTO = {
    "burger": "burger-1.jpg", "bbq": "bbq-1.jpg", "taco": "tacos-1.jpg",
    "mexican": "tacos-2.jpg", "ice cream": "icecream-1.jpg", "shaved": "ice-2.jpg",
    "seafood": "seafood-1.jpg", "cupcake": "cupcake-1.jpg", "bakery": "cupcake-1.jpg",
    "caribbean": "truck-1.jpg", "texas": "truck-2.jpg", "pizza": "seafood-2.jpg",
}


def photo_for(category: str, used: dict) -> str:
    low = (category or "").lower()
    for key, f in PHOTO.items():
        if key in low and used.get(f, 0) < 2:
            used[f] = used.get(f, 0) + 1
            return f
    for f in ("truck-1.jpg", "truck-2.jpg", "hero-2.jpg"):
        if used.get(f, 0) < 2:
            used[f] = used.get(f, 0) + 1
            return f
    return "hero-2.jpg"


def data() -> dict:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    # a fresh install may not have the service_area column yet; never crash the site builder over it
    cols = [c[1] for c in con.execute("PRAGMA table_info(vendors)")]
    if "service_area" not in cols:
        con.execute("ALTER TABLE vendors ADD COLUMN service_area TEXT")
    sys.path.insert(0, os.path.join(os.path.dirname(DB)))
    import vendor_tiers as VT          # the entitlement layer: paid tiers must actually do something
    VT.ensure_schema(con)
    ratings = {x["id"]: x for x in R.summary()}
    price_state = {x["id"]: x for x in P.vendor_summary()}
    used: dict = {}
    trucks = []
    markets: set[str] = set()
    for v in con.execute("select id,name,category,city,phone,current_location,specialty_summary,"
                         "location_updated_at,service_area,listing_tier,location_source,serving_status,"
                         "status_updated_at,checkin_lat,checkin_lon,base_lat,base_lon,lat,lon from vendors order by name"):
        served = f"{v['city'] or ''} {v['service_area'] or ''}"
        for m in MARKETS:
            if m.lower() in served.lower():
                markets.add(m)
        items = [dict(m) for m in con.execute("select * from menu_items where vendor_id=? limit 5", (v["id"],))]
        rt = ratings.get(v["id"], {"average": 0, "count": 0, "highly_recommended": False})
        # LIVE means: a fresh vendor check-in, or a fresh vendor-confirmed serving status. Nothing else.
        # A stored location_updated_at alone is NOT live - it may be days old (that was the old lie).
        state = CS.public_state(dict(v))
        checked_in = state["location_label"] == "vendor check-in"
        trucks.append({
            "id": v["id"], "name": v["name"], "slug": site_base.slug(v["name"]),
            "cuisine": v["category"] or "", "city": v["city"] or "",
            "service_area": v["service_area"] or "",
            "phone": v["phone"] or "", "area": v["current_location"] or "",
            "blurb": (v["specialty_summary"] or "")[:190],
            "photo": photo_for(v["category"] or "", used),
            "items": len(items),
            "reported": v["location_updated_at"] if checked_in else None,
            "checked_in": checked_in, "serving": state["serving"],
            "checkin_age": state["location_age_minutes"],
            "live": checked_in or state["serving"],
            "rating": rt["average"], "reviews": rt["count"], "badge": rt["highly_recommended"],
            "price_state": (price_state.get(v["id"]) or {}).get("state", "prices unconfirmed"),
            "confirmed": (price_state.get(v["id"]) or {}).get("confirmed", 0),
            "tier": VT.normalize(v["listing_tier"]),
        })
    # Premier leads the roster, then Professional — this is what the $35 and $15 tiers pay for.
    trucks = VT.order_by_tier(trucks, key="tier")
    con.close()
    cities = sorted(markets, key=lambda m: -sum(1 for t in trucks if m.lower() in f"{t['city']} {t['area']}".lower()))
    return {"trucks": trucks, "cities": cities,
            "live_count": sum(1 for t in trucks if t["live"]),
            "menu_items": sum(t["items"] for t in trucks),
            "confirmed_prices": sum(t["confirmed"] for t in trucks),
            "reviews": sum(t["reviews"] for t in trucks),
            "badged": sum(1 for t in trucks if t["badge"]),
            "built": datetime.date.today().isoformat(),
            "built_human": datetime.date.today().strftime("%d %b %Y")}


def stars(avg: float) -> str:
    full = int(round(avg))
    return "★" * full + "☆" * (5 - full)


def live_pin(t: dict) -> str:
    """Only a fresh check-in or fresh vendor-confirmed serving gets the live pin. Everything else: usual area."""
    if not t["live"]:
        return '<span class="pin">usual area</span>'
    bits = []
    if t["serving"]:
        bits.append("serving now")
    if t["checked_in"]:
        age = t.get("checkin_age")
        bits.append(f"checked in {age} min ago" if age is not None else "checked in")
    return f'<span class="pin pin-live"><span class="dot" style="width:6px;height:6px"></span>{" · ".join(bits)}</span>'


def truck_card(t: dict) -> str:
    loc_pin = live_pin(t)
    badge = ('<span class="pin pin-badge-earned">HIGHLY RECOMMENDED</span>' if t["badge"] else "")
    # paid placement is labelled as paid placement — never dressed up as an earned badge
    tier_pin = {"premier": '<span class="pin pin-tier">PREMIER</span>',
                "professional": '<span class="pin pin-tier">PROFESSIONAL</span>'}.get(t.get("tier", "free"), "")
    card_cls = "vendor reveal" + (" vendor-premier" if t.get("tier") == "premier" else "")
    if t["reviews"]:
        rating = (f'<span class="stars">{stars(t["rating"])}</span> <strong>{t["rating"]:.1f}</strong> '
                  f'<span class="muted small">({t["reviews"]} review{"" if t["reviews"] == 1 else "s"})</span>')
    else:
        rating = '<span class="none">New listing · no reviews yet</span>'
    tel = t["phone"].replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
    call = (f'<a class="btn btn-primary btn-sm" href="tel:{tel}">Call {H.escape(t["phone"])}</a>' if t["phone"] else "")
    area_line = (f"Checked in · {H.escape(t['area'])}" if t["live"] else f"Usually around {H.escape(t['area'])}")
    return f"""      <article class="{card_cls}" data-slug="{t['slug']}">
        <div class="vendor-media">
          <img src="assets/{t['photo']}" alt="{H.escape(t['name'])} — {H.escape(t['cuisine'])}" loading="lazy" width="1024" height="640">
          <div class="vendor-pins">{loc_pin}{tier_pin}{badge}</div>
        </div>
        <div class="vendor-body">
          <h3><a href="trucks/{t['slug']}/">{H.escape(t['name'])}</a></h3>
          <p class="vendor-meta">{H.escape(t['cuisine'])} · {H.escape(t['city'])}</p>
          <p class="small muted" style="margin:0">{area_line}</p>
          <p class="rating">{rating}</p>
          <p class="small muted" style="margin:0">Menu: {t['items']} item{'s' if t['items'] != 1 else ''} · {H.escape(t['price_state'])}</p>
          <div class="vendor-foot">
            {call}
            {site_base.fav_button(t['slug'], t['name'])}
            <a class="btn btn-sm btn-ghost" href="radar/">Radar</a>
          </div>
        </div>
      </article>"""


def review_block(d: dict) -> str:
    if not d["reviews"]:
        return f"""      <div class="rule reveal">
        <p style="margin:0 0 8px"><strong>Nothing here is seeded, bought, or written by us — which is why this
        page now says zero.</strong> The first review comes from a real customer message.</p>
        <p style="margin:0" class="small"><strong>Earned, never sold:</strong> HIGHLY RECOMMENDED needs at least
        {R.MIN_REVIEWS} reviews, an average of {R.MIN_AVG}+ and no review below 3 stars in the last
        {R.BADGE_WINDOW_DAYS} days. It is recalculated on every review, so it can be lost. One review per truck per
        {R.COOLDOWN_HOURS} hours per person; only a first name and last initial are stored.</p>
      </div>
      <div class="review reveal">
        <q>Reviews are the whole point of a food truck. If I can't see who's worth the walk, I'm guessing.</q>
        <cite>— our position at Where We Eatin', stated plainly</cite>
      </div>"""
    top = sorted([t for t in d["trucks"] if t["reviews"]], key=lambda x: (-x["rating"], -x["reviews"]))[:4]
    cards = "".join(f"""      <div class="review reveal">
        <q>{H.escape(t['name'])} — {t['rating']:.1f} from {t['reviews']} review{'' if t['reviews'] == 1 else 's'}</q>
        <cite>{'HIGHLY RECOMMENDED' if t['badge'] else 'rated by real customers'}</cite>
      </div>""" for t in top)
    return cards


def squadpoll_block(d: dict) -> str:
    """The group-dinner poll. Checklist is generated from the live roster, never hand-typed, so a truck added
    to the DB appears on the ballot without an HTML edit. assets/share.js owns the vote/share mechanics."""
    opts = "".join(
        '          <label style="display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer">'
        f'<input type="checkbox" name="truck_opt" value="{H.escape(t["name"], quote=True)}"'
        f'{" checked" if i < 2 else ""}> {H.escape(t["name"])} &middot; {H.escape(t["cuisine"])}</label>\n'
        for i, t in enumerate(d["trucks"]))
    return f"""  <section class="sec" id="squadpoll" style="background:var(--paper-2);border-top:1px solid var(--line);border-bottom:1px solid var(--line)">
    <div class="wrap">
      <p class="eyebrow">End the &quot;I don&apos;t care, where do you want to go?&quot; debate</p>
      <h2>Where We Eatin&apos; Tonight? — Squad Vote</h2>
      <p class="lead" style="margin-bottom:20px">Pick 2 to 4 food trucks from the roster, generate an instant poll link, and text it to family, coworkers, or friends. Everyone taps their vote; the winner gets picked in seconds.</p>

      <div id="activePollBanner" hidden style="background:var(--paper);border:2px solid var(--brand);border-radius:12px;padding:20px;margin-bottom:24px;box-shadow:0 8px 24px rgba(0,0,0,0.06)">
        <p class="eyebrow" style="color:var(--brand);margin-bottom:6px">SQUAD POLL ACTIVE</p>
        <h3 id="pollQuestion" style="margin:0 0 12px">Cast your vote for dinner:</h3>
        <div id="pollCandidates" style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px"></div>
        <p id="pollStatus" class="small muted" style="margin:0">Tap your choice to cast your vote. Instant results calculate live in your browser.</p>
      </div>

      <div class="poll-builder" style="background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:24px">
        <h3 style="margin-top:0;margin-bottom:12px">Create a group dinner poll:</h3>
        <p class="small muted" style="margin-bottom:16px">Select 2 to 4 trucks to put on the ballot:</p>
        <div id="pollTruckChecklist" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(220px, 1fr));gap:10px;margin-bottom:20px">
{opts}        </div>
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center">
          <button type="button" id="btnShareSquadPoll" class="btn btn-primary" style="padding:12px 20px;font-weight:700">Share Poll with Friends</button>
          <button type="button" id="btnSmsSquadPoll" class="btn btn-ghost" style="padding:12px 18px">Text to Group (SMS)</button>
          <button type="button" id="btnCopySquadPoll" class="btn btn-ghost" style="padding:12px 18px">Copy Link</button>
          <span id="pollShareFeedback" class="small muted" style="margin-left:8px"></span>
        </div>
      </div>
    </div>
  </section>"""


def community_hub_block() -> str:
    """City SEO hub: one link per corridor city, generated from site_base.CITY_HUBS so the landing pages,
    this hub, and sitemap.xml can never drift out of sync."""
    cards = "".join(
        f'        <li><a href="{h["path"]}">{h["city"]}</a>'
        + (f' <span class="small muted">{h["distance_miles"]} mi from Pueblo</span>' if h["distance_miles"] else ' <span class="small muted">home base</span>')
        + "</li>\n"
        for h in site_base.CITY_HUBS)
    return f"""  <section class="sec tight" id="community-hub" style="background:var(--paper)">
    <div class="wrap">
      <p class="eyebrow">Pueblo + the 120-mile corridor</p>
      <h2>Food trucks across Southern Colorado</h2>
      <p class="lead" style="margin-bottom:20px">A dedicated radar and directory page for every city we serve — from Pueblo to Colorado Springs, Castle Rock, Salida, Trinidad and La Junta.</p>
      <ul style="columns:2 240px;gap:28px;list-style:none;padding:0;margin:0;font-size:1.05rem">
{cards}      </ul>
    </div>
  </section>"""


def build() -> str:
    d = data()
    n = len(d["trucks"])
    trucks = "\n".join(truck_card(t) for t in d["trucks"])
    city_list = ", ".join(d["cities"][:-1]) + " and " + d["cities"][-1] if len(d["cities"]) > 1 else d["cities"][0]
    city_links = "\n".join(f'          <li><a href="{h["path"]}">{h["city"]}</a></li>' for h in site_base.CITY_HUBS)
    live_line = site_base.live_sentence(d["live_count"])
    title = "Where We Eatin'? — find Southern Colorado food trucks"
    desc = (f"Track {n} food trucks across {city_list}: see who has checked in, how to call them and what they cook. "
            "Free listings, 0% delivery markup.")
    item_list = [{"@type": "FoodEstablishment", "name": t["name"], "servesCuisine": t["cuisine"],
                  "address": {"@type": "PostalAddress", "addressLocality": t["city"], "addressRegion": "CO",
                              "addressCountry": "US"},
                  "telephone": t["phone"],
                  **({"aggregateRating": {"@type": "AggregateRating", "ratingValue": t["rating"],
                                          "reviewCount": t["reviews"], "bestRating": 5}} if t["reviews"] else {})}
                 for t in d["trucks"]]
    og = site_base.og_block(title, desc, "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)}</title>
<meta name="description" content="{H.escape(desc, quote=True)}">
<link rel="canonical" href="{site_base.url('/')}">
<meta name="theme-color" content="#d81f26">
{og}
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/assets/icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<!-- WebMCP: machine-readable typed tools (static manifest + embedded public roster). -->
<link rel="modelcontext" href="/api/tools.json">
<script src="assets/webmcp.js" defer></script>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Where We Eatin">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
<style>{site_base.NAV_CSS}</style>
<script type="application/ld+json">
{{"@context":"https://schema.org","@graph":[
 {{"@type":"WebSite","name":"Where We Eatin'?","url":"{site_base.url('/')}","inLanguage":"en-US",
   "description":"Independent food-truck directory for Southern Colorado."}},
 {{"@type":"ItemList","name":"Tracked food trucks","numberOfItems":{n},
   "itemListElement":{json.dumps(item_list)}}}]}}
</script>
</head>
<body>
<a class="skip" href="#main" style="position:absolute;left:-9999px;top:0;background:#fff;padding:12px;z-index:99"
   onfocus="this.style.left='12px'" onblur="this.style.left='-9999px'">Skip to content</a>

{site_base.nav_block("/")}

<main id="main">
  <section class="hero">
    <div class="wrap hero-grid">
      <div>
        <p class="eyebrow">Southern Colorado · {n} trucks tracked</p>
        <h1>Find the truck<br>before you're <em>hungry.</em></h1>
        <p class="lead">See which trucks have checked in right now, how far they are from you, what they cook and how to
        call them — on a map, not a guess. Free for every truck, and we take <strong>0%</strong> of what you spend
        with them.</p>
        <div class="hero-cta">
          <a class="btn btn-primary" href="radar/">Open the live radar →</a>
          <a class="btn btn-ghost" href="#trucks">See every truck</a>
        </div>
        <p class="hero-note"><span class="dot" aria-hidden="true"></span>
        {live_line} · {n} trucks across {H.escape(city_list)} · a check-in expires after four hours</p>
      </div>
      <figure class="shot">
        <img src="assets/hero-2.jpg" alt="Food trucks lined up at a street food festival" width="1024" height="768" fetchpriority="high">
        <span class="shot-badge"><span class="dot" aria-hidden="true"></span> 0% markup on every order</span>
        <figcaption>Street food, still run by the people who cook it. Photo: Geoff Peters 604 (CC BY)</figcaption>
      </figure>
    </div>
    <div class="wrap">
      <div class="stats">
        <div class="stat reveal"><b>{n}</b><span>trucks tracked and listed free</span></div>
        <div class="stat reveal"><b>{len(d['cities'])}</b><span>markets served: {H.escape(city_list)}</span></div>
        <div class="stat reveal"><b>{d['menu_items']}</b><span>menu items listed · {d['confirmed_prices']} prices vendor-confirmed</span></div>
        <div class="stat reveal"><b>0%</b><span>delivery markup — you pay the truck, not us</span></div>
      </div>
    </div>
  </section>

  <section class="sec tight" id="how">
    <div class="wrap">
      <p class="eyebrow">Three steps between you and lunch</p>
      <h2>A truck, a map, and a phone number.</h2>
      <p class="lead" style="margin-bottom:28px">No app to install, no account to make, no delivery fee added
      behind your back. This is a directory with a live map — nothing more, on purpose.</p>
      <div class="steps">
        <div class="step reveal"><h3>See who has checked in</h3>
        <p class="muted">The radar sorts every truck by how far it is from you. A truck is marked live only when the
        vendor checks in or confirms they are serving, and that lasts four hours. Everything else shows its usual area.</p></div>
        <div class="step reveal"><h3>Call or walk up</h3>
        <p class="muted">Tap to call, or tap the truck for its area. No ordering app in between, which is why
        there's no markup and no per-order fee.</p></div>
        <div class="step reveal"><h3>Rate them after you eat</h3>
        <p class="muted">One message, real stars. Those reviews are the only thing that can earn a truck the
        HIGHLY RECOMMENDED badge — and the only thing that can lose it.</p></div>
      </div>
    </div>
  </section>

  <section class="sec" id="trucks" style="background:var(--paper-2)">
    <div class="wrap">
      <p class="eyebrow">The roster</p>
      <h2>Every truck we track, updated {d['built_human']}.</h2>
      <p class="lead" style="margin-bottom:30px">{n} trucks across {H.escape(city_list)}. {live_line}.
      Ratings show as zero until a real customer leaves one — we don't seed them.</p>
      <div class="vendors">
{trucks}
      </div>
      <p class="small muted" style="margin-top:26px">Menu prices and spots come from vendors; prices are explicitly marked unconfirmed until the truck verifies them. Photos are Creative Commons licensed (credited in the footer) and show the kind of food each truck makes — ask any truck for its own photos and we'll swap them in.</p>
    </div>
  </section>

  <section class="sec tight" id="mytrucks" hidden style="background:var(--paper-2)">
    <div class="wrap">
      <p class="eyebrow">Saved on this device</p>
      <h2>My trucks</h2>
      <p class="small muted">Trucks you saved with the heart button. Saved in this browser only; nothing is sent to us.</p>
      <div class="vendors" id="myTrucksList" style="margin-top:20px"></div>
    </div>
  </section>

  <section class="sec" id="reviews">
    <div class="wrap">
      <p class="eyebrow">Ratings, comments, one badge that matters</p>
      <h2>Reviews humans write. A badge trucks earn.</h2>
      <p class="lead" style="margin-bottom:26px">{f"{d['reviews']} reviews so far across {n} trucks" if d['reviews'] else "Zero reviews so far — and that number is the honest one"}.
      Leave a review by message &mdash; no account, no app. Tap <a href="{REVIEW_BOT_LINK}">@Sheba_telegram_bot</a> and send
      a rating like &ldquo;5 Big Papa&#39;s Grill - great brisket&rdquo;.</p>
      <div class="reviews-grid">
{review_block(d)}
      </div>
      <p style="margin-top:26px"><a class="btn btn-ghost" href="reviews/">See all ratings</a></p>
    </div>
  </section>

  <section class="sec" id="vendors" style="background:var(--paper-2)">
    <div class="wrap">
      <p class="eyebrow">For food trucks</p>
      <h2>Get found by people who are already hungry.</h2>
      <p class="lead" style="margin-bottom:30px">We charge nothing to list a truck, and nothing per order.
      A listing is a page with your food, your phone number, your usual spots and a pin that lights up only when you
      check in with us.</p>
      <div class="tiers">
        <div class="tier reveal">
          <h3>Free listing</h3>
          <div class="price">$0 <small>forever</small></div>
          <ul>
            <li>Your truck on the radar and in the roster</li>
            <li>Menu, phone, usual spots, weekly schedule</li>
            <li>Live pin when you check in — it expires after four hours</li>
            <li>Ratings and reviews from real customers</li>
          </ul>
          <a class="btn btn-primary" href="{DESK}">Check listing status →</a>
        </div>
        <div class="tier reveal">
          <h3>Professional</h3>
          <div class="price">$15 <small>/ month, cancel any time</small></div>
          <ul>
            <li>Full listing page you can point customers at</li>
            <li>Your menu and prices kept current</li>
            <li>Vendor-controlled menu and listing page</li>
            <li>Still no commission on any order</li>
          </ul>
          <a class="btn btn-ghost" href="{DESK}">Check plan availability →</a>
        </div>
        <div class="tier premier reveal">
          <span class="ribbon">Most trucks pick this</span>
          <h3>Premier</h3>
          <div class="price">$35 <small>/ month, cancel any time</small></div>
          <ul>
            <li>Top of the roster and first in radius results</li>
            <li>Full-size photo and your story on the page</li>
            <li>Priority in event and catering matching</li>
            <li>Still no commission on any order</li>
          </ul>
          <a class="btn btn-ghost" href="{DESK}">Check plan availability →</a>
        </div>
      </div>
      <p class="small muted" style="margin-top:20px">Catering, Brewery, and Event Bookings: a <strong>$250 booking deposit</strong>
      holds the date and is credited to the final bill — <a href="https://buy.stripe.com/6oUcMY3KX26vgG03uh08g0s"><strong>Reserve a food truck date ($250 deposit) →</strong></a> or ask us and we'll match the headcount to the right trucks.Listed trucks can also <a href="qr-stickers/"><strong>download a free printable Window QR Sticker</strong></a> so customers in line can scan to rate them or check where they are parked tomorrow.</p>
      <p class="small muted" style="margin-top:22px">Premier placement is the only thing we sell. The badge is not
      for sale at any price — it comes from reviews or it doesn't come.</p>

      <aside id="wwe-venue-rotations" class="reveal" style="margin-top:24px;padding:20px;background:var(--paper);border:2px solid var(--ink);border-radius:14px">
        <p class="eyebrow" style="margin:0 0 6px">For Breweries, Taprooms, Hospitals &amp; Workplaces</p>
        <h3 style="margin:0 0 8px;font-size:1.18rem">Need a Verified Food Truck Rotation or Event Catering?</h3>
        <p class="small" style="margin:0 0 12px">Taprooms without kitchens, shift-change employers (hospitals, warehouses, campuses), and HOAs across Pueblo, Colorado Springs, Cañon City, and Fountain can request a rotating food truck schedule or book a multi-truck event directly — <strong>0% platform markup</strong>.</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <a class="btn btn-primary" href="https://buy.stripe.com/6oUcMY3KX26vgG03uh08g0s">Reserve Event / Catering Date ($250 Deposit) →</a>
          <a class="btn btn-ghost" href="{DESK_BOT_LINK}">Request Free Taproom / Shift-Change Rotation →</a>
          <a class="btn btn-ghost" href="qr-stickers/">Truck Window QR Stickers (All 31 Trucks) →</a>
        </div>
      </aside>

      <div class="reveal" style="margin-top:32px;background:var(--paper);border:2px solid var(--ink);border-radius:16px;padding:24px;overflow-x:auto">
        <p class="eyebrow">In Today&apos;s Economy &middot; Diners &amp; Trucks Keep Their Money</p>
        <h3 style="margin:6px 0 10px">How Where We Eatin&apos;? Compares to Delivery Apps &amp; National Directories</h3>
        <p class="small muted" style="margin-bottom:16px">Why pay 25% menu markups as a customer — or give away 30% of your window sales as a truck?</p>
        <table style="width:100%;border-collapse:collapse;font-size:.92rem;min-width:580px;text-align:left">
          <thead>
            <tr style="border-bottom:2px solid var(--ink)">
              <th style="padding:10px 12px">Cost &amp; Experience</th>
              <th style="padding:10px 12px;background:var(--paper-2)">Where We Eatin&apos;?</th>
              <th style="padding:10px 12px">Delivery Apps (DoorDash / Uber Eats)</th>
              <th style="padding:10px 12px">National Directories (Roaming Hunger / Truckster)</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid var(--rule)">
              <td style="padding:10px 12px;font-weight:700">Customer Menu Prices</td>
              <td style="padding:10px 12px;background:var(--paper-2);font-weight:700">0% markup &middot; Real window prices</td>
              <td style="padding:10px 12px">15%&ndash;30% menu markup + service &amp; delivery fees</td>
              <td style="padding:10px 12px">Often no menu prices shown</td>
            </tr>
            <tr style="border-bottom:1px solid var(--rule)">
              <td style="padding:10px 12px;font-weight:700">Commission Taken From the Truck</td>
              <td style="padding:10px 12px;background:var(--paper-2);font-weight:700">0% commission on every order</td>
              <td style="padding:10px 12px">15%&ndash;30% commission per order</td>
              <td style="padding:10px 12px">Catering/event booking fee cut</td>
            </tr>
            <tr style="border-bottom:1px solid var(--rule)">
              <td style="padding:10px 12px;font-weight:700">Monthly Truck Listing Cost</td>
              <td style="padding:10px 12px;background:var(--paper-2);font-weight:700">$0 Free forever &middot; $15 Pro &middot; $35 Premier</td>
              <td style="padding:10px 12px">Tablet fees + mandatory promo discounts</td>
              <td style="padding:10px 12px">$25+/mo or catering-only lock-in</td>
            </tr>
            <tr>
              <td style="padding:10px 12px;font-weight:700">Location &amp; Badge Honesty</td>
              <td style="padding:10px 12px;background:var(--paper-2);font-weight:700">4-hr expiring vendor check-in + earned-only review badge</td>
              <td style="padding:10px 12px">Paid sponsored ranking</td>
              <td style="padding:10px 12px">Static calendars that go stale</td>
            </tr>
          </tbody>
        </table>
        <aside id="wwe-roi-calc" style="margin-top:18px;padding:16px;background:var(--paper-2);border-radius:12px">
          <p style="margin:0 0 8px;font-weight:700">Interactive 0%-Commission Savings Calculator &middot; Se Habla Espa&ntilde;ol</p>
          <p class="small" style="margin:0">
            <label for="wweSales" style="font-weight:700;margin-right:8px">Weekly window sales routed via directory:</label>
            <select id="wweSales" onchange="window.updateWweCalc && window.updateWweCalc()" style="padding:6px 10px;border-radius:8px;font-weight:700;margin-right:12px">
              <option value="500">$500 / week</option>
              <option value="1000" selected>$1,000 / week</option>
              <option value="2500">$2,500 / week</option>
              <option value="5000">$5,000 / week</option>
            </select>
            <strong id="wweCalcOut">At $1,000/wk in orders, 0% commission on Where We Eatin&apos;? saves your truck $13,000/year vs. a 25% delivery-app cut.</strong>
          </p>
        </aside>

        <aside id="wwe-cbc-combo" style="margin-top:18px;padding:20px;background:var(--paper-2);border:2px solid var(--ink);border-radius:14px">
          <p class="eyebrow" style="margin:0 0 6px">Party, Catering &amp; Vendor Combo Partner &middot; Colorado Bounce Club</p>
          <h4 style="margin:0 0 8px;font-size:1.15rem">Feed &amp; Bounce Combo: Food Trucks + 8-Hour Bounce Houses &amp; Water Slides</h4>
          <p class="small" style="margin:0 0 10px">Planning a birthday, quincea&ntilde;era, graduation, school carnival, or block party in Pueblo or Colorado Springs? Pair a local food truck ($250 catering deposit credited to your final bill) with an 8-hour sanitized inflatable from veteran-owned <a href="https://coloradobounceclub.com/" target="_blank" rel="noopener"><strong>Colorado Bounce Club</strong></a> (719-299-0772):</p>
          <ul class="small" style="margin:0 0 12px;padding-left:20px">
            <li><strong>Customer Party Combo ($25 OFF):</strong> Get <strong>$25 OFF any 8-hour Bounce House ($150&ndash;$175), Tiny Town Toddler Bouncer ($85), or Water Slide ($175&ndash;$275)</strong> when booked alongside a Where We Eatin&apos;? food truck. Free delivery in Pueblo ($50 within 50 miles).</li>
            <li><strong>Listed Food Truck Vendor Perk (20% OFF + $20 Credit):</strong> Listed trucks get <strong>20% OFF weekday &amp; pop-up event inflatables</strong> to draw families to their rally, plus a <strong>$20 referral credit</strong> toward Professional ($15/mo) or Premier ($35/mo) for every catering party referred.</li>
          </ul>
          <p class="small" style="margin:0"><a class="btn btn-ghost" href="https://coloradobounceclub.com/" target="_blank" rel="noopener">Explore Colorado Bounce Club Rentals (719-299-0772) &rarr;</a></p>
        </aside>
      </div>
    </div>
  </section>

  {squadpoll_block(d)}
  {community_hub_block()}

  <section class="sec faq" id="faq">
    <div class="wrap">
      <p class="eyebrow">The honest answers</p>
      <h2>Questions people actually ask.</h2>
      <div style="margin-top:22px">
        <details open><summary>Do you take a cut of what I spend at the truck?</summary>
        <p>No. There is no ordering, no delivery and no card processing here — you pay the truck directly,
        which is why everything costs what the truck charges.</p></details>
        <details><summary>How do you know where a truck is right now?</summary>
        <p>Only when the truck checks in with us, or confirms it is serving. A check-in is labelled live and expires
        after four hours. Every other truck shows its <em>usual area</em>, which means exactly that: their normal patch,
        not a live position. We don't pretend otherwise.</p></details>
        <details><summary>Does it cost a truck anything to be listed?</summary>
        <p>No. Listing is free forever and includes the radar pin, menu, phone number and reviews. Optional
        paid plans are Professional at $15/month and Premier at $35/month; neither affects ratings.</p></details>
        <details><summary>Can a truck buy the HIGHLY RECOMMENDED badge?</summary>
        <p>No. It requires {R.MIN_REVIEWS}+ reviews, a {R.MIN_AVG}+ average and no review below 3 stars in the last
        {R.BADGE_WINDOW_DAYS} days. It recalculates on every review, so it can be lost as well as earned.</p></details>
        <details><summary>Who are you?</summary>
        <p>An independent local directory started in Pueblo, not a franchise, not a delivery app. If we
        can't prove something on this site with a real number, we say so — including that we have
        {d['reviews']} reviews and {n} trucks so far.</p></details>
        <details><summary>I'm a truck and I want in. What do I send?</summary>
        <p>Message <a href="{DESK_BOT_LINK}">@Sheba_telegram_bot</a> and send your truck name, what you sell, your
        phone, and your usual area &mdash; free to list, no commission. Check the
        <a href="list-your-truck/">For trucks page</a> for the full details.</p></details>
      </div>
    </div>
  </section>

  <section class="sec tight">
    <div class="wrap">
      <div class="banner reveal">
        <div>
          <h2>Hungry now? Open the radar.</h2>
          <p>Sorted by distance from you, with a call button on every truck.</p>
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          <a class="btn btn-primary" href="radar/">Open the radar →</a>
          <a class="btn btn-ghost" href="{DESK}">Listing status</a>
        </div>
      </div>
    </div>
  </section>
</main>

<footer class="foot">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <a class="brand" href="./" style="margin-bottom:12px"><span class="brand-mark">WW</span> Where We Eatin'?</a>
        <p class="small muted" style="margin-top:12px;max-width:34ch">Independent food-truck directory for
        Pueblo, Pueblo West, Colorado Springs and Cañon City. Free listings, no commission, no app.</p>
      </div>
      <div>
        <h4>Find food</h4>
        <ul>
          <li><a href="radar/">Live radar</a></li>
          <li><a href="promotions/">Vendor-posted offers &amp; specialties</a></li>
          <li><a href="travel/">Road trip radar &mdash; eat &amp; fuel on the drive</a></li>
          <li><a href="#trucks">All {n} trucks</a></li>
          <li><a href="reviews/">Reviews &amp; ratings</a></li>
          <li><a href="list-your-truck/">Get your truck listed</a></li>
        </ul>
        <h4>Cities we cover</h4>
        <ul>
          {city_links}
        </ul>
      </div>
      <div>
        <h4>For trucks</h4>
        <ul>
          <li><a href="#vendors">Pricing</a></li>
          <li><a href="list-your-truck/">Listing status</a></li>
          <li><a href="#faq">FAQ</a></li>
        </ul>
      </div>
      <div>
        <h4>About</h4>
        <ul>
          <li><a href="privacy/">Privacy policy</a></li>
          <li><a href="sitemap.xml">Sitemap</a></li>
          <li><a href="#faq">How the badge works</a></li>
        </ul>
      </div>
    </div>
    <div class="foot-legal">
      <span>© <span id="year">2026</span> Where We Eatin'? · Built and updated {d['built']} from our own vendor records.</span>
      <span>Get listed or leave a review by message: <a href="{DESK_BOT_LINK}">@Sheba_telegram_bot</a>.</span>
    </div>
    <p class="small muted" style="margin:14px 0 0">Photos: Creative Commons (BY / BY-SA) via Flickr —
    Geoff Peters 604, Phil Denton, ricardodiaz11 and others; full credits in <a href="assets/credits.json">credits.json</a>.
    Truck facts, prices and locations come from each vendor; ratings come from customer reviews.</p>
  </div>
</footer>
{site_base.footer_block()}

<script src="assets/site.js" defer></script>
<script src="assets/favorites.js" defer></script>
<script src="assets/share.js" defer></script>
<script>
/* Registers the service worker. A manifest alone does NOT make a site installable and the offline shell never
   activates without this - which is why the "mobile app" was not one. Braces are doubled: this markup lives
   inside a Python f-string. */
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', function () {{
    navigator.serviceWorker.register('/sw.js').catch(function () {{}});
  }});
}}
window.updateWweCalc = function () {{
  var el = document.getElementById('wweSales');
  var out = document.getElementById('wweCalcOut');
  if (!el || !out) return;
  var wk = parseInt(el.value || '1000', 10);
  var yrSave = Math.round(wk * 0.25 * 52);
  var lang = document.documentElement.getAttribute('data-lang') || 'en';
  if (lang === 'es') {{
    out.textContent = 'Con $' + wk.toLocaleString() + '/semana en ventas, 0% de comisión en Where We Eatin\'? le ahorra a su lonchera $' + yrSave.toLocaleString() + '/año frente al 25% de las apps de entrega.';
  }} else {{
    out.textContent = 'At $' + wk.toLocaleString() + '/wk in orders, 0% commission on Where We Eatin\'? saves your truck $' + yrSave.toLocaleString() + '/year vs. a 25% delivery-app cut.';
  }}
}};
(function () {{
  var es = {{
    'Get found by people who are already hungry.': 'Que lo encuentren las personas que ya tienen hambre.',
    'Free listing': 'Listado gratis',
    'Professional': 'Profesional',
    'Questions people actually ask.': 'Preguntas que la gente realmente hace.',
    'Hungry now? Open the radar.': '¿Tiene hambre ahora? Abra el radar.',
    'Open the radar →': 'Abrir el radar →'
  }};
  var rev = {{}}; Object.keys(es).forEach(function (k) {{ rev[es[k]] = k; }});
  var bar = document.createElement('aside');
  bar.style.cssText = 'position:fixed;bottom:16px;left:16px;z-index:999;background:#1c1917;color:#fff;padding:6px 12px;border-radius:999px;border:2px solid #d81f26;display:flex;gap:8px;align-items:center;font-size:0.82rem;font-weight:700;';
  var bEn = document.createElement('button'); bEn.type = 'button'; bEn.textContent = 'EN';
  bEn.style.cssText = 'padding:4px 10px;border-radius:999px;border:none;background:#d81f26;color:#fff;font-weight:800;cursor:pointer;';
  var bEs = document.createElement('button'); bEs.type = 'button'; bEs.textContent = 'Español (ES)';
  bEs.style.cssText = 'padding:4px 10px;border-radius:999px;border:1px solid #fff;background:transparent;color:#fff;font-weight:800;cursor:pointer;';
  bar.appendChild(bEn); bar.appendChild(bEs); document.body.appendChild(bar);
  function setLang(l) {{
    document.documentElement.setAttribute('data-lang', l);
    var d = l === 'es' ? es : rev;
    document.querySelectorAll('h2,h3,a').forEach(function (el) {{
      if (el.children.length === 0) {{ var t = (el.textContent || '').trim(); if (d[t]) el.textContent = d[t]; }}
    }});
    window.updateWweCalc();
  }}
  bEn.onclick = function () {{ setLang('en'); }}; bEs.onclick = function () {{ setLang('es'); }};
  if (new URLSearchParams(location.search).get('lang') === 'es') setLang('es');
}})();
</script>
  <script src="/assets/mobile-app-install.js" defer></script>
</body>
</html>
"""


if __name__ == "__main__":
    page = build()
    cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
    if "--check" in sys.argv:
        ok = site_base.same(page, cur)
        print("CURRENT" if ok else "STALE")
        raise SystemExit(0 if ok else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    d = data()
    print(f"wrote {OUT} ({len(page)} bytes, {len(d['trucks'])} trucks, {d['reviews']} reviews, {len(d['cities'])} cities)")
