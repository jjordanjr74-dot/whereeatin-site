#!/usr/bin/env python3
"""Build the PUBLIC live radar: a real map with the trucks, distances, and where you are.

Why this exists: the venture had a working radar only on a private machine (`:5596`), so customers
could not see anything, while the public site showed a plain list. The static site can carry a real
map with no backend and no API key — Leaflet + OpenStreetMap tiles + client-side haversine — so the
radar is publishable today and stays honest about what "live" means.

Freshness rule: each vendor's coordinates are the AREA they park in, updated by hand from their own
word (and from the Telegram listing desk), not a GPS feed from the truck. The page says so, because
a map that implies real-time GPS when it is not is a lie a customer discovers on the street.

Usage: python build_radar.py [--check]
"""
from __future__ import annotations
import site_base  # noqa: E402  the one place the site URL lives

import datetime
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "radar", "index.html")
DB = os.path.join(os.path.dirname(HERE), "vendors_row", "vendors_row.db")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "vendors_row"))
import reviews as REVIEWS  # noqa: E402  (ratings rules live in reviews.py)
import checkin_state as CHECKINS  # noqa: E402  (freshness rules live in one module)

VENDORS_DB = os.path.join(os.path.dirname(HERE), "vendors_row", "vendors_row.db")


def serving_count():
    return CHECKINS.verified_serving_count(VENDORS_DB)


def location_state(row, now=None):
    return CHECKINS.public_state(row, now=now)




def vendors() -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "vendors_row"))
    import vendor_tiers as VT       # the radar must honour the placement the $35 tier pays for
    VT.ensure_schema(con)
    rows = []
    CHECKINS.ensure_schema(con)
    for r in con.execute("select id, name, category, current_location, city, lat, lon, base_lat, base_lon, "
                         "checkin_lat, checkin_lon, phone, status, serving_status, status_updated_at, "
                         "location_updated_at, location_source, listing_tier "
                         "from vendors where name is not null order by id"):
        d = dict(r)
        public = CHECKINS.public_state(d)
        if public["lat"] is None or public["lon"] is None:
            continue
        rows.append({"id": d["id"], "name": d["name"], "cuisine": d["category"] or "",
                     "area": d["current_location"] or "", "city": d["city"] or "",
                     "lat": public["lat"], "lon": public["lon"], "phone": d["phone"] or "",
                     "serving": public["serving"], "status_label": public["status_label"],
                     "status_age_minutes": public["status_age_minutes"],
                     "location_label": public["location_label"], "location_age_minutes": public["location_age_minutes"],
                     "reported": d["location_updated_at"] if public["location_fresh"] else None,
                     "tier": VT.normalize(d["listing_tier"]),
                     "tier_rank": VT.rank(d["listing_tier"])})
    con.close()
    # ratings come from the one place that owns the rules, so the map can never show a badge the
    # reviews page does not agree with
    ratings = {r["id"]: r for r in REVIEWS.summary()}
    for r in rows:
        rt = ratings.get(r["id"], {})
        r["average"] = rt.get("average", 0)
        r["reviews"] = rt.get("count", 0)
        r["badge"] = bool(rt.get("highly_recommended"))
    return rows


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live radar — Where We Eatin'?</title>
<meta name="description" content="See every tracked Southern Colorado food truck on a map, sorted by how far it is from you. Free listings and direct vendor contact.">
<meta name="theme-color" content="#dc2626">
<link rel="canonical" href="__CANON__">
__OG__
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  :root{--ink:#111827;--muted:#4b5563;--brand:#dc2626;--paper:#fef2f2;--line:#e5e7eb}
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Karla,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  header{padding:18px 20px 10px;max-width:1100px;margin:0 auto}
  h1{margin:0 0 4px;font-size:26px}
  .sub{margin:0;color:var(--muted);font-size:15px}
  .wrap{max-width:1100px;margin:0 auto;padding:0 20px 60px;display:grid;grid-template-columns:1fr;gap:18px}
  @media(min-width:900px){.wrap{grid-template-columns:380px 1fr}}
  #map{height:520px;border-radius:14px;box-shadow:0 8px 30px rgba(17,24,39,.08)}
  .panel{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 8px 30px rgba(17,24,39,.06)}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  select,button{font:inherit;padding:9px 12px;border-radius:10px;border:1px solid var(--line);background:#fff}
  button.primary{background:var(--brand);color:#fff;border-color:var(--brand);font-weight:700;cursor:pointer}
  ol#list{list-style:none;margin:14px 0 0;padding:0}
  ol#list li{padding:10px 0;border-top:1px solid var(--line)}
  .name{font-weight:700}
  .meta{color:var(--muted);font-size:14px}
  .dist{float:right;font-weight:700;color:var(--brand)}
  .note{margin:12px 0 0;font-size:13px;color:var(--muted)}
  a{color:var(--brand)}
  .badge{display:inline-block;background:#ecfdf5;color:#065f46;border-radius:999px;padding:1px 8px;font-size:12px;font-weight:700}
__NAVCSS__
</style>
</head>
<body>
__NAV__
<header>
  <h1>Live radar</h1>
  <p class="sub">__COUNT__ trucks tracked across Pueblo, Pueblo West and Colorado Springs. __LIVELINE__. Distances are measured from <strong>you</strong> once you share your location &mdash; nothing is stored.</p>
</header>
<div class="wrap">
  <section class="panel">
    <div class="row">
      <button class="primary" id="locate">Use my location</button>
      <select id="radius" aria-label="Only show trucks within">
        <option value="999">any distance</option>
        <option value="5">within 5 miles</option>
        <option value="10">within 10 miles</option>
        <option value="25">within 25 miles</option>
        <option value="60">within 60 miles</option>
      </select>
      <select id="origin" aria-label="Measure distances from">
        <option value="38.2544,-104.6091">from Downtown Pueblo</option>
        <option value="38.3512,-104.72">from Pueblo West</option>
        <option value="38.8339,-104.8214">from Colorado Springs</option>
        <option value="38.4411,-105.2424">from Cañon City</option>
      </select>
    </div>
    <p class="note" id="where">Distances are from Downtown Pueblo until you share your location.</p>
    <ol id="list"></ol>
    <p class="note">A vendor check-in shows the truck's shared position for up to four hours; then the map falls back to its usual area. These are not continuous GPS updates. Serving status is shown only when the vendor confirms it and expires after four hours. Data built __BUILT__.</p>
  </section>
  <div id="map"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var VENDORS = __VENDORS__;
var map = L.map('map').setView([38.35, -104.7], 9);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
var markers = {};
VENDORS.forEach(function (v) {
  v.marker = L.marker([v.lat, v.lon]).addTo(map);
  var phone = v.phone ? '<br><a href="tel:' + v.phone.replace(/[^0-9+]/g, '') + '">' + v.phone + '</a>' : '';
  var rt = (v.reviews ? '\\u2605 ' + v.average.toFixed(1) + ' (' + v.reviews + ')' + (v.badge ? ' HIGHLY RECOMMENDED' : '') + '<br>' : '');
  v.marker.bindPopup('<strong>' + v.name + '</strong><br>' + rt + v.cuisine + '<br>' + v.area +
    ' <span class="meta">(' + v.city + ')</span><br><span class="meta">' + v.status_label + ' · ' + v.location_label + '</span>' + phone);
});
var youMarker = null;
function miles(a, b) {
  var R = 3958.8, t = Math.PI / 180;
  var dLat = (b[0] - a[0]) * t, dLon = (b[1] - a[1]) * t;
  var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos(a[0] * t) * Math.cos(b[0] * t) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return 2 * R * Math.asin(Math.sqrt(h));
}
function timeAgo(iso) {
  try {
    var mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 2) return 'just now';
    if (mins < 90) return mins + ' minutes ago';
    var h = Math.round(mins / 60);
    if (h < 36) return h + ' hours ago';
    return Math.round(h / 24) + ' days ago';
  } catch (e) { return ''; }
}
function render(origin, label) {
  var list = document.getElementById('list');
  list.innerHTML = '';
  var sorted = VENDORS.slice().sort(function (a, b) {
    // Premier placement leads the radius results (that is what the tier pays for), then nearest first
    if (a.tier_rank !== b.tier_rank) return a.tier_rank - b.tier_rank;
    return miles(origin, [a.lat, a.lon]) - miles(origin, [b.lat, b.lon]);
  });
  var maxMi = parseFloat(document.getElementById('radius').value);
  sorted = sorted.filter(function (v) { return miles(origin, [v.lat, v.lon]) <= maxMi; });
  if (!sorted.length) {
    list.innerHTML = '<li class="meta">No tracked truck inside that radius. Widen it, or move the origin.</li>';
  }
  sorted.forEach(function (v) {
    var d = miles(origin, [v.lat, v.lon]);
    var li = document.createElement('li');
    li.innerHTML = '<span class="dist">' + d.toFixed(1) + ' mi</span>' +
      '<span class="name">' + v.name + '</span>' + (v.serving ? ' <span class="badge badge-serving">serving now</span>' : '') +
      (v.tier === 'premier' ? ' <span class="badge">PREMIER</span>' : (v.tier === 'professional' ? ' <span class="badge">PROFESSIONAL</span>' : '')) +
      '<div class="meta">' + v.cuisine + ' &middot; ' + v.area + (v.phone ? ' &middot; ' + v.phone : '') + '</div>' +
      '<div class="meta">' + v.status_label + (v.status_age_minutes !== null ? ' &middot; ' + v.status_age_minutes + ' min ago' : '') + ' &middot; ' + v.location_label + (v.location_age_minutes !== null ? ' &middot; ' + v.location_age_minutes + ' min ago' : '') + '</div>' +
      '<div class="meta">' + (v.reviews ? '\u2605 ' + v.average.toFixed(1) + ' from ' + v.reviews + ' review' + (v.reviews === 1 ? '' : 's') : 'no reviews yet') +
      (v.badge ? ' <span class="badge">HIGHLY RECOMMENDED</span>' : '') + '</div>';
    li.style.cursor = 'pointer';
    li.onclick = function () { map.setView([v.lat, v.lon], 13); v.marker.openPopup(); };
    list.appendChild(li);
  });
  document.getElementById('where').textContent = 'Distances from ' + label + '.';
}
document.getElementById('radius').addEventListener('change', function () {
  var p = document.getElementById('origin').value.split(',').map(Number);
  render(p, document.getElementById('origin').options[document.getElementById('origin').selectedIndex].text.replace('from ', ''));
});
document.getElementById('origin').addEventListener('change', function (e) {
  var p = e.target.value.split(',').map(Number);
  render(p, e.target.options[e.target.selectedIndex].text.replace('from ', ''));
});
document.getElementById('locate').addEventListener('click', function () {
  if (!navigator.geolocation) { document.getElementById('where').textContent = 'This browser will not share a location - pick an origin instead.'; return; }
  navigator.geolocation.getCurrentPosition(function (pos) {
    var p = [pos.coords.latitude, pos.coords.longitude];
    if (youMarker) { map.removeLayer(youMarker); }
    youMarker = L.circleMarker(p, { radius: 8, color: '#111827', fillColor: '#111827', fillOpacity: 1 }).addTo(map)
      .bindPopup('You are here');
    map.setView(p, 11);
    render(p, 'your location (not stored, not sent anywhere)');
  }, function () {
    document.getElementById('where').textContent = 'Location permission denied - pick an origin instead.';
  }, { timeout: 8000 });
});
render([38.2544, -104.6091], 'Downtown Pueblo');
__NAVJS__
</script>
__FOOT__
</body>
</html>
"""


def build() -> str:
    vs = vendors()
    for v in vs:
        v.pop("marker", None)
    html = (PAGE.replace("__CANON__", site_base.url("radar/")).replace("__VENDORS__", json.dumps(vs))
                .replace("__COUNT__", str(len(vs)))
                .replace("__LIVELINE__", site_base.live_sentence(sum(1 for v in vs if v.get("serving") or v.get("location_label") == "vendor check-in")))
                .replace("__BUILT__", datetime.date.today().isoformat())
                .replace("__OG__", site_base.og_block(
                    "Live radar - Southern Colorado food trucks near you",
                    "See every tracked Southern Colorado food truck on a map, sorted by how far it is from you. Free listings and direct vendor contact.",
                    "radar/"))
                .replace("__NAVCSS__", site_base.NAV_CSS)
                .replace("__NAV__", site_base.nav_block("/radar/"))
                .replace("__NAVJS__", site_base.NAV_JS).replace("__FOOT__", site_base.footer_block()))
    return html


if __name__ == "__main__":
    html = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
    if "--check" in sys.argv:
        ok = site_base.same(html, cur)
        print("CURRENT" if ok else "STALE")
        raise SystemExit(0 if ok else 1)
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"wrote {OUT} ({len(html)} bytes, {html.count(chr(34)+'lat'+chr(34))} vendor coordinates)")
