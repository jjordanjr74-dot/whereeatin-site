#!/usr/bin/env python3
"""Generate the customer-and-vendor promotions board from live venture data.

Usage: python build_promotions.py [--check]
Only time-bounded vendor-posted offers are advertised. The current truck roster
is imported from vendors_row.roster; promotions come from vendors_row.db.
"""
from __future__ import annotations

import datetime as dt
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDORS = HERE.parent / "vendors_row"
sys.path.insert(0, str(VENDORS))
import roster  # noqa: E402
import site_base  # noqa: E402

OUT = HERE / "promotions" / "index.html"
SIGNUP = "https://whereeatin.com/list-your-truck/"
RADAR = "https://whereeatin.com/radar/"
DESK_BOT_LINK = site_base.desk_link("vendor")

# The specials write API has no authenticated vendor identity, so it is not
# safe to present those rows as vendor-confirmed offers.


def build() -> str:
    vendors = roster.load()
    cards = []
    for vendor in vendors:
        label = html.escape(vendor["name"])
        cuisine = html.escape(vendor["specialty"])
        area = html.escape(vendor["location"])
        tel = "".join(c for c in (vendor.get("phone") or "") if c.isdigit() or c == "+")
        call = f'<a class="button secondary" href="tel:{tel}">Call the truck</a>' if tel else ""
        cards.append(
            f'<article class="vendor-card"><span class="eyebrow">{area} · usual area</span>'
            f'<p class="speciality">{cuisine}</p><h2>{label}</h2>'
            f'<div class="actions">{call}<a class="button" href="{RADAR}">Find on radar</a></div>'
            f'</article>'
        )

    empty_notice = (
        '<p class="notice">No time-limited offers are published here. This site does not yet have an '
        'authenticated vendor offer-submission flow. Browse truck listings below and contact the vendor '
        'to confirm today’s menu, availability, and prices.</p>'
    )
    built = dt.date.today().isoformat()
    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Explore local food trucks | Where We Eatin’?</title>
<meta name="description" content="Explore Southern Colorado food trucks, their listed specialties and usual service areas. Call vendors directly to confirm today's menu and availability.">
<link rel="canonical" href="{site_base.url('promotions/')}">
__OG__
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../assets/site.css">
<style>
.promo-hero{{background:linear-gradient(120deg,#fff1e9,#fffdfa 60%,#f7f3ec);padding:clamp(44px,7vw,84px) 0 42px}}
.promo-hero h1{{max-width:15ch;font-size:clamp(2rem,8.5vw,4.2rem);overflow-wrap:anywhere}}
.promo-hero .lead{{max-width:58ch;margin-top:20px}}
.promo-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-top:26px}}
.promo-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin-top:34px}}
.vendor-card{{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow-1);display:flex;flex-direction:column;min-width:0}}
.vendor-card h2{{font-size:1.45rem;margin:12px 0 7px;overflow-wrap:anywhere}}
.card-top{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:.9rem}}
.vendor-special{{color:var(--ink-2);font-weight:600}}
.deal{{position:relative;border-left:4px solid var(--live);background:var(--live-soft);border-radius:0 12px 12px 0;padding:14px;margin:8px 0 18px}}
.deal p{{margin:6px 0}}.deal small{{color:var(--muted)}}.deal-price{{float:right;font-weight:800;color:#0a6b3c}}
.notice{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:18px 0;color:var(--ink-2)}}
.actions{{display:flex;flex-wrap:wrap;gap:10px;margin-top:auto;padding-top:18px}}
.actions .button{{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 16px;border-radius:999px;background:var(--brand);color:#fff;text-decoration:none;font-weight:700}}
.actions .secondary{{background:#fff;color:var(--ink);border:1px solid var(--line)}}
@media(max-width:900px){{.promo-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:600px){{.promo-grid{{grid-template-columns:minmax(0,1fr)}}.vendor-card{{padding:18px}}}}
__NAVCSS__
</style></head><body>
__NAV__
<main id="main"><section class="promo-hero"><div class="wrap"><p class="eyebrow">Southern Colorado · Pueblo to Colorado Springs</p>
<h1>Good food. Found before you drive.</h1><p class="lead">Explore local truck specialties, find a usual service area, and call the people cooking. No delivery markup. Confirm menus and availability with the vendor.</p>
<div class="promo-actions"><a class="btn btn-primary" href="{RADAR}">Find trucks near you →</a><a class="btn btn-ghost" href="{SIGNUP}">Check listing status</a></div></div></section>
<section class="sec"><div class="wrap"><p class="eyebrow">Food trucks, direct</p><h2>Find your next meal</h2>
{empty_notice}<div class="promo-grid">{"".join(cards)}</div>
<div class="banner" style="margin-top:44px"><div><h2>Run a food truck?</h2><p>Listings are free &mdash; message <a href="{DESK_BOT_LINK}">@Sheba_telegram_bot</a> to get yours started. No commission, ever.</p></div><a class="btn btn-primary" href="{DESK_BOT_LINK}">List your truck free →</a></div>
<div class="notice" style="margin-top:24px;border:2px solid var(--ink)">
  <p class="eyebrow" style="margin:0 0 6px">Event &amp; Party Partner &middot; Veteran-Owned Colorado Bounce Club</p>
  <h3 style="margin:0 0 8px">Planning a Party or Truck Rally? Bundle a Food Truck + 8-Hour Bounce House ($25 OFF)</h3>
  <p style="margin:0 0 8px">Pair any local food truck booking with an 8-hour sanitized bounce house ($85&ndash;$175) or water slide combo ($175&ndash;$275) from <a href="https://coloradobounceclub.com/" target="_blank" rel="noopener"><strong>Colorado Bounce Club</strong></a> (719-299-0772 &middot; Free delivery in Pueblo, $50 within 50 miles to Colorado Springs &amp; Fountain) and receive <strong>$25 OFF your inflatable rental</strong>. Listed food trucks also receive <strong>20% OFF weekday/pop-up event inflatables</strong> and a <strong>$20 plan credit</strong> per referred party. Se Habla Espa&ntilde;ol.</p>
  <p style="margin:8px 0 0"><a class="btn btn-sm btn-primary" href="https://buy.stripe.com/6oUcMY3KX26vgG03uh08g0s">Reserve Food Truck Event Date ($250 Deposit) →</a></p>
</div>
</div></section></main><footer class="foot"><div class="wrap"><p>No vendor offer-submission flow is enabled on this page. Confirm menus, prices, and availability directly with each truck; unconfirmed menu prices are not represented as verified.</p><p><a href="../privacy/">Privacy</a> · <a href="../">Home</a></p><small>Data built {built} from the current vendor roster.</small></div></footer>
<script src="../assets/site.js" defer></script>
<script>__NAVJS__</script>
__FOOT__
</body></html>"""
    return (page.replace("__OG__", site_base.og_block(
        "Explore local food trucks in Southern Colorado",
        "Browse local truck specialties and contact vendors directly. No invented discounts or ordering markup.",
        "promotions/"))
        .replace("__NAVCSS__", site_base.NAV_CSS)
        .replace("__NAV__", site_base.nav_block("/promotions/"))
        .replace("__NAVJS__", site_base.NAV_JS).replace("__FOOT__", site_base.footer_block()))


def main() -> int:
    page = build()
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if "--check" in sys.argv:
        ok = site_base.same(page, current)
        print("CURRENT" if ok else "STALE")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page)} bytes, {len(roster.load())} trucks; offer submission is not enabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
