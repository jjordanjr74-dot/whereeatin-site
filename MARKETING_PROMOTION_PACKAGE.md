# Where We Eatin’ — customer + vendor marketing package

## Customer message
“Track the truck. Skip the guess. Taste the town.” Find Southern Colorado food trucks by location, see their actual listed specialty, and contact the vendor directly. Where We Eatin’ is a discovery directory: no in-app ordering, no delivery, and no markup added by the directory.

## Vendor message
“Your truck. On the map.” A Southern Colorado food truck can request a free listing with no commission. Share truck name, what you sell, customer phone, usual location, and service days in one Telegram message. The operator confirms details and asks for approval before publishing. Only request details the intake channel actually collects. Existing listings and paid listing tiers are disclosed on the website; do not promise unimplemented social post cadence or fabricated reach.

## Promotion rules
- The app's existing vendor_specials write API has no authenticated submitter field/access check. The public offer board therefore displays no specials until that trust gate exists; never imply an unverified API row is a vendor-confirmed offer.
- Menu prices remain labelled unconfirmed until the vendor verifies them. Current live catalogue has 45 menu rows and zero vendor-confirmed menu prices.
- Ratings and HIGHLY RECOMMENDED remain earned only; never imply a paid placement is a rating.
- Customer actions are radar, vendor listing page, and tap-to-call. Do not claim ordering, reservations, customer coupons, or catering lead routing unless the specific mechanism is independently verified.
- Never send outreach, publish customer-visible changes, or spend on ads without the authorized publishing/campaign step.

## Customer launch copy
“Lunch plans? Open the Where We Eatin’ radar. Check the food trucks around you, see the vendor-reported spot when available, and call the truck directly. No app account. No delivery markup. Serving now is shown only when the truck confirms it.”

CTA: https://whereeatin.com/radar/

## Vendor invite copy
“Hey [truck name] — we’re building a local food-truck radar for Southern Colorado. Your free listing can show your truck, what you cook, your customer phone and usual spot. There’s no commission. Want us to send you the details to approve before it goes live? Sign-up: https://whereeatin.com/list-your-truck/”

## Community post
“Pueblo / Pueblo West / Colorado Springs / Cañon City: looking for a local food truck? Where We Eatin’ puts tracked trucks on a map with direct contact links. Locations aren’t continuous GPS: a truck’s check-in is vendor-reported and expires, otherwise the map shows its usual area. Find trucks: https://whereeatin.com/radar/”

## 30-day measurable pilot (no paid media)
1. Week 1: Confirm each existing listing with the vendor; correct stale phone, location, schedule and menu claims. Do not mark complete without vendor reply.
2. Week 2: Ask participating vendors to share their own listing/radar link; publish only approved copy and approved vendor photos.
3. Week 3: Invite customers to try the radar and leave honest reviews through the review desk; no incentivized or planted reviews.
4. Week 4: Read server-side listing impressions/call taps and count actual vendor submissions, verified prices, active offers and new reviews. Compare with the pre-pilot baseline before claiming lift.

Track: listing pageviews by vendor, call taps, opt-in new vendors, returned vendor confirmations, vendor-confirmed menu items, current expiring specials, genuine customer reviews. No target conversion numbers are asserted before baseline data exists.

## Assets and status
- Public customer page: `https://whereeatin.com/promotions/`
- Vendor onboarding page: `https://whereeatin.com/list-your-truck/`
- Customer radar: `https://whereeatin.com/radar/`
- Vendor social/print assets in `D:/Hermes_Core/Workspace/vendors_row/static/creatives/` are an existing separate app kit; do not redistribute the older package text with fake features or the obsolete GitHub URL.
- Build: `python build_promotions.py`; generated page is `promotions/index.html`; freshness check: `python build_promotions.py --check`.
- Local regression: `python test_marketing_package.py`.
- Release: first run all project checks and inspect full deploy scope; publish only after explicit approval of customer-facing publication.

## Known constraints
The intake channel is Telegram `@HermesEbookBot` (generic current bot name). The intake process is operator-mediated. Stripe has live-mode configuration, but there are no paid vendor sessions or paid vendors; the free signup path is the active acquisition CTA. This package does not send messages or claim to have generated customers.