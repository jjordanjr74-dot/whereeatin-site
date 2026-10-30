"""Per-truck listing pages — the thing a paid listing actually buys.

WHY THIS EXISTS
  `vendor_tiers.ENTITLEMENTS` promises `listing_page` to Professional ($15) and Premier ($35). Nothing built one.
  So the product's own price list was advertising a deliverable that did not exist, and the sales conversation had
  nothing to show a food truck. This generates a real page per truck, from the database, and links it from the
  roster.

WHAT THE FREE TIER GETS, AND WHY THAT IS NOT A LIE
  Every truck gets a page, but a free truck's page is an UNCLAIMED listing: real public data, prices explicitly
  marked unconfirmed, and a banner saying nobody from the truck has claimed it. That is the honest state (Yelp and
  TripAdvisor work the same way) and it is also the sales asset — the truck sees its own page, with its own menu
  and its own name, and the price it would cost to own it.

  Paid trucks get the same page marked CLAIMED, without the claim banner. Paid placement is labelled as paid, never
  dressed up as earned, matching the roster's existing rule.

HONESTY
  All menu prices currently sit at price_source='unverified' — seeded, never confirmed by the vendor. They are
  printed WITH that state rather than as fact, and confirming them is exactly what the paid tier sells.

Usage:
  python build_listing.py            # write trucks/<slug>/index.html for every truck, plus trucks/index.html
  python build_listing.py --check    # report STALE/CURRENT without writing
"""
from __future__ import annotations

import datetime
import html as H
import json
import os
import pathlib
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(VR, "vendors_row"))

import build_site as BS  # reuse photo_for/data/stars so the roster and the pages cannot diverge
import site_base
import stripe_tools as ST
import vendor_tiers as VT

DB = os.path.join(VR, "vendors_row", "vendors_row.db")
OUTDIR = os.path.join(HERE, "trucks")
CLAIM_KIND = "professional"


slug = site_base.slug          # one definition, shared with the roster builder


def menu_for(con, vendor_id: int) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT name, description, price_cents, price_source, is_available FROM menu_items "
        "WHERE vendor_id=? ORDER BY price_cents", (vendor_id,))]


def money(cents) -> str:
    return f"${cents / 100:,.2f}" if cents else "—"


def claim_link(name: str, kind: str = CLAIM_KIND) -> str:
    """A live $15 or $35 link tagged with THIS vendor, so the reconciler can grant the right row.

    Checks payment_links.json first (permanent buy.stripe.com links), then falls back to stripe_links.csv.
    """
    pl_path = os.path.join(VR, "vendors_row", "payment_links.json")
    if os.path.isfile(pl_path):
        try:
            pl_data = json.load(open(pl_path, encoding="utf-8"))
            entry = (pl_data.get("links") or {}).get(f"{kind}|{name}") or {}
            url = entry.get("url") or ""
            if url.startswith("https://buy.stripe.com/"):
                return url
        except Exception:
            pass
    if os.path.isfile(ST.TRACKER):
        with open(ST.TRACKER, encoding="utf-8") as fh:
            rows = list(__import__("csv").DictReader(fh))
        for r in reversed(rows):
            url = r.get("url") or ""
            if r.get("kind") == kind and r.get("who") == name and url.startswith("https://buy.stripe.com/"):
                return url
        for r in reversed(rows):
            url = r.get("url") or ""
            if r.get("kind") == kind and r.get("who") == name and "cs_live_" in url:
                return url
        for r in reversed(rows):                       # last resort: any link, but never a test one
            url = r.get("url") or ""
            if r.get("kind") == kind and r.get("who") == name and "cs_test_" not in url:
                return url
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):            # make_link prints; a build should stay quiet
        out = ST.make_link(kind, name)
    return out.get("url", "")


def tier_pin(tier: str) -> str:
    label = {"premier": "PREMIER", "professional": "PROFESSIONAL"}.get(tier, "")
    return f'<span class="pin pin-tier">{label}</span>' if label else ""


def page(t: dict, items: list[dict], link: str) -> str:
    tier = VT.normalize(t.get("tier"))
    paid = VT.has(tier, "listing_page")
    name, city, cuisine, area = t["name"], t["city"], t["cuisine"], t["area"]
    s = slug(name)
    path = f"trucks/{s}/"
    rating = (f'<span class="stars">{BS.stars(t["rating"])}</span> <strong>{t["rating"]:.1f}</strong> '
              f'<span class="muted small">({t["reviews"]} review{"s" if t["reviews"] != 1 else ""})</span>'
              if t["reviews"] else '<span class="none">New listing · no reviews yet</span>')
    tel = re.sub(r"[^0-9+]", "", t["phone"] or "")
    call = f'<a class="btn btn-primary" id="callBtn" href="tel:{tel}">Call {H.escape(t["phone"])}</a>' if t["phone"] else ""
    tap_body = (f'var _cb=document.getElementById("callBtn");'
                f'if(_cb){{_cb.addEventListener("click",function(){{'
                f'if(navigator.sendBeacon)navigator.sendBeacon("/tap/{t["id"]}");}});}}'
                if t.get("phone") else "")
    call_tap_js = "<script>__NAVJS__\n" + tap_body + "</script>"
    # live only with a fresh check-in or fresh vendor-confirmed serving (shared rule in checkin_state)
    loc = BS.live_pin(t)
    if t["live"]:
        status = f"Checked in · {H.escape(area)}" if t["checked_in"] else f"Serving now · {H.escape(area)}"
    else:
        status = f"Usually around {H.escape(area)}. Not checked in right now."
    badge = '<span class="pin pin-badge-earned">HIGHLY RECOMMENDED</span>' if t["badge"] else ""
    rows = []
    for it in items:
        unconfirmed = (it.get("price_source") or "unverified") != "vendor-confirmed"
        flag = ' <span class="muted small">· price unconfirmed</span>' if unconfirmed else ""
        desc = f'<div class="small muted">{H.escape(it["description"])}</div>' if it.get("description") else ""
        rows.append(f'        <li style="display:flex;gap:12px;justify-content:space-between;padding:10px 0;'
                    f'border-bottom:1px solid var(--line)"><div><strong>{H.escape(it["name"])}</strong>{desc}'
                    f'</div><div style="white-space:nowrap">{money(it.get("price_cents"))}{flag}</div></li>')

    if paid:
        state = (f'<h2>Claimed listing</h2><p>This page is maintained with the vendor on the '
                 f'<strong>{VT.TIER_LABELS[tier]}</strong> plan, which keeps the menu and prices current.</p>')
    else:
        prem_link = claim_link(name, "premier")
        prem_btn = (f' <a class="btn btn-ghost" href="{H.escape(prem_link)}">Upgrade to Premier (#1 in radius + catering priority) — $35/month</a>'
                    if prem_link else '')
        state = (f'<h2>Unclaimed listing</h2>'
                 f'<p>Nobody from <strong>{H.escape(name)}</strong> has claimed this page. We built it from public '
                 f'information so people can find them — the details may be out of date.</p>'
                 f'<p><strong>Is this your truck?</strong> Claiming it puts you in control of this page: confirm '
                 f'your prices, keep your menu current, and get your own link to put in your bio.</p>'
                 + (f'<p style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn btn-primary" href="{H.escape(link)}">Claim this listing (Professional) — $15/month</a>{prem_btn}</p>'
                    if link else '')
                 + '<p class="small muted">Free listings stay free. You only pay if you want the page kept current '
                   'and controlled by you. <a href="/qr-stickers/' + t["slug"] + '.png" download="' + t["slug"] + '-window-qr.png">Download your free printable window QR sticker (.PNG) →</a></p>')

    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "FoodEstablishment",
        "name": name, "servesCuisine": cuisine, "telephone": t["phone"],
        "address": {"@type": "PostalAddress", "addressLocality": city, "addressRegion": "CO", "addressCountry": "US"},
        "url": site_base.url(path),
        **({"aggregateRating": {"@type": "AggregateRating", "ratingValue": round(t["rating"], 1),
                                "reviewCount": t["reviews"]}} if t["reviews"] else {}),
    }, ensure_ascii=False)
    title = f"{name} — {cuisine} in {city} | Where We Eatin'?"
    desc = f"{name}: {cuisine} in {city}. Usually around {area}. Menu, phone and how to call them."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)}</title>
<meta name="description" content="{H.escape(desc, quote=True)}">
<link rel="canonical" href="{site_base.url(path)}">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#d81f26">
<link rel="stylesheet" href="/assets/site.css">
__OG__
<script type="application/ld+json">{jsonld}</script>
<style>__NAVCSS__</style>
</head>
<body>
__NAV__
<main class="wrap">
  <p class="small muted"><a href="/trucks/">← All trucks</a></p>
  <article class="vendor" data-slug="{s}">
    <div class="vendor-media">
      <img src="/assets/{t['photo']}" alt="{H.escape(name)} — {H.escape(cuisine)}" width="1024" height="640">
      <div class="vendor-pins">{loc}{tier_pin(tier)}{badge}</div>
    </div>
    <div class="vendor-body">
      <h1>{H.escape(name)}</h1>
      <p class="vendor-meta">{H.escape(cuisine)} · {H.escape(city)}</p>
      <p class="small muted">{status}</p>
      <p class="rating">{rating}</p>
      <div class="vendor-foot">{call}{site_base.follow_button(s, name)}{site_base.fav_button(s, name)}<a class="btn btn-sm btn-ghost" href="/radar/">Radar</a>{site_base.share_button(site_base.url(path), title)}</div>
    </div>
  </article>

  <section style="margin-top:28px">
    <h2>Menu</h2>
    <ul style="list-style:none;padding:0;margin:0">
{chr(10).join(rows)}
    </ul>
    <p class="small muted">Prices are what we have on record. Nothing here has been confirmed by the vendor yet.</p>
  </section>

  <section style="margin-top:28px">{state}</section>
</main>
__FOOT__
<script src="/assets/favorites.js" defer></script>
<script src="/assets/share.js" defer></script>
{call_tap_js}
</body>
</html>
""".replace("__OG__", site_base.og_block(title, desc, path, image=t["photo"])) \
        .replace("__NAVCSS__", site_base.NAV_CSS) \
        .replace("__NAV__", site_base.nav_block(f"/{path}")) \
        .replace("__NAVJS__", site_base.NAV_JS) \
        .replace("__FOOT__", site_base.footer_block())


def index_page(trucks: list[dict]) -> str:
    live_n = sum(1 for t in trucks if t["live"])
    cards = "\n".join(
        f'      <li style="padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:10px;flex-wrap:wrap;align-items:center">'
        f'<a href="/trucks/{slug(t["name"])}/"><strong>{H.escape(t["name"])}</strong></a> '
        f'<span class="muted small">{H.escape(t["cuisine"])} · {H.escape(t["city"])}'
        + (" · checked in" if t["live"] else "") + '</span>'
        + site_base.follow_button(slug(t["name"]), t["name"]) + site_base.fav_button(slug(t["name"]), t["name"]) + '</li>'
        for t in sorted(trucks, key=lambda x: x["name"]))
    desc = "Listing pages for every food truck tracked in Pueblo, Pueblo West, Colorado Springs and Cañon City."
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Every truck we track | Where We Eatin'?</title>
<meta name="description" content="{H.escape(desc, quote=True)}">
<link rel="canonical" href="{site_base.url('trucks/')}">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#d81f26">
<link rel="stylesheet" href="/assets/site.css">
__OG__
<style>__NAVCSS__</style>
</head>
<body>
__NAV__
<main class="wrap">
  <h1>Every truck we track</h1>
  <p class="muted">{H.escape(site_base.live_sentence(live_n))}. Each truck has its own page with its usual area; vendors can claim theirs and keep it current.</p>
  <ul style="list-style:none;padding:0;margin:0">
{cards}
  </ul>
</main>
__FOOT__
<script src="/assets/favorites.js" defer></script>
</body>
</html>
""".replace("__OG__", site_base.og_block(
        "Every food truck we track in Southern Colorado", desc, "trucks/")) \
        .replace("__NAVCSS__", site_base.NAV_CSS) \
        .replace("__NAV__", site_base.nav_block("/trucks/")) \
        .replace("__FOOT__", site_base.footer_block())


def sitemap(trucks: list[dict]) -> str:
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    pages = [("", "weekly", "1.0"), ("radar/", "hourly", "0.9"), ("travel/", "hourly", "0.9"),
             ("promotions/", "daily", "0.8"),
             ("trucks/", "daily", "0.8"), ("list-your-truck/", "monthly", "0.7"),
             ("reviews/", "daily", "0.7"), ("privacy/", "yearly", "0.3")]
    pages += [(h["path"], "weekly", "0.7") for h in site_base.CITY_HUBS]
    pages += [(f"trucks/{slug(t['name'])}/", "weekly", "0.8") for t in sorted(trucks, key=lambda x: x["name"])]
    rows = "\n".join(
        f'  <url><loc>{site_base.url(p)}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq>'
        + (f'<priority>{pri}</priority>' if pri else '') + '</url>'
        for p, f, pri in pages)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + '\n</urlset>\n')


def build(check: bool = False) -> int:
    d = BS.data()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    ids = {r["name"]: r["id"] for r in con.execute("SELECT id, name FROM vendors")}

    written = stale = 0
    for t in d["trucks"]:
        items = menu_for(con, ids.get(t["name"], -1))
        link = "" if VT.has(t.get("tier"), "listing_page") else claim_link(t["name"])
        html = page(t, items, link)
        path = os.path.join(OUTDIR, slug(t["name"]), "index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cur = pathlib.Path(path).read_text(encoding="utf-8") if os.path.isfile(path) else ""
        if site_base.same(html, cur):
            continue
        if check:
            stale += 1
            print(f"  STALE {os.path.relpath(path, HERE)}")
            continue
        pathlib.Path(path).write_text(html, encoding="utf-8")
        written += 1
    con.close()

    for name, content in (("trucks/index.html", index_page(d["trucks"])),
                          ("sitemap.xml", sitemap(d["trucks"]))):
        path = os.path.join(HERE, name) if name != "trucks/index.html" else os.path.join(OUTDIR, "index.html")
        cur = pathlib.Path(path).read_text(encoding="utf-8") if os.path.isfile(path) else ""
        if site_base.same(content, cur):
            continue
        if check:
            stale += 1
            print(f"  STALE {name}")
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pathlib.Path(path).write_text(content, encoding="utf-8")
        written += 1

    if check:
        print(f"{'STALE' if stale else 'CURRENT'} — {stale} page(s) would change")
        return 1 if stale else 0
    print(f"wrote {written} file(s) under trucks/ (+sitemap.xml) for {len(d['trucks'])} trucks")
    return 0


if __name__ == "__main__":
    raise SystemExit(build(check="--check" in sys.argv))