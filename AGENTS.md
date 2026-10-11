# AGENTS.md — Where We Eatin' site

Agent instructions for this repository. Read by Cursor, Hermes and other coding agents.
Keep this short and current; a stale rule is worse than no rule.

## What this is

Static site + Python generators for **Where We Eatin'** (food-truck directory).
Generated HTML is committed and served by GitHub Pages. The `.py` builders are the source of truth;
the `.html` files are build output that happens to live in the tree.

## Build & gates

Each builder supports a staleness gate — generated pages must be CURRENT, never hand-edited:

```bash
python build_site.py --check        # also: build_listing.py, build_radar.py,
python build_promotions.py --check  #       build_reviews.py, build_travel.py
python travel_check.py              # travel-page validation
python -m pytest -q                 # 1 test file here
```

If `--check` reports STALE, **rebuild** (`python build_site.py`), do not edit the HTML by hand.

## Hard rules

1. **Deploy is owner-gated.** `deploy_site.py` pushes to GitHub Pages and changes the live public
   site. Never run it, and never `git push`, without explicit approval in the current session.
2. **Live must equal build.** After any change to a builder or its inputs, regenerate and confirm the
   committed HTML reflects it. A site serving an older claim than the repo is a defect.
3. **Never assert a price is vendor-confirmed here.** That fact is owned by
   `../vendors_row/verify_price.py`. Do not write "prices confirmed by the truck" or similar into
   copy unless that script supports it — it exits non-zero by design when prices are unconfirmed,
   and that exit code is the only evidence that counts.
4. **No intake forms on the public static surface.** This host is static-only; a form posting to a
   relative action endpoint collects nothing and silently drops submissions. Use a phone/text CTA, or
   the private tunnel surface, for real intake.
5. Cross-repo dependency: the radar roster sync lives in `../vendors_row/sync_radar_roster.py`.
   Run its `--check` after roster changes rather than duplicating its logic here.

## Gotchas

- `site_base.py` supplies the base URL/template values. A missing/blank base leaks template
  placeholders into the deployed HTML — grep the built output for `{site_base`-style leftovers after
  a build.
- `CNAME.hold` exists deliberately; do not delete it or `CNAME` without checking which one is active.
